"""Automatic Dataset Harvester for Vivan Fine-Tuning (GPT-SoVITS / Fish Speech / F5-TTS-ID).

Every time ElevenLabs `eleven_v4` generates a Vivan voiceover with character/word timestamps,
this harvester automatically slices the audio at natural sentence boundaries (3s - 12s per clip)
and exports clean 24kHz mono WAV + `.lab` (clean Indonesian transcript) pairs into:
  /home/ubuntu/apps/ugc-lemonaru/assets/audio/vivan_dataset/

By the end of the active ElevenLabs billing cycle, this dataset reaches 20-30 minutes of
100% studio-aligned Vivan emotional storytelling data for fine-tuning.
"""

import re
import json
import hashlib
import subprocess
from pathlib import Path
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT_DIR / "assets" / "audio" / "vivan_dataset"
WAVS_DIR = DATASET_DIR / "wavs"
MANIFEST_FILE = DATASET_DIR / "metadata.jsonl"


def harvest_from_aligned_words(
    audio_path: str,
    words: List[Dict[str, Any]],
    source_id: str = "",
) -> int:
    """Slice raw Vivan audio into clean 3-12s sentence clips + .lab transcripts for training."""
    WAVS_DIR.mkdir(parents=True, exist_ok=True)
    src_audio = Path(audio_path)
    if not src_audio.exists() or not words:
        return 0

    if not source_id:
        source_id = src_audio.stem

    # Group words into sentence segments (3.0s to 12.0s)
    segments = []
    curr_words = []
    seg_start = None

    for w in words:
        word_text = str(w.get("word") or w.get("text") or "").strip()
        if not word_text:
            continue
        start_s = float(w.get("start") if "start" in w else float(w.get("startMs", 0)) / 1000.0)
        end_s = float(w.get("end") if "end" in w else float(w.get("endMs", 0)) / 1000.0)

        if seg_start is None:
            seg_start = start_s
        curr_words.append(word_text)
        dur = end_s - seg_start

        is_punct_end = word_text.endswith((".", "!", "?"))
        if (is_punct_end and dur >= 3.0) or dur >= 10.5:
            segments.append({
                "start": max(0.0, seg_start - 0.05),
                "end": end_s + 0.08,
                "text": " ".join(curr_words),
            })
            curr_words = []
            seg_start = None

    if curr_words and seg_start is not None:
        last_end = float(words[-1].get("end") if "end" in words[-1] else float(words[-1].get("endMs", 0)) / 1000.0)
        if last_end - seg_start >= 2.0:
            segments.append({
                "start": max(0.0, seg_start - 0.05),
                "end": last_end + 0.08,
                "text": " ".join(curr_words),
            })

    existing_ids = set()
    if MANIFEST_FILE.exists():
        for line in MANIFEST_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    existing_ids.add(json.loads(line).get("clip_id"))
                except Exception:
                    pass

    saved_count = 0
    with open(MANIFEST_FILE, "a", encoding="utf-8") as mf:
        for idx, seg in enumerate(segments):
            clean_txt = re.sub(r"\[[^\]]*\]", "", seg["text"]).strip()
            clean_txt = re.sub(r"\s+", " ", clean_txt)
            if len(clean_txt) < 10:
                continue

            h = hashlib.md5(clean_txt.encode("utf-8")).hexdigest()[:8]
            clip_id = f"{source_id}_{idx:02d}_{h}"
            if clip_id in existing_ids:
                continue

            wav_out = WAVS_DIR / f"{clip_id}.wav"
            lab_out = WAVS_DIR / f"{clip_id}.lab"
            dur = round(seg["end"] - seg["start"], 3)

            res = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-ss", str(round(seg["start"], 3)),
                    "-t", str(dur),
                    "-i", str(src_audio),
                    "-ar", "24000", "-ac", "1",
                    str(wav_out),
                ],
                capture_output=True,
            )
            if res.returncode == 0 and wav_out.exists():
                lab_out.write_text(clean_txt, encoding="utf-8")
                mf.write(json.dumps({
                    "clip_id": clip_id,
                    "audio_filepath": str(wav_out),
                    "text": clean_txt,
                    "duration": dur,
                    "speaker": "vivan",
                    "language": "id",
                }, ensure_ascii=False) + "\n")
                saved_count += 1

    return saved_count

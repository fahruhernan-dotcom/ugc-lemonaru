"""Custom Zero-Cost Vivan Voice Cloning & Word-Level Timestamp Engine for DoniesDaily.

Provides 100% drop-in compatibility with `elevenlabs_tts.py`:
- `generate_speech(text, output_path, ...)`
- `generate_speech_with_timestamps(text, output_audio_path, output_captions_json, ...)`

Architecture (3-Tier Resilient Pool + Groq Whisper Word Aligner):
1. Tier 1 (`chatterbox`): Zero-Shot Voice Cloning via `ResembleAI/Chatterbox-Multilingual-TTS`
   (& `-V3` mirror) using DoniesDaily's clean studio Vivan reference (`vivan_master_ref_12s.wav`).
   Processes full Shorts script in 1 single GPU call (up to 650 chars) to conserve quota.
2. Tier 2 (`seedvc`): Native Indonesian neural prosody (`edge-tts` `id-ID-ArdiNeural`)
   converted via Diffusion Transformer Voice Cloning (`Plachta/Seed-VC` ZeroGPU + `Uniaff/Seed-VC`
   Unlimited CPU-Basic Space) to Vivan's 25s reference (`vivan_master_ref_25s.wav`).
3. Tier 3 (`local_studio`): Local sentence-directed `edge-tts` (`id-ID-ArdiNeural`) with dynamic
   pitch/rate per emotion tag (`[curious]`, `[gasps]`, `[excited]`) + FFmpeg studio vocal EQ
   matching Vivan's warm chest resonance.
4. Word-Level Timestamp Forced Aligner: Uses Groq `whisper-large-v3-turbo` (`timestamp_granularities=["word"]`)
   to produce millisecond-accurate Remotion `captions.json` (`text`, `startMs`, `endMs`, `timestampMs`, `confidence`).
"""

import os
import re
import json
import shutil
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env", override=True)
load_dotenv("/home/ubuntu/.hermes/.env", override=False)

REF_DIR = ROOT_DIR / "assets" / "audio" / "voice_clones"
VIVAN_REF_12S = REF_DIR / "vivan_master_ref_12s.wav"
VIVAN_REF_25S = REF_DIR / "vivan_master_ref_25s.wav"

TAG_EXAGGERATION_MAP = {
    "excited": 0.68,
    "gasps": 0.70,
    "curious": 0.60,
    "laughs": 0.62,
    "whispers": 0.35,
    "sighs": 0.42,
}
DEFAULT_EXAGGERATION = 0.55

# Dynamic prosody mapping for base Indonesian TTS per emotion tag
TAG_PROSODY_MAP = {
    "curious": ("+8%", "+3Hz"),
    "gasps": ("+11%", "+5Hz"),
    "excited": ("+10%", "+4Hz"),
    "laughs": ("+7%", "+2Hz"),
    "whispers": ("-4%", "-4Hz"),
    "sighs": ("-3%", "-3Hz"),
}
DEFAULT_PROSODY = ("+6%", "-1Hz")


def _ensure_reference_files():
    """Ensure clean 12s and 25s Vivan reference WAV files exist."""
    REF_DIR.mkdir(parents=True, exist_ok=True)
    src_candidates = [
        ROOT_DIR / "assets" / "audio" / "generated_voiceovers" / "cat_sleeping_on_dirty_laundry_vivan.mp3",
        ROOT_DIR / "assets" / "audio" / "generated_voiceovers" / "cat_water_bowl_away_from_food_vivan.mp3",
        ROOT_DIR / "data" / "sample_Vivan_Male.mp3",
    ]
    src = next((p for p in src_candidates if p.exists()), None)
    if not src:
        raise FileNotFoundError("Master Vivan audio source not found in assets/audio/generated_voiceovers/")

    if not VIVAN_REF_12S.exists():
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "2", "-t", "12", "-i", str(src), "-ar", "24000", "-ac", "1", str(VIVAN_REF_12S)],
            check=True, capture_output=True
        )
    if not VIVAN_REF_25S.exists():
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "2", "-t", "25", "-i", str(src), "-ar", "24000", "-ac", "1", str(VIVAN_REF_25S)],
            check=True, capture_output=True
        )


def _split_script_into_chunks(text: str, max_chars: int = 650) -> List[Tuple[str, float]]:
    """Split script into natural chunks (default 650 chars = 1 single call per Shorts video)."""
    raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    chunks: List[Tuple[str, float]] = []
    curr_text = ""
    curr_exag = DEFAULT_EXAGGERATION

    for sent in raw_sentences:
        sent = sent.strip()
        if not sent:
            continue

        tags = re.findall(r"\[([a-zA-Z_\s]+)\]", sent.lower())
        sent_exag = DEFAULT_EXAGGERATION
        for t in tags:
            t_clean = t.strip()
            if t_clean in TAG_EXAGGERATION_MAP:
                sent_exag = TAG_EXAGGERATION_MAP[t_clean]
                break

        clean_sent = re.sub(r"\[[^\]]*\]", "", sent).strip()
        clean_sent = re.sub(r"\s+", " ", clean_sent)
        if not clean_sent:
            continue

        if len(curr_text) + len(clean_sent) + 1 <= max_chars:
            curr_text = f"{curr_text} {clean_sent}".strip() if curr_text else clean_sent
            curr_exag = max(curr_exag, sent_exag)
        else:
            if curr_text:
                chunks.append((curr_text, curr_exag))
            curr_text = clean_sent
            curr_exag = sent_exag

    if curr_text:
        chunks.append((curr_text, curr_exag))

    return chunks


def _build_expressive_base_mp3(text: str, out_mp3: Path):
    """Generate sentence-by-sentence expressive Indonesian neural audio via edge-tts."""
    import edge_tts

    raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        part_files: List[Path] = []

        async def _run_all():
            for idx, sent in enumerate(raw_sentences):
                sent = sent.strip()
                if not sent:
                    continue
                tags = re.findall(r"\[([a-zA-Z_\s]+)\]", sent.lower())
                rate, pitch = DEFAULT_PROSODY
                for t in tags:
                    t_clean = t.strip()
                    if t_clean in TAG_PROSODY_MAP:
                        rate, pitch = TAG_PROSODY_MAP[t_clean]
                        break
                clean_sent = re.sub(r"\[[^\]]*\]", "", sent).strip()
                clean_sent = re.sub(r"\s+", " ", clean_sent)
                if not clean_sent:
                    continue
                p_out = tmp_path / f"sent_{idx:02d}.mp3"
                comm = edge_tts.Communicate(clean_sent, "id-ID-ArdiNeural", rate=rate, pitch=pitch)
                await comm.save(str(p_out))
                part_files.append(p_out)

        asyncio.run(_run_all())

        if not part_files:
            raise RuntimeError("No valid sentences found in script")

        concat_txt = tmp_path / "concat.txt"
        concat_txt.write_text("\n".join(f"file '{p}'" for p in part_files), encoding="utf-8")
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
                "-af", "equalizer=f=180:width_type=o:width=1.5:g=3.2,equalizer=f=3500:width_type=o:width=2.0:g=2.0,loudnorm=I=-16:TP=-1.5:LRA=11",
                "-codec:a", "libmp3lame", "-qscale:a", "2", str(out_mp3)
            ],
            check=True, capture_output=True
        )


def _synthesize_chatterbox(chunks: List[Tuple[str, float]], out_mp3: Path) -> bool:
    """Tier 1: Zero-Shot Voice Cloning via Chatterbox-Multilingual."""
    from gradio_client import Client, handle_file

    _ensure_reference_files()
    hf_token = os.getenv("HF_TOKEN") or None
    spaces = [
        ("ResembleAI/Chatterbox-Multilingual-TTS", "v1"),
        ("ResembleAI/Chatterbox-Multilingual-TTS-V3", "v3"),
    ]

    for space_id, variant in spaces:
        try:
            client = Client(space_id, token=hf_token)
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                wav_parts: List[Path] = []

                for idx, (chunk_text, exag) in enumerate(chunks):
                    if variant == "v1":
                        res = client.predict(
                            text_input=chunk_text,
                            language_id="ms",
                            audio_prompt_path_input=handle_file(str(VIVAN_REF_12S)),
                            exaggeration_input=float(exag),
                            temperature_input=0.75,
                            seed_num_input=42,
                            cfgw_input=0.5,
                            api_name="/generate_tts_audio",
                        )
                    else:
                        res = client.predict(
                            text_input=chunk_text,
                            audio_prompt_path_input=handle_file(str(VIVAN_REF_12S)),
                            language_id_input="ms",
                            exaggeration_input=float(exag),
                            temperature_input=0.75,
                            seed_num_input=42,
                            cfgw_input=0.5,
                            api_name="/generate_tts_audio",
                        )

                    part_wav = tmp_path / f"part_{idx:02d}.wav"
                    shutil.copy(res, part_wav)
                    wav_parts.append(part_wav)

                concat_list = tmp_path / "concat.txt"
                concat_list.write_text("\n".join(f"file '{p}'" for p in wav_parts), encoding="utf-8")
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
                        "-af", "silenceremove=start_periods=1:start_silence=0.05:start_threshold=-45dB,loudnorm=I=-16:TP=-1.5:LRA=11",
                        "-codec:a", "libmp3lame", "-qscale:a", "2", str(out_mp3)
                    ],
                    check=True, capture_output=True
                )
                return True
        except Exception as e:
            print(f"[custom_vivan_tts] Tier 1 Chatterbox ({space_id}) info: {e}")
            continue
    return False


def _synthesize_seedvc(raw_script: str, out_mp3: Path, include_cpu_space: bool = False) -> bool:
    """Tier 2: Expressive Indonesian Base + Seed-VC Diffusion Voice Conversion to Vivan."""
    from gradio_client import Client, handle_file

    _ensure_reference_files()
    hf_token = os.getenv("HF_TOKEN") or None

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        base_mp3 = tmp_path / "base_expressive.mp3"
        _build_expressive_base_mp3(raw_script, base_mp3)

        seedvc_targets = [("Plachta/Seed-VC", "/predict_1", 25)]
        if include_cpu_space:
            seedvc_targets.append(("Uniaff/Seed-VC", "/predict", 10))

        for space_id, api_ep, steps in seedvc_targets:
            try:
                svc = Client(space_id, token=hf_token)
                if api_ep == "/predict_1":
                    res = svc.predict(
                        source_audio_path=handle_file(str(base_mp3)),
                        target_audio_path=handle_file(str(VIVAN_REF_25S)),
                        diffusion_steps=steps,
                        length_adjust=1.0,
                        inference_cfg_rate=0.7,
                        f0_condition=False,
                        auto_f0_adjust=True,
                        pitch_shift=0,
                        api_name=api_ep,
                    )
                else:
                    res = svc.predict(
                        source=handle_file(str(base_mp3)),
                        target=handle_file(str(VIVAN_REF_25S)),
                        diffusion_steps=steps,
                        length_adjust=1.0,
                        inference_cfg_rate=0.7,
                        f0_condition=False,
                        auto_f0_adjust=True,
                        pitch_shift=0,
                        api_name=api_ep,
                    )
                full_out = res[1] if isinstance(res, (list, tuple)) else res
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-i", str(full_out),
                        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
                        "-codec:a", "libmp3lame", "-qscale:a", "2", str(out_mp3)
                    ],
                    check=True, capture_output=True
                )
                return True
            except Exception as e:
                print(f"[custom_vivan_tts] Tier 2 Seed-VC ({space_id}) info: {e}")
                continue
    return False


def _extract_word_timestamps_groq(audio_path: Path) -> Tuple[List[Dict[str, Any]], float]:
    """Extract millisecond-accurate word-level timestamps using Groq whisper-large-v3-turbo."""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise RuntimeError("GROQ_API_KEY is missing for word-level timestamp alignment")

    cmd = [
        "curl", "-s", "https://api.groq.com/openai/v1/audio/transcriptions",
        "-H", f"Authorization: Bearer {groq_key}",
        "-F", f"file=@{audio_path}",
        "-F", "model=whisper-large-v3-turbo",
        "-F", "language=id",
        "-F", "response_format=verbose_json",
        "-F", "timestamp_granularities[]=word",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    words = data.get("words", [])
    duration = float(data.get("duration") or (words[-1]["end"] if words else 0.0))

    remotion_captions = []
    for idx, w in enumerate(words):
        t = str(w.get("word", "")).replace(",", "").strip()
        if not t:
            continue
        if idx > 0 and not t.startswith(" "):
            t = " " + t
        s_ms = int(float(w.get("start", 0.0)) * 1000)
        e_ms = int(float(w.get("end", 0.0)) * 1000)
        remotion_captions.append({
            "text": t,
            "startMs": s_ms,
            "endMs": e_ms,
            "timestampMs": s_ms,
            "confidence": 0.99,
        })

    return remotion_captions, duration


def generate_speech(
    text: str,
    output_path: str,
    engine: str = "auto",
) -> str:
    """Generate Vivan cloned speech MP3 (zero-cost 3-Tier pool)."""
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    chunks = _split_script_into_chunks(text)

    if engine in ("auto", "chatterbox"):
        if _synthesize_chatterbox(chunks, out_file):
            return str(out_file)
        if engine == "chatterbox":
            raise RuntimeError("Chatterbox synthesis failed")

    if engine in ("auto", "seedvc"):
        if _synthesize_seedvc(text, out_file, include_cpu_space=(engine == "seedvc")):
            return str(out_file)
        if engine == "seedvc":
            raise RuntimeError("Seed-VC synthesis failed")

    # Tier 3: Guaranteed zero-latency Local Expressive Studio Neural fallback
    print("[custom_vivan_tts] Using Tier 3 Local Expressive Studio Neural engine...")
    _build_expressive_base_mp3(text, out_file)
    return str(out_file)


def generate_speech_with_timestamps(
    text: str,
    output_audio_path: str,
    output_captions_json: str,
    engine: str = "auto",
) -> Tuple[str, str, float]:
    """Generate Vivan cloned speech MP3 + Remotion word-level captions JSON."""
    out_audio = Path(output_audio_path).resolve()
    out_captions = Path(output_captions_json).resolve()
    out_audio.parent.mkdir(parents=True, exist_ok=True)
    out_captions.parent.mkdir(parents=True, exist_ok=True)

    generate_speech(text=text, output_path=str(out_audio), engine=engine)
    remotion_captions, duration = _extract_word_timestamps_groq(out_audio)

    with open(out_captions, "w", encoding="utf-8") as f:
        json.dump(remotion_captions, f, indent=2)

    return str(out_audio), str(out_captions), duration


if __name__ == "__main__":
    print("Custom Vivan TTS module initialized successfully.")

"""ElevenLabs TTS Integration for DoniesDaily Engine.
Loads ELEVENLABS_API_KEY from .env using python-dotenv.
Supports standard speech generation and high-precision word-level timestamps for Remotion captions.
"""

import os
import json
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv
from elevenlabs import ElevenLabs, VoiceSettings

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env", override=True)

client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Suara default: Vivan – Clean, Warm, and Expressive Male (ZowYWFat3iypr7PwKMPb)
# Alternatif: Kak Ceria (d15jrIAARvF899pDoC6T)
DEFAULT_VOICE_ID = "ZowYWFat3iypr7PwKMPb"
DEFAULT_MODEL_ID = "eleven_v4"

def _send_telegram_alert(text: str):
    """Kirim notifikasi darurat kuota ke Telegram Mas Fahru."""
    try:
        token = ""
        env_hermes = Path("/home/ubuntu/.hermes/.env")
        if env_hermes.exists():
            for line in env_hermes.read_text(encoding="utf-8").splitlines():
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    token = line.split("=", 1)[1].strip("\"'")
        if token:
            import urllib.request
            payload = json.dumps({"chat_id": "1357517232", "text": text, "parse_mode": "Markdown"}).encode("utf-8")
            req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
    except Exception as e:
        print(f"[elevenlabs_tts] Failed to send Telegram alert: {e}")

def check_elevenlabs_quota_health() -> int:
    """Mengecek sisa karakter ElevenLabs dan memicu early-warning jika sisa < 3.000 karakter."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        return 0
    try:
        import urllib.request
        req = urllib.request.Request("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": api_key})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            used = data.get("character_count", 0)
            limit = data.get("character_limit", 0)
            remaining = max(0, limit - used)
            
            # Alert throttling: max 1 notifikasi per hari jika sisa kritis
            alert_file = ROOT_DIR / "data/elevenlabs_low_quota_alert.txt"
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            if remaining < 3000:
                already_alerted = alert_file.exists() and alert_file.read_text().strip() == today_str
                if not already_alerted:
                    alert_file.parent.mkdir(parents=True, exist_ok=True)
                    alert_file.write_text(today_str)
                    _send_telegram_alert(
                        f"⚠️ *[EARLY WARNING KUOTA ELEVENLABS @DoniesDaily]*\\n"
                        f"Sisa kuota vokal Vivan tersisa *{remaining:,}* dari {limit:,} karakter (~{remaining // 750} video Short tersisa).\\n"
                        f"Sistem akan otomatis beralih ke Custom Vivan Clone jika kuota habis."
                    )
            return remaining
    except Exception as e:
        print(f"[elevenlabs_tts] Warning checking quota: {e}")
        return 999999

def _use_custom_provider() -> bool:
    return os.getenv("DONIES_TTS_PROVIDER", "elevenlabs").strip().lower() in ("custom", "custom_vivan", "vivan_clone")

def generate_speech(
    text: str,
    output_path: str,
    voice_id: str = DEFAULT_VOICE_ID,
    model_id: str = DEFAULT_MODEL_ID
) -> str:
    if _use_custom_provider():
        from src.custom_vivan_tts import generate_speech as custom_generate_speech
        return custom_generate_speech(text=text, output_path=output_path)

    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        audio_stream = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            voice_settings=VoiceSettings(
                stability=0.40,
                similarity_boost=0.75
            )
        )
        
        with open(out_file, "wb") as f:
            for chunk in audio_stream:
                f.write(chunk)
                
        return str(out_file)
    except Exception as e:
        print(f"[elevenlabs_tts] ElevenLabs API error ({e}), auto-falling back to Custom Vivan Clone...")
        from src.custom_vivan_tts import generate_speech as custom_generate_speech
        return custom_generate_speech(text=text, output_path=output_path)

def generate_speech_with_timestamps(
    text: str,
    output_audio_path: str,
    output_captions_json: str,
    voice_id: str = DEFAULT_VOICE_ID,
    model_id: str = DEFAULT_MODEL_ID
) -> Tuple[str, str, float]:
    """Generates audio with eleven_v4 and converts character alignments to word-level captions format for Remotion.
    Automatically filters out internal audio tags (e.g. [laughs], [sighs]) from visual subtitles.
    Supports seamless toggle via DONIES_TTS_PROVIDER=custom_vivan or auto-fallback on quota exhaustion.
    Returns (audio_path, captions_json_path, duration_seconds).
    """
    if _use_custom_provider():
        from src.custom_vivan_tts import generate_speech_with_timestamps as custom_gen_ts
        return custom_gen_ts(
            text=text,
            output_audio_path=output_audio_path,
            output_captions_json=output_captions_json
        )

    # Telemetry & Pre-emptive fallback if quota exhausted (<800 chars)
    rem_chars = check_elevenlabs_quota_health()
    if rem_chars < 800:
        print(f"[elevenlabs_tts] Sisa kuota kritis ({rem_chars} chars), beralih ke Custom Vivan Clone...")
        from src.custom_vivan_tts import generate_speech_with_timestamps as custom_gen_ts
        return custom_gen_ts(
            text=text,
            output_audio_path=output_audio_path,
            output_captions_json=output_captions_json
        )

    out_audio = Path(output_audio_path).resolve()
    out_captions = Path(output_captions_json).resolve()
    out_audio.parent.mkdir(parents=True, exist_ok=True)
    out_captions.parent.mkdir(parents=True, exist_ok=True)

    try:
        resp = client.text_to_speech.convert_with_timestamps(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            voice_settings=VoiceSettings(
                stability=0.40,
                similarity_boost=0.75
            )
        )
    except Exception as e:
        print(f"[elevenlabs_tts] ElevenLabs API error ({e}), auto-falling back to Custom Vivan Clone...")
        from src.custom_vivan_tts import generate_speech_with_timestamps as custom_gen_ts
        return custom_gen_ts(
            text=text,
            output_audio_path=output_audio_path,
            output_captions_json=output_captions_json
        )

    audio_bytes = base64.b64decode(resp.audio_base_64)
    with open(out_audio, "wb") as f:
        f.write(audio_bytes)

    # Parse character alignments to word tokens, ignoring bracketed audio tags [tag]
    chars = resp.alignment.characters if resp.alignment else []
    starts = resp.alignment.character_start_times_seconds if resp.alignment else []
    ends = resp.alignment.character_end_times_seconds if resp.alignment else []

    words: List[Dict[str, Any]] = []
    curr_word = ""
    w_start = 0.0
    w_end = 0.0
    in_bracket = False

    for i, ch in enumerate(chars):
        if ch == '[':
            in_bracket = True
            continue
        if ch == ']':
            in_bracket = False
            continue
        if in_bracket:
            continue

        s = starts[i]
        e = ends[i]
        if ch in [" ", "\n", "\t"]:
            if curr_word:
                words.append({"word": curr_word, "start": w_start, "end": w_end})
                curr_word = ""
        else:
            if not curr_word:
                w_start = s
            curr_word += ch
            w_end = e

    if curr_word:
        words.append({"word": curr_word, "start": w_start, "end": w_end})

    # Remotion captions schema format:
    remotion_captions = []
    for idx, w in enumerate(words):
        t = w["word"].replace(",", "")  # Hapus tanda koma dari subtitle (kebijakan visual bersih)
        if not t.strip():
            continue
        if idx > 0 and not t.startswith(" "):
            t = " " + t
        s_ms = int(w["start"] * 1000)
        e_ms = int(w["end"] * 1000)
        remotion_captions.append({
            "text": t,
            "startMs": s_ms,
            "endMs": e_ms,
            "timestampMs": s_ms,
            "confidence": 0.99
        })

    with open(out_captions, "w", encoding="utf-8") as f:
        json.dump(remotion_captions, f, indent=2)

    # Auto-harvest clean Vivan sentence clips + transcripts for fine-tuning dataset
    try:
        from src.vivan_dataset_harvester import harvest_from_aligned_words
        harvested = harvest_from_aligned_words(str(out_audio), words, source_id=out_audio.stem)
        if harvested:
            print(f"[elevenlabs_tts] Auto-harvested {harvested} Vivan training clips to vivan_dataset/")
    except Exception as he:
        print(f"[elevenlabs_tts] Dataset harvest warning: {he}")

    total_dur = words[-1]["end"] if words else 0.0
    return str(out_audio), str(out_captions), total_dur

if __name__ == "__main__":
    print("ElevenLabs module initialized successfully.")

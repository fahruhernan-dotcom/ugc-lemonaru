"""Indonesian Voice-Over TTS Engine for Velora AI.
Powered by Microsoft Edge Neural Voice (edge-tts).
Supports natural Indonesian voices: id-ID-GadisNeural (Female) and id-ID-ArdiNeural (Male).
Ensures zero-cost, high-fidelity neural audio generation directly to Drive D.
"""

import asyncio
import logging
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Union

import edge_tts
import imageio_ffmpeg

from src.config import TEMP_DIR

logger = logging.getLogger(__name__)

# Curated high-fidelity Indonesian neural voices
INDONESIAN_VOICES = {
    "gadis": {
        "id": "id-ID-GadisNeural",
        "gender": "Female",
        "description": "Lively, energetic, friendly Indonesian female voice - ideal for TikTok fashion & affiliate reviews",
    },
    "ardi": {
        "id": "id-ID-ArdiNeural",
        "gender": "Male",
        "description": "Warm, confident Indonesian male voice - suitable for formal / technical fashion overviews",
    },
}

DEFAULT_VOICE = "id-ID-GadisNeural"


class TTSEngine:
    """Manages voiceover generation and speech alignment for TikTok vertical videos."""

    @staticmethod
    def clean_script_for_speech(text: str) -> str:
        """Prepares text for natural speech synthesis.
        Strips markdown bolding, URLs, hashtags, emojis, and stage directions.
        """
        if not text:
            return ""

        # Remove markdown bold/italics
        cleaned = re.sub(r"[*_~`]", "", text)
        # Remove parenthesized cues like (Scene 1), [Pause], (Senyum)
        cleaned = re.sub(r"\([^\)]*\)", "", cleaned)
        cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)
        # Remove hashtags and URLs
        cleaned = re.sub(r"#\S+", "", cleaned)
        cleaned = re.sub(r"https?://\S+", "", cleaned)
        # Remove emojis & non-standard symbols while preserving Indonesian punctuation
        cleaned = re.sub(r"[^\w\s.,!?'\"-]", " ", cleaned, flags=re.UNICODE)
        # Collapse multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @classmethod
    def get_audio_duration(cls, audio_path: Union[str, Path]) -> float:
        """Extracts exact audio duration in seconds using FFmpeg probe."""
        path = Path(audio_path)
        if not path.exists():
            return 0.0

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [ffmpeg_exe, "-i", str(path), "-f", "null", "-"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res.stderr)
            if match:
                hours, minutes, seconds = map(float, match.groups())
                return hours * 3600 + minutes * 60 + seconds
        except Exception as exc:
            logger.warning("Failed to probe audio duration with FFmpeg: %s", exc)

        # Fallback estimation based on file size for standard 64-128kbps mp3
        try:
            size_bytes = path.stat().st_size
            # Rough estimate: ~16KB per second for 128kbps MP3
            return max(1.0, round(size_bytes / 16000.0, 2))
        except Exception:
            return 5.0

    @classmethod
    async def generate_voiceover_async(
        cls,
        text: str,
        output_path: Union[str, Path],
        voice: str = DEFAULT_VOICE,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> Tuple[Path, float]:
        """Asynchronously generates an MP3 narration from text using edge-tts.
        Returns (target_path, duration_seconds).
        """
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        cleaned_text = cls.clean_script_for_speech(text)
        if not cleaned_text:
            cleaned_text = "Halo Sahabat Velora, cek rekomendasi fashion pilihan ini sekarang!"

        communicate = edge_tts.Communicate(cleaned_text, voice=voice, rate=rate, pitch=pitch)
        await communicate.save(str(out_file))

        duration = cls.get_audio_duration(out_file)
        logger.info("Generated voiceover '%s': %.2fs at %s", voice, duration, out_file)
        return out_file, duration

    @classmethod
    def generate_voiceover(
        cls,
        text: str,
        output_path: Union[str, Path],
        voice: str = DEFAULT_VOICE,
        rate: str = "+0%",
        pitch: str = "+0Hz",
    ) -> Tuple[Path, float]:
        """Synchronously generates Indonesian voiceover audio."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(
                        asyncio.run,
                        cls.generate_voiceover_async(text, output_path, voice, rate, pitch),
                    ).result()
            else:
                return loop.run_until_complete(
                    cls.generate_voiceover_async(text, output_path, voice, rate, pitch)
                )
        except RuntimeError:
            return asyncio.run(
                cls.generate_voiceover_async(text, output_path, voice, rate, pitch)
            )

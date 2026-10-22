"""Media Muxer & Audio-Video Synchronization Engine for Velora AI.
Provides production-grade FFmpeg muxing, audio-stream validation,
background music ducking, and duration alignment for TikTok 9:16 UGC packages.
"""

import os
import re
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("media_muxer")


class MediaMuxer:
    """Production FFmpeg operator for automated TikTok video & audio assembly."""

    @staticmethod
    def get_ffmpeg_binary() -> str:
        """Resolves local FFmpeg binary path via imageio_ffmpeg or system PATH."""
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return shutil.which("ffmpeg") or "ffmpeg"

    @classmethod
    def probe_file(cls, file_path: Path) -> Dict[str, Any]:
        """Probes video/audio file metadata using FFmpeg output."""
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            return {"exists": False, "duration": 0.0, "has_audio": False, "has_video": False}

        ffmpeg_bin = cls.get_ffmpeg_binary()
        cmd = [ffmpeg_bin, "-i", str(file_path)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            output = res.stderr
        except Exception as e:
            logger.error("Failed to probe file %s: %s", file_path, e)
            return {"exists": True, "duration": 0.0, "has_audio": False, "has_video": False, "error": str(e)}

        # Parse duration: Duration: 00:00:10.01,
        duration = 0.0
        dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", output)
        if dur_match:
            hours, minutes, seconds = dur_match.groups()
            duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)

        has_audio = bool(re.search(r"Stream #\d+:\d+.*Audio:", output))
        has_video = bool(re.search(r"Stream #\d+:\d+.*Video:", output))

        return {
            "exists": True,
            "duration": round(duration, 2),
            "has_audio": has_audio,
            "has_video": has_video,
            "raw_probe": output[:500]
        }

    @classmethod
    def verify_has_audio(cls, video_path: Path) -> bool:
        """Verifies whether a video file contains a valid audio track."""
        info = cls.probe_file(video_path)
        return info.get("has_audio", False) and info.get("duration", 0) > 0.5

    @classmethod
    def mux_video_and_audio(
        cls,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
        bgm_path: Optional[Path] = None,
        bgm_volume: float = 0.15,
        vo_volume: float = 1.0,
        target_duration: Optional[float] = None
    ) -> Dict[str, Any]:
        """Muxes visual stream with voiceover audio and optional ducked BGM.
        
        Args:
            video_path: Source MP4 video (silent or with raw audio).
            audio_path: Voiceover speech audio (e.g. Edge-TTS MP3).
            output_path: Destination MP4 file.
            bgm_path: Optional background music track.
            bgm_volume: Relative volume for BGM (0.10 - 0.20 for speech clarity).
            vo_volume: Relative volume for voiceover (default 1.0).
            target_duration: Optional enforced output duration in seconds.
        """
        video_path = Path(video_path).resolve()
        audio_path = Path(audio_path).resolve()
        output_path = Path(output_path).resolve()

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio voiceover file not found: {audio_path}")

        ffmpeg_bin = cls.get_ffmpeg_binary()
        v_info = cls.probe_file(video_path)
        a_info = cls.probe_file(audio_path)

        v_dur = v_info.get("duration", 10.0)
        a_dur = a_info.get("duration", 10.0)
        final_dur = target_duration or max(v_dur, a_dur)

        logger.info(
            "Muxing media -> Video: %.2fs (%s) | Audio: %.2fs (%s) -> Target: %.2fs",
            v_dur, video_path.name, a_dur, audio_path.name, final_dur
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp_out = output_path.with_name(f"{output_path.stem}_mux_tmp.mp4")

        # Command construction
        cmd = [ffmpeg_bin, "-y"]

        # If audio is longer than video, loop video to cover speech
        if a_dur > v_dur + 0.5 and not target_duration:
            # Loop video stream to match audio length
            cmd.extend(["-stream_loop", "-1", "-i", str(video_path)])
            cmd.extend(["-i", str(audio_path)])
        else:
            cmd.extend(["-i", str(video_path)])
            cmd.extend(["-i", str(audio_path)])

        if bgm_path and Path(bgm_path).exists():
            cmd.extend(["-stream_loop", "-1", "-i", str(Path(bgm_path).resolve())])
            # Filter complex: voiceover at 1.0, BGM ducked at 0.15, mixed
            filter_complex = (
                f"[1:a]volume={vo_volume}[vo];"
                f"[2:a]volume={bgm_volume}[bgm];"
                f"[vo][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "0:v:0",
                "-map", "[aout]",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "22",
                "-c:a", "aac",
                "-b:a", "192k",
                "-t", f"{final_dur:.2f}",
                "-movflags", "+faststart",
                str(temp_out)
            ])
        else:
            # Voiceover only (no BGM)
            cmd.extend([
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "22",
                "-c:a", "aac",
                "-b:a", "192k",
                "-t", f"{final_dur:.2f}",
                "-movflags", "+faststart",
                str(temp_out)
            ])

        logger.debug("Executing FFmpeg mux: %s", " ".join(cmd))
        run_res = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if run_res.returncode != 0:
            logger.error("FFmpeg muxing failed: %s", run_res.stderr)
            if temp_out.exists():
                temp_out.unlink()
            raise RuntimeError(f"FFmpeg muxing failed with code {run_res.returncode}: {run_res.stderr[-300:]}")

        # Atomic replace target
        if temp_out.exists():
            if output_path.exists():
                output_path.unlink()
            shutil.move(str(temp_out), str(output_path))

        out_info = cls.probe_file(output_path)
        logger.info(
            "Successfully muxed final video: %s (%.2f MB, %.2fs, has_audio=%s)",
            output_path.name,
            output_path.stat().st_size / (1024 * 1024),
            out_info.get("duration", 0.0),
            out_info.get("has_audio", False)
        )

        return {
            "success": True,
            "output_path": str(output_path),
            "duration": out_info.get("duration", 0.0),
            "has_audio": out_info.get("has_audio", False),
            "size_mb": round(output_path.stat().st_size / (1024 * 1024), 2)
        }

"""Unit tests for the MediaMuxer FFmpeg Synchronization Engine."""

import subprocess
from pathlib import Path
import pytest
from src.media_muxer import MediaMuxer


@pytest.fixture
def dummy_media_files(tmp_path):
    """Generates synthetic 2-second silent MP4 and 2-second audio MP3 for testing."""
    ffmpeg_bin = MediaMuxer.get_ffmpeg_binary()
    video_file = tmp_path / "test_video.mp4"
    audio_file = tmp_path / "test_audio.mp3"

    # Generate 2-second silent test video (lavfi testsrc)
    cmd_v = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=24",
        "-c:v", "libx264", "-preset", "ultrafast",
        str(video_file)
    ]
    subprocess.run(cmd_v, capture_output=True, check=True)

    # Generate 2-second sine wave audio
    cmd_a = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
        "-c:a", "libmp3lame",
        str(audio_file)
    ]
    subprocess.run(cmd_a, capture_output=True, check=True)

    return video_file, audio_file


def test_probe_media(dummy_media_files):
    video_file, audio_file = dummy_media_files
    
    v_info = MediaMuxer.probe_file(video_file)
    assert v_info["exists"] is True
    assert v_info["has_video"] is True
    assert 1.8 <= v_info["duration"] <= 2.2

    a_info = MediaMuxer.probe_file(audio_file)
    assert a_info["exists"] is True
    assert a_info["has_audio"] is True
    assert a_info["has_video"] is False
    assert 1.8 <= a_info["duration"] <= 2.2


def test_mux_video_and_audio(dummy_media_files, tmp_path):
    video_file, audio_file = dummy_media_files
    out_file = tmp_path / "muxed_output.mp4"

    res = MediaMuxer.mux_video_and_audio(
        video_path=video_file,
        audio_path=audio_file,
        output_path=out_file
    )

    assert res["success"] is True
    assert out_file.exists()
    assert res["has_audio"] is True
    assert 1.8 <= res["duration"] <= 2.5
    assert MediaMuxer.verify_has_audio(out_file) is True


def test_verify_has_audio_negative(dummy_media_files):
    video_file, _ = dummy_media_files
    # Video before muxing is silent (no audio track)
    assert MediaMuxer.verify_has_audio(video_file) is False

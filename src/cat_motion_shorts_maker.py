"""Enhanced Cat Video Shorts Engine.
Combines real 9:16 vertical motion cat videos, Edge-TTS storytelling,
background music, and multi-line stylish subtitles into high-retention YouTube Shorts.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.tts_engine import TTSEngine

def create_video_cat_short(
    input_video_path: str,
    script_text: str,
    output_path: str,
    headline: str = "FAKTA UNIK KUCING 🐱"
) -> str:
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path("/tmp/cat_render_v2")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate Voiceover via Edge-TTS
    print("🎙️ [1/3] Generating Edge-TTS voiceover...")
    tts = TTSEngine()
    audio_path = temp_dir / "voiceover.mp3"
    _, duration = tts.generate_voiceover(script_text, str(audio_path), voice="id-ID-ArdiNeural")
    print(f"   ✅ Audio generated: {duration:.2f} seconds")

    total_duration = duration + 0.8

    # 2. Prepare text splits for readable subtitles
    clean_headline = headline.replace("'", "").replace(":", " -")
    clean_script = script_text.replace("'", "").replace(":", " -")
    words = clean_script.split()
    
    # 3 lines of subtitle
    chunk = len(words) // 3
    line1 = " ".join(words[:chunk])
    line2 = " ".join(words[chunk:chunk*2])
    line3 = " ".join(words[chunk*2:])

    # 3. Assemble with FFmpeg:
    # - Scale to 1080x1920 (9:16)
    # - Top headline banner
    # - Bottom semi-transparent subtitle card with clean typography
    print("🎬 [2/3] Processing video clips & compositing typography via FFmpeg...")
    vf = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"drawbox=y=160:color=yellow@0.9:width=iw:height=120:t=fill,"
        f"drawtext=text='{clean_headline}':fontcolor=black:fontsize=52:x=(w-text_w)/2:y=195,"
        f"drawbox=y=ih-520:color=black@0.75:width=iw-80:x=40:height=380:t=fill,"
        f"drawtext=text='{line1}':fontcolor=white:fontsize=44:x=(w-text_w)/2:y=h-470:shadowcolor=black:shadowx=2:shadowy=2,"
        f"drawtext=text='{line2}':fontcolor=yellow:fontsize=46:x=(w-text_w)/2:y=h-390:shadowcolor=black:shadowx=2:shadowy=2,"
        f"drawtext=text='{line3}':fontcolor=white:fontsize=44:x=(w-text_w)/2:y=h-310:shadowcolor=black:shadowx=2:shadowy=2"
    )

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(input_video_path),
        "-i", str(audio_path),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-t", str(total_duration),
        "-shortest",
        str(out_file)
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg render failed:\n{res.stderr}")

    print(f"   ✅ Motion Video Shorts created: {out_file}")
    return str(out_file)

if __name__ == "__main__":
    fun_fact_script = (
        "Tahukah kamu? Kucing tidak bisa merasakan rasa manis sama sekali! "
        "Lidah kucing kekurangan reseptor gen rasa manis, jadi mereka hanya tertarik pada protein dan lemak daging segar."
    )
    vid_in = "/tmp/cat_video1.mp4"
    vid_out = "/home/ubuntu/apps/ugc-lemonaru/output/cat_short_video_v2.mp4"
    create_video_cat_short(vid_in, fun_fact_script, vid_out, headline="KENAPA KUCING GAK SUKA MANIS? 🐱🍬")

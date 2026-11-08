"""Cat Shorts Production Engine.
Combines Edge-TTS Voiceover, dynamic cat facts, image panning/zooming (Ken Burns effect),
subtitles, and FFmpeg assembly into a complete 9:16 vertical MP4 video for YouTube Shorts.
"""

import os
import sys
import subprocess
from pathlib import Path
from src.tts_engine import TTSEngine

def build_cat_short(
    script_text: str,
    image_path: str,
    output_video_path: str,
    title_caption: str = "FAKTA KUCING OYEN 🐱"
) -> str:
    out_path = Path(output_video_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path("/tmp/cat_render")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate Voiceover via Edge-TTS
    print("🎙️ [1/3] Generating Edge-TTS voiceover...")
    tts = TTSEngine()
    audio_path = temp_dir / "voiceover.mp3"
    _, duration = tts.generate_voiceover(script_text, str(audio_path))
    print(f"   ✅ Audio generated: {duration:.2f} seconds")

    # 2. Build 9:16 Video with Ken Burns Zoom & Subtitle via FFmpeg
    print("🎬 [2/3] Rendering 9:16 vertical video via FFmpeg...")
    # Add 1 second buffer to duration
    video_duration = duration + 1.0
    fps = 30
    total_frames = int(video_duration * fps)

    # Escape title caption for ffmpeg drawtext
    clean_title = title_caption.replace("'", "").replace(":", "-")
    clean_script = script_text.replace("'", "").replace(":", "-")

    # Split script into 2 shorter lines for readability
    words = clean_script.split()
    mid = len(words) // 2
    line1 = " ".join(words[:mid])
    line2 = " ".join(words[mid:])

    # FFmpeg Filter Complex:
    # 1. Scale image to fill 1080x1920 (aspect ratio crop)
    # 2. Slow smooth zoom-in (Ken Burns)
    # 3. Draw black gradient/card for subtitles
    # 4. Draw Title and Subtitle text with border
    vf = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,"
        f"zoompan=z='min(zoom+0.0008,1.25)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps={fps},"
        f"drawbox=y=ih-500:color=black@0.6:width=iw:height=380:t=fill,"
        f"drawtext=text='{clean_title}':fontcolor=yellow:fontsize=56:x=(w-text_w)/2:y=h-460:shadowcolor=black:shadowx=3:shadowy=3,"
        f"drawtext=text='{line1}':fontcolor=white:fontsize=44:x=(w-text_w)/2:y=h-360:shadowcolor=black:shadowx=2:shadowy=2,"
        f"drawtext=text='{line2}':fontcolor=white:fontsize=44:x=(w-text_w)/2:y=h-290:shadowcolor=black:shadowx=2:shadowy=2"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-i", str(audio_path),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-t", str(video_duration),
        "-shortest",
        str(out_path)
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg render failed:\n{res.stderr}")

    print(f"   ✅ Video rendered successfully: {out_path}")
    return str(out_path)

if __name__ == "__main__":
    script = "Tahukah kamu? Kucing mendengkur bukan cuma saat bahagia, tapi juga untuk menyembuhkan luka dan menenangkan diri!"
    img = "/tmp/cat1.jpg"
    out = "/home/ubuntu/apps/ugc-lemonaru/output/cat_short_demo.mp4"
    build_cat_short(script, img, out)

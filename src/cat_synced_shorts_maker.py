"""Precision Subtitle & Motion Shorts Engine.
Generates word-accurate, synchronized dynamic animated subtitles
where the text appears exactly in sync with the audio sentence timing!
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path
import edge_tts

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))


def format_srt_time(seconds: float) -> str:
    millis = int((seconds - int(seconds)) * 1000)
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"


async def generate_speech_with_cues(text: str, audio_path: Path, srt_path: Path, voice: str = "id-ID-ArdiNeural") -> float:
    communicate = edge_tts.Communicate(text, voice)
    cues = []
    
    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                start = chunk["offset"] / 10_000_000
                dur = chunk["duration"] / 10_000_000
                cues.append({
                    "start": start,
                    "end": start + dur,
                    "text": chunk["text"].strip()
                })

    # Write clean ASS or SRT subtitle
    # We will write SRT
    with open(srt_path, "w", encoding="utf-8") as f:
        for idx, cue in enumerate(cues, 1):
            s_time = format_srt_time(cue["start"])
            e_time = format_srt_time(cue["end"])
            # Format text into max 4-5 words per line if long
            raw_t = cue["text"]
            words = raw_t.split()
            if len(words) > 5:
                mid = len(words) // 2
                display_t = " ".join(words[:mid]) + "\n" + " ".join(words[mid:])
            else:
                display_t = raw_t

            f.write(f"{idx}\n{s_time} --> {e_time}\n{display_t}\n\n")

    # Probe duration
    last_end = cues[-1]["end"] if cues else 10.0
    return last_end


def create_synchronized_cat_short(
    input_video: str,
    script_text: str,
    output_video: str,
    headline: str = "FAKTA KUCING 🐱"
) -> str:
    out_file = Path(output_video).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path("/tmp/sync_cat_render")
    temp_dir.mkdir(parents=True, exist_ok=True)

    audio_file = temp_dir / "audio.mp3"
    srt_file = temp_dir / "subtitles.srt"

    print("🎙️ [1/3] Generating Speech & Sentence Timings via Edge-TTS...")
    dur = asyncio.run(generate_speech_with_cues(script_text, audio_file, srt_file))
    print(f"   ✅ Audio and SRT generated! Total speech duration: {dur:.2f}s")

    total_duration = dur + 0.8

    # Create ASS style with subtitles filter for viral TikTok/Shorts font styling:
    # Yellow highlighted, bold, black outline, centered at bottom
    clean_headline = headline.replace("'", "").replace(":", " -")
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    sub_style = (
        "Fontname=DejaVu Sans,FontSize=18,Bold=1,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,"
        "BorderStyle=3,Outline=3,Shadow=1,MarginV=60,Alignment=2"
    )

    print("🎬 [2/3] Rendering Video with Synchronized Subtitles via FFmpeg...")
    vf = (
        f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"drawbox=y=160:color=yellow@0.95:width=iw:height=120:t=fill,"
        f"drawtext=fontfile='{font_path}':text='{clean_headline}':fontcolor=black:fontsize=52:x=(w-text_w)/2:y=195,"
        f"subtitles='{srt_file}':force_style='{sub_style}'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(input_video),
        "-i", str(audio_file),
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

    print(f"   ✅ Synchronized Video Shorts ready: {out_file}")
    return str(out_file)


if __name__ == "__main__":
    script = (
        "Tahukah kamu? Kucing tidak bisa merasakan rasa manis sama sekali! "
        "Lidah mereka kekurangan reseptor gen rasa manis. "
        "Itulah kenapa kucing cuma doyan protein dan daging segar!"
    )
    vid_in = "/tmp/cat_video1.mp4"
    vid_out = "/home/ubuntu/apps/ugc-lemonaru/output/cat_short_synced_v3.mp4"
    create_synchronized_cat_short(vid_in, script, vid_out, headline="KUCING GAK BISA RASA MANIS?! 🐱🍬")

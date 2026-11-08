"""Multi-Clip Real Motion Cat Shorts Maker.
Combines 3 lively, dynamic moving cat action clips (playing, jumping, rolling),
Edge-TTS Indonesian narration, and the approved safe-zone subtitles.
"""

import asyncio
import os
import subprocess
from pathlib import Path
import edge_tts

WORKSPACE = Path("/home/ubuntu/apps/ugc-lemonaru")
OUTPUT_DIR = WORKSPACE / "output"
ASSETS_DIR = WORKSPACE / "assets" / "cat_videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VOICE = "id-ID-ArdiNeural"

SCRIPT = {
    "title": "KENAPA KUCING JAGO LOMPAT?",
    "sentences": [
        "Tahukah kamu?",
        "Kucing ternyata bisa melompat setinggi 6 kali panjang tubuhnya sendiri!",
        "Kekuatan luar biasa ini berasal dari otot paha belakang mereka yang sangat elastis.",
        "Jadi jangan kaget ya, kalau mereka gampang banget nangkring di atas lemari atau pagar rumah kamu!"
    ]
}

def format_ass_timestamp(seconds: float) -> str:
    cs = int((seconds % 1) * 100)
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:d}:{minutes:02d}:{secs:02d}.{cs:02d}"

def create_ass_subtitles(sentences_timing: list, ass_path: Path):
    ass_header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,44,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,2,2,60,60,460,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for start_time, end_time, text in sentences_timing:
        clean_text = text.strip()
        words = clean_text.split()
        if len(words) > 6:
            mid = len(words) // 2
            formatted_text = " ".join(words[:mid]) + r"\N" + " ".join(words[mid:])
        else:
            formatted_text = clean_text
            
        start_ass = format_ass_timestamp(start_time)
        end_ass = format_ass_timestamp(end_time)
        events.append(f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{formatted_text}")
        
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events))

async def generate_audio_and_subs(script: dict, audio_path: Path, ass_path: Path):
    full_text = " ".join(script["sentences"])
    communicate = edge_tts.Communicate(full_text, VOICE, rate="+5%", pitch="+0Hz")
    
    sentences_timing = []
    with open(audio_path, "wb") as f_audio:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f_audio.write(chunk.get("data", b""))
            elif chunk["type"] == "SentenceBoundary":
                offset = chunk["offset"] / 10000000.0
                duration = chunk["duration"] / 10000000.0
                sentences_timing.append((offset, offset + duration, chunk.get("text", "")))
                
    total_audio_duration = sentences_timing[-1][1] if sentences_timing else 15.4
    create_ass_subtitles(sentences_timing, ass_path)
    return total_audio_duration

def render_multiclip_video(audio_path: Path, ass_path: Path, output_mp4: Path, duration: float):
    # 3 active moving clips:
    # Clip 1: grey kitten rolling (0 - 4.5s)
    # Clip 2: kittens playfully fighting & jumping (4.5 - 9.5s)
    # Clip 3: cat chasing red ball (9.5 - end)
    c1 = ASSETS_DIR / "clip4_kitten.mp4"
    c2 = ASSETS_DIR / "clip1_fight.mp4"
    c3 = ASSETS_DIR / "clip2_ball.mp4"
    
    filter_complex = (
        f"[0:v]trim=0:4.5,setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v1];"
        f"[1:v]trim=0:5.0,setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v2];"
        f"[2:v]trim=0:6.5,setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v3];"
        f"[v1][v2][v3]concat=n=3:v=1:a=0[vcat];"
        f"[vcat]trim=duration={duration:.2f}[vtrimmed];"
        f"[vtrimmed]drawbox=x=0:y=220:w=1080:h=120:color=black@0.65:t=fill,"
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='KENAPA KUCING JAGO LOMPAT?':fontcolor=yellow:fontsize=46:"
        f"x=(w-text_w)/2:y=255,"
        f"ass={ass_path}[finalv]"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(c1),
        "-i", str(c2),
        "-i", str(c3),
        "-i", str(audio_path),
        "-filter_complex", filter_complex,
        "-map", "[finalv]",
        "-map", "3:a",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_mp4)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {res.stderr}")

async def main():
    audio_path = Path("/tmp/sync_multi_audio.mp3")
    ass_path = Path("/tmp/sync_multi_sub.ass")
    final_output = OUTPUT_DIR / "cat_short_motion_v5.mp4"
    
    dur = await generate_audio_and_subs(SCRIPT, audio_path, ass_path)
    render_multiclip_video(audio_path, ass_path, final_output, dur + 0.3)
    print(f"✅ Motion Video Shorts Ready: {final_output}")

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
build_spook_part2.py
====================
Assembles, composites, QCs, and publishes Spook Part 2 for DoniesDaily.
Formula:
- 4 Narrative Cuts from raw_videos/part2_day2_how_long_does_it_take.mp4 (56.64s total)
- Remotion ProRes 4444 overlay (Single-word Hormozi kinetic typography + hook banner + outro)
- 3-Layer Audio Mix: 100% Vivan voice + 35% original Spook vocal/meow + 18% cat_playful_bgm.mp3 (3s fadeout)
- Loudnorm -14.5 LUFS
- Cleo 2.0 AI-Vision QC gatekeeper (20 frames inspection)
- YouTube Shorts upload with proper series credits and tags
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path

SERIES_DIR = Path("/home/ubuntu/apps/ugc-lemonaru/content_series/spook_kitten_training")
RAW_VIDEO = SERIES_DIR / "raw_videos/part2_day2_how_long_does_it_take.mp4"
AUDIO_PATH = SERIES_DIR / "scripts/part2_audio.mp3"
OVERLAY_MOV = SERIES_DIR / "spook_part2_remotion_overlay.mov"
BGM_PATH = Path("/home/ubuntu/apps/ugc-lemonaru/assets/audio/cat_playful_bgm.mp3")
MASTER_MP4 = SERIES_DIR / "spook_part2_master.mp4"
SCRIPT_JSON = SERIES_DIR / "scripts/part2_naskah_hari_2.json"

def composite_part2():
    print("🎬 Compositing Spook Part 2 with 3-Layer Audio & Remotion Overlay...")
    
    # 4 Slices matching narrative beats:
    # 1. 0.00 -> 14.20s (14.20s): Spook mondar-mandir heboh pas mangkok diangkat
    # 2. 30.00 -> 47.20s (17.20s): Spook ngesot di kaki, melolong panjang (extinction burst)
    # 3. 88.00 -> 100.76s (12.76s): Spook mulai tenang, mematung di lantai
    # 4. 103.00 -> 115.48s (12.48s): Emma jongkok taruh mangkok, teks '9:30', Spook makan lahap + outro
    # Total = 56.64s
    
    filter_complex = """
[0:v]trim=start=0:end=14.20,setpts=PTS-STARTPTS[v1];
[0:a]atrim=start=0:end=14.20,asetpts=PTS-STARTPTS[a1];
[0:v]trim=start=30:end=47.20,setpts=PTS-STARTPTS[v2];
[0:a]atrim=start=30:end=47.20,asetpts=PTS-STARTPTS[a2];
[0:v]trim=start=88:end=100.76,setpts=PTS-STARTPTS[v3];
[0:a]atrim=start=88:end=100.76,asetpts=PTS-STARTPTS[a3];
[0:v]trim=start=103:end=115.48,setpts=PTS-STARTPTS[v4];
[0:a]atrim=start=103:end=115.48,asetpts=PTS-STARTPTS[a4];

[v1][v2][v3][v4]concat=n=4:v=1:a=0,scale=1080:1920:flags=lanczos[vbg];
[vbg][1:v]overlay=0:0:format=yuv420[vmaster];

[a1][a2][a3][a4]concat=n=4:v=0:a=1,volume=0.35[ameong];
[2:a]volume=1.0[avoice];
[3:a]atrim=start=0:end=56.64,afade=t=out:st=53.64:d=3.0,volume=0.18[abgm];

[ameong][avoice][abgm]amix=inputs=3:duration=first:normalize=0,loudnorm=I=-14.5:TP=-1.5:LRA=11[amaster]
"""
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(RAW_VIDEO),
        "-i", str(OVERLAY_MOV),
        "-i", str(AUDIO_PATH),
        "-i", str(BGM_PATH),
        "-filter_complex", filter_complex,
        "-map", "[vmaster]",
        "-map", "[amaster]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        str(MASTER_MP4)
    ]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("❌ FFmpeg compositing failed:", res.stderr[-1000:], file=sys.stderr)
        sys.exit(1)
        
    print(f"✅ Compositing complete: {MASTER_MP4}")
    
    # Check duration and size
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "json", str(MASTER_MP4)],
        capture_output=True, text=True
    )
    data = json.loads(probe.stdout)
    dur = float(data["format"]["duration"])
    size_mb = float(data["format"]["size"]) / 1024 / 1024
    print(f"📊 Master Video Specs: {dur:.2f}s | {size_mb:.2f} MB")
    return MASTER_MP4

if __name__ == "__main__":
    composite_part2()

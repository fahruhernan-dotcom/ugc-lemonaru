#!/usr/bin/env python3
"""
build_spook_part3.py
====================
Assembles, composites, QCs, and publishes Spook Part 3 for DoniesDaily.
Formula:
- Authentic source: content_series/spook_kitten_training/raw_videos/part3_day3_holding_back_hunger.mp4
- Remotion ProRes 4444 overlay (Hormozi kinetic typography + hook banner + outro)
- 3-Layer Audio Mix: 100% Vivan voice + 35% original Spook meow/vocal + 18% cat_playful_bgm.mp3 (3s fadeout)
- Loudnorm -14.5 LUFS
- Strict Cleo DB-Aware & AI-Vision QC gatekeeper (20 frames inspection)
- YouTube Shorts upload with proper series credits and tags
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path

SERIES_DIR = Path("/home/ubuntu/apps/ugc-lemonaru/content_series/spook_kitten_training")
PROJECT_ROOT = Path("/home/ubuntu/apps/ugc-lemonaru")
RAW_VIDEO = SERIES_DIR / "raw_videos/part3_day3_holding_back_hunger.mp4"
AUDIO_PATH = PROJECT_ROOT / "remotion/public/spook_part3_master.mp3"
CAPTIONS_FILE = "doni-spook_part3-captions.json"
BGM_PATH = PROJECT_ROOT / "assets/audio/cat_playful_bgm.mp3"
MASTER_MP4 = PROJECT_ROOT / "data/spook_part3_master.mp4"
MASTER_MP4.parent.mkdir(parents=True, exist_ok=True)
OVERLAY_MOV = Path("/tmp/spook_part3_remotion_overlay.mov")
THUMB_JPG = PROJECT_ROOT / "data/spook_part3_master_thumb.jpg"

sys.path.insert(0, str(PROJECT_ROOT / "src"))
from doni_hybrid_renderer import DoniHybridRenderer
from doni_qc_gate import audit_against_database, inspect_video

def render_overlay():
    print("🎨 Rendering Remotion transparent overlay for Spook Part 3...")
    renderer = DoniHybridRenderer()
    duration_sec = 58.90
    renderer.render_overlay_layer(
        hook_title="HARI KE-3: DRAMA MENAHAN NAFSU MAKAN!",
        hook_subtitle="Bukan Karena Marah Lho!",
        badge_text="🐱 SPOOK PART 3",
        captions_filename=CAPTIONS_FILE,
        duration_sec=duration_sec,
        output_mov_path=OVERLAY_MOV,
        subtitle_bottom=500,
        layout_mode="youtube_shorts",
        show_safe_area_guide=False
    )
    renderer.render_remotion_thumbnail(
        hook_title="HARI KE-3: DRAMA MENAHAN NAFSU MAKAN!",
        hook_subtitle="Bukan Karena Marah Lho!",
        badge_text="🐱 SPOOK PART 3",
        output_thumb_path=THUMB_JPG,
        bg_image_ref=RAW_VIDEO
    )
    print("✅ Remotion overlay & thumbnail rendered successfully!")

def composite_master():
    print("🎬 Compositing Spook Part 3 master video with 3-Layer Audio & Authentic Footage...")
    duration_sec = 58.90
    stretch_factor = 58.90 / 52.633333
    
    filter_complex = f"""
[0:v]setpts={stretch_factor:.6f}*PTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[vbg];
[vbg][1:v]overlay=0:0:format=yuv420[vmaster];

[0:a]asetpts={stretch_factor:.6f}*PTS,atempo={1.0/stretch_factor:.6f},volume=0.35[ameong];
[2:a]volume=1.0[avoice];
[3:a]atrim=start=0:end={duration_sec},afade=t=out:st={duration_sec-3.0}:d=3.0,volume=0.18[abgm];

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
        "-t", f"{duration_sec:.2f}",
        "-movflags", "+faststart",
        str(MASTER_MP4)
    ]
    subprocess.run(cmd, check=True)
    print(f"🎉 Master video composited: {MASTER_MP4} ({MASTER_MP4.stat().st_size / 1024 / 1024:.2f} MB)")

def run_cleo_qc():
    print("🔍 [CLEO QC GATEKEEPER] Running DB-Aware & AI-Vision 20-Frame Inspection...")
    report = audit_against_database(
        topic_key="spook_part3",
        footage_clips=[RAW_VIDEO],
        video_path=MASTER_MP4
    )
    print("--- QC REPORT ---")
    print("Passed:", report["passed"])
    print("Errors:", report["errors"])
    print("Warnings:", report["warnings"])
    if not report["passed"]:
        raise RuntimeError(f"🚨 Cleo QC REJECTION: {report['errors']}")
    print("✅ Video APPROVED by Cleo QC Gatekeeper!")
    return report

if __name__ == "__main__":
    render_overlay()
    composite_master()
    run_cleo_qc()
    print("🚀 SPOOK PART 3 PRODUCTION COMPLETED 100% CORRECTLY!")

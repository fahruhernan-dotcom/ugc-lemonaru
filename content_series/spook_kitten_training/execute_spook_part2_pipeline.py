#!/usr/bin/env python3
"""
execute_spook_part2_pipeline.py
===============================
Complete end-to-end automation for DoniesDaily Spook Part 2:
1. Wait for Remotion overlay render
2. Composite video (cuts, 3-layer audio, overlay)
3. Cleo 2.0 AI-Vision QC Gatekeeper
4. YouTube Shorts upload via Data API v3
5. Supabase ai_brain sync
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path("/home/ubuntu/apps/ugc-lemonaru")
sys.path.insert(0, str(PROJECT_ROOT))

from src.youtube_api_publisher import YouTubeAPIPublisher
from src.doni_ai_qc import audit_video_narrative_and_quality

SERIES_DIR = PROJECT_ROOT / "content_series/spook_kitten_training"
OVERLAY_MOV = SERIES_DIR / "spook_part2_remotion_overlay.mov"
BUILD_SCRIPT = SERIES_DIR / "build_spook_part2.py"
MASTER_MP4 = SERIES_DIR / "spook_part2_master.mp4"
SCRIPT_JSON = SERIES_DIR / "scripts/part2_naskah_hari_2.json"

def wait_for_overlay():
    print("⏳ Waiting for Remotion overlay render to finish...")
    # Poll until file exists and process is done
    while True:
        # Check if remotion process is still running
        ps = subprocess.run(["pgrep", "-f", "remotion render DoniOverlay"], capture_output=True, text=True)
        if not ps.stdout.strip():
            if OVERLAY_MOV.exists() and OVERLAY_MOV.stat().st_size > 1000000:
                print(f"✅ Remotion overlay ready: {OVERLAY_MOV} ({OVERLAY_MOV.stat().st_size / 1024 / 1024:.2f} MB)")
                break
        time.sleep(5)

def run_compositing():
    print("🚀 Running video compositing...")
    res = subprocess.run([sys.executable, str(BUILD_SCRIPT)], capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print("❌ Compositing failed:", res.stderr, file=sys.stderr)
        sys.exit(1)

def run_cleo_qc():
    print("🔍 [CLEO 2.0] Running AI-Vision 20-Frame QC Gatekeeper...")
    with open(SCRIPT_JSON, "r", encoding="utf-8") as f:
        meta = json.load(f)

    report = audit_video_narrative_and_quality(
        video_path=MASTER_MP4,
        script_text=meta.get("script_text", ""),
        title=meta.get("title", "HARI KE-2: PECAH REKOR 9 MENIT 30 DETIK!"),
        hook_banner="HARI KE-2: PECAH REKOR 9 MENIT 30 DETIK!"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report.get("passed"):
        print(f"❌ Video rejected by Cleo 2.0 (Score: {report.get('overall_score')})", file=sys.stderr)
        sys.exit(1)
    print(f"✅ Video APPROVED by Cleo 2.0 (Score: {report.get('overall_score')}/100)")
    return report

def upload_and_sync(qc_report):
    print("📤 Uploading to YouTube Shorts...")
    with open(SCRIPT_JSON, "r", encoding="utf-8") as f:
        meta = json.load(f)

    publisher = YouTubeAPIPublisher()
    upload_res = publisher.upload_short(
        video_path=str(MASTER_MP4),
        title=meta.get("title", "HARI KE-2: PECAH REKOR 9 MENIT 30 DETIK! 🐱💥"),
        description=meta.get("description", "Kelanjutan latihan Spook kitten agar berhenti rewel!"),
        tags=meta.get("tags", ["Shorts", "Kucing", "Cat", "DoniesDaily", "Spook", "LatihanKucing"]),
        privacy_status="public",
        category_id="15"
    )

    if not upload_res.get("success"):
        print("❌ YouTube upload failed:", upload_res.get("error"), file=sys.stderr)
        sys.exit(1)

    video_id = upload_res["video_id"]
    short_url = upload_res["short_url"]
    print(f"🎉 Upload successful! URL: {short_url}")

    # Record to Supabase
    print("💾 Recording to Supabase ai_brain...")
    tags_list = meta.get("tags", ["Shorts", "Kucing", "Cat", "DoniesDaily", "Spook", "LatihanKucing", "Anabul", "CatTraining", "FunnyCat"])
    tags_sql = "ARRAY[" + ", ".join(f"'{t}'" for t in tags_list) + "]::text[]"

    record_sql = f"""
    INSERT INTO ai_brain.doniesdaily_posts (
        video_id, title, hook, story_text, banner_title, tags, duration_sec, privacy_status, short_url, posted_at
    ) VALUES (
        '{video_id}',
        '{meta.get("title").replace("'", "''")}',
        '{meta.get("title").replace("'", "''")}',
        '{meta.get("script_text").replace("'", "''")}',
        'HARI KE-2: PECAH REKOR 9 MENIT 30 DETIK!',
        {tags_sql},
        56.64,
        'public',
        '{short_url}',
        now()
    ) ON CONFLICT (video_id) DO NOTHING;

    UPDATE ai_brain.doniesdaily_content_ideas 
    SET status = 'posted', updated_at = now()
    WHERE topic_key = 'spook_part2';

    UPDATE ai_brain.cadence_tasks
    SET last_run_at = now()
    WHERE task_key = 'business.doni_midday_serial';

    INSERT INTO ai_brain.cadence_logs (
        task_key, fired_at, status, action_result
    ) VALUES (
        'business.doni_midday_serial',
        now(),
        'SUCCESS',
        '{{"video_id": "{video_id}", "url": "{short_url}", "series": "spook_part2"}}'::jsonb
    );
    """

    res = subprocess.run([
        "docker", "exec", "-i", "supabase-db", "psql", "-U", "postgres", "-d", "postgres", "-c", record_sql
    ], capture_output=True, text=True)
    if res.returncode == 0:
        print("✅ Supabase DB synced successfully!")
    else:
        print("⚠️ Supabase sync warning:", res.stderr)

if __name__ == "__main__":
    wait_for_overlay()
    run_compositing()
    qc = run_cleo_qc()
    upload_and_sync(qc)

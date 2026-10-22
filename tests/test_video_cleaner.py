"""Unit tests for VideoLifecycleManager and garbage cleaner."""

from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import pytest
import time

from src.config import (
    ROOT_DIR,
    DATA_DIR,
    PACKAGES_DIR,
    PACKAGES_PENDING_DIR,
    PACKAGES_POSTED_DIR,
    TEMP_DIR,
    OUTPUT_DIR,
)
from src.video_cleaner import VideoLifecycleManager, SecurityViolationError


def test_strict_whitelist_guard():
    """Verifies that security validation allows whitelisted paths and violently rejects sensitive assets."""
    # Whitelisted paths should pass
    safe_posted = PACKAGES_POSTED_DIR / "dummy_pkg"
    safe_temp = TEMP_DIR / "temp_clip.mp4"
    safe_out = OUTPUT_DIR / "debug_screenshot.png"

    assert VideoLifecycleManager.validate_safety(safe_posted) == safe_posted.resolve()
    assert VideoLifecycleManager.validate_safety(safe_temp) == safe_temp.resolve()
    assert VideoLifecycleManager.validate_safety(safe_out) == safe_out.resolve()

    # Sensitive paths must raise SecurityViolationError
    with pytest.raises(SecurityViolationError):
        VideoLifecycleManager.validate_safety(ROOT_DIR / ".env")

    with pytest.raises(SecurityViolationError):
        VideoLifecycleManager.validate_safety(ROOT_DIR / "src" / "models.py")

    with pytest.raises(SecurityViolationError):
        VideoLifecycleManager.validate_safety(DATA_DIR / "tiktok.db")

    with pytest.raises(SecurityViolationError):
        VideoLifecycleManager.validate_safety(DATA_DIR / "templates" / "velora_official.jpg")

    with pytest.raises(SecurityViolationError):
        VideoLifecycleManager.validate_safety(ROOT_DIR)


def test_in_flight_protection(tmp_path):
    """Verifies that files currently being rendered/written are protected by grace period or lockfile."""
    test_file = tmp_path / "rendering_clip.mp4"
    test_file.write_bytes(b"video bytes")

    # Fresh file (<15 mins) should be marked in-flight
    assert VideoLifecycleManager.is_in_flight(test_file, grace_minutes=15) is True

    # Artificially age the file to 2 hours ago
    two_hours_ago = time.time() - (2 * 3600)
    os.utime(test_file, (two_hours_ago, two_hours_ago))
    assert VideoLifecycleManager.is_in_flight(test_file, grace_minutes=15) is False

    # Adding a lockfile should protect it even if old
    lock_file = test_file.with_suffix(".mp4.lock")
    lock_file.write_text("locked")
    assert VideoLifecycleManager.is_in_flight(test_file, grace_minutes=15) is True


def test_mark_as_posted_transition(tmp_path):
    """Verifies moving package from pending to posted and updating metadata."""
    # Create dummy package in pending
    pkg_name = f"PKG_TEST_{int(time.time())}"
    pkg_dir = PACKAGES_PENDING_DIR / pkg_name
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "video.mp4").write_bytes(b"dummy video")
    (pkg_dir / "metadata.json").write_text(json.dumps({"pipeline_stage": "PENDING"}), encoding="utf-8")

    try:
        dest_dir = VideoLifecycleManager.mark_as_posted(pkg_dir, status_label="STAGED_AS_DRAFT")
        assert dest_dir.parent == PACKAGES_POSTED_DIR
        assert dest_dir.exists()
        assert not pkg_dir.exists()

        meta = json.loads((dest_dir / "metadata.json").read_text(encoding="utf-8"))
        assert meta["pipeline_stage"] == "COMPLETED_AND_POSTED"
        assert meta["publication_status"] == "STAGED_AS_DRAFT"
        assert "posted_at" in meta
    finally:
        # Cleanup
        target = PACKAGES_POSTED_DIR / pkg_name
        if target.exists():
            import shutil
            shutil.rmtree(target)


def test_clean_expired_videos_dry_run_and_actual():
    """Verifies retention policy: dry-run reports without deleting, real execution deletes expired only."""
    import shutil

    # Create dummy expired posted package (>72 hours old)
    old_pkg = PACKAGES_POSTED_DIR / f"PKG_OLD_{int(time.time())}"
    old_pkg.mkdir(parents=True, exist_ok=True)
    (old_pkg / "video.mp4").write_bytes(b"12345" * 1000)
    old_time = time.time() - (80 * 3600)  # 80 hours ago
    (old_pkg / "metadata.json").write_text(
        json.dumps({"posted_at": (datetime.now(timezone.utc) - timedelta(hours=80)).isoformat()}),
        encoding="utf-8"
    )
    os.utime(old_pkg, (old_time, old_time))

    # Create dummy fresh posted package (1 hour old)
    fresh_pkg = PACKAGES_POSTED_DIR / f"PKG_FRESH_{int(time.time())}"
    fresh_pkg.mkdir(parents=True, exist_ok=True)
    (fresh_pkg / "video.mp4").write_bytes(b"fresh video content")
    fresh_time = time.time() - (2 * 3600)  # 2 hours ago (past 15-min grace, but well within 72h retention)
    os.utime(fresh_pkg, (fresh_time, fresh_time))

    # Create dummy expired temp file (>24 hours old)
    old_temp = TEMP_DIR / f"stale_clip_{int(time.time())}.mp4"
    old_temp.write_bytes(b"stale temp clip")
    os.utime(old_temp, (old_time, old_time))

    try:
        # 1. Dry run
        dry_res = VideoLifecycleManager.clean_expired_videos(dry_run=True)
        assert dry_res["dry_run"] is True
        assert old_pkg.name in dry_res["deleted_posted_packages"]
        assert fresh_pkg.name not in dry_res["deleted_posted_packages"]
        assert dry_res["reclaimed_bytes"] > 0
        # Files should still exist
        assert old_pkg.exists()
        assert fresh_pkg.exists()
        assert old_temp.exists()

        # 2. Real execution
        real_res = VideoLifecycleManager.clean_expired_videos(dry_run=False)
        assert real_res["dry_run"] is False
        assert old_pkg.name in real_res["deleted_posted_packages"]
        # Old files deleted
        assert not old_pkg.exists()
        assert not old_temp.exists()
        # Fresh package remains
        assert fresh_pkg.exists()

    finally:
        if old_pkg.exists():
            shutil.rmtree(old_pkg)
        if fresh_pkg.exists():
            shutil.rmtree(fresh_pkg)
        if old_temp.exists():
            old_temp.unlink()


def test_storage_breakdown():
    """Verifies that storage breakdown returns coherent metrics."""
    breakdown = VideoLifecycleManager.get_storage_breakdown()
    assert "pending" in breakdown
    assert "posted" in breakdown
    assert "temp" in breakdown
    assert "output" in breakdown
    assert "total_mb" in breakdown
    assert "max_storage_mb" in breakdown
    assert "usage_percent" in breakdown
    assert isinstance(breakdown["total_mb"], float)

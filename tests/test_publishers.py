"""Tests for TikTok publishers (Playwright and Selenium operators)."""

from pathlib import Path
from src.tiktok_browser_operator import TikTokBrowserOperator
from src.tiktok_selenium_operator import TikTokSeleniumOperator
from publisher import find_latest_package


def test_publisher_find_latest_package():
    latest = find_latest_package(require_video=True)
    if not latest:
        import pytest
        pytest.skip("No staged package in ready_to_publish/ yet")
    assert latest != ""
    assert Path(latest).exists()
    assert (Path(latest) / "video.mp4").exists()
    assert (Path(latest) / "caption.txt").exists()


def test_browser_operator_init():
    op = TikTokBrowserOperator()
    assert op.port == 9222
    assert op.profile_dir.exists()


def test_selenium_operator_init():
    op = TikTokSeleniumOperator()
    assert op.profile_dir.exists()


def test_upload_missing_package():
    op = TikTokBrowserOperator()
    res = op.prepare_package_upload("non_existent_package_dir")
    assert res["status"] == "ERROR"
    assert "not found" in res["message"].lower()


def test_operator_aigc_and_draft_methods():
    pw_op = TikTokBrowserOperator()
    assert hasattr(pw_op, "toggle_aigc_disclosure")
    assert hasattr(pw_op, "save_as_draft")

    sel_op = TikTokSeleniumOperator()
    assert hasattr(sel_op, "toggle_aigc_disclosure")
    assert hasattr(sel_op, "save_as_draft")


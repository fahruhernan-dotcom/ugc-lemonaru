"""Unit tests for Google Flow Agent & Selenium Operator."""

from pathlib import Path
import pytest

from src.flow_adapter import GoogleFlowAdapter, FlowAuthError
from src.flow_selenium_operator import GoogleFlowSeleniumOperator
from src.config import FLOW_AGENT_DIR, FLOW_BIN_PATH, FLOW_EXTENSION_DIR, DATA_DIR


def test_flow_paths_and_binary_existence():
    """Verifies that Google Flow Agent repository paths and binary are properly detected."""
    assert FLOW_AGENT_DIR.exists(), f"FLOW_AGENT_DIR should exist at {FLOW_AGENT_DIR}"
    assert FLOW_BIN_PATH.exists(), f"FLOW_BIN_PATH should exist at {FLOW_BIN_PATH}"
    assert FLOW_EXTENSION_DIR.exists(), f"FLOW_EXTENSION_DIR should exist at {FLOW_EXTENSION_DIR}"
    assert (FLOW_EXTENSION_DIR / "manifest.json").exists(), "manifest.json must be present in extension folder"


def test_google_flow_selenium_operator_init():
    """Verifies GoogleFlowSeleniumOperator initial config and Drive D directories."""
    op = GoogleFlowSeleniumOperator()
    assert op.profile_dir == (DATA_DIR / "chrome_profile_google_flow").resolve()
    assert op.profile_dir.exists(), "Profile dir on Drive D must be created"
    assert op.extension_dir == FLOW_EXTENSION_DIR.resolve()
    assert op.cookies_dir.exists(), "Cookies dir must exist"
    assert op.driver is None, "Driver should not start eagerly before start_driver()"


def test_google_flow_adapter_doctor():
    """Verifies that doctor checks run and return valid diagnostic structure."""
    adapter = GoogleFlowAdapter()
    assert adapter.bin_path == FLOW_BIN_PATH.resolve()

    doctor_info = adapter.check_doctor()
    assert isinstance(doctor_info, dict)
    assert "checks" in doctor_info or "error" in doctor_info or "version" in doctor_info

    # Verify is_authenticated without crashing
    is_auth = adapter.is_authenticated()
    assert isinstance(is_auth, bool)


def test_google_flow_adapter_auth_guard():
    """Verifies that generation without session cookies raises FlowAuthError with actionable guidance."""
    adapter = GoogleFlowAdapter()
    if not adapter.is_authenticated():
        with pytest.raises(FlowAuthError) as exc_info:
            adapter.generate_video(prompt="A stylish luxury batik dress 9:16")
        assert "Google Flow cookies belum terpasang" in str(exc_info.value)


def test_generate_foundation_photos_mocked(tmp_path, monkeypatch):
    """Verifies that generate_foundation_photos creates both Foto 1 and Foto 2 with correct naming."""
    adapter = GoogleFlowAdapter()

    dummy_img = tmp_path / "mock_gen.jpg"
    dummy_img.write_text("fake image content")
    monkeypatch.setattr(adapter, "generate_image", lambda *args, **kwargs: dummy_img)
    monkeypatch.setattr("time.sleep", lambda *args, **kwargs: None)

    from src.models import Product
    prod = Product(
        product_id="GARMENT-05",
        name="CLASSY - TESSA Peplum Top Wanita Blouse Tanpa Lengan",
        category="fashion_peplum_top",
        price_idr=129000.0,
        commission_rate=0.15,
        shop_name="CLASSY Official"
    )

    res = adapter.generate_foundation_photos(prod, output_dir=tmp_path / "foundation")
    assert "close_up" in res
    assert "wide_silhouette" in res
    assert res["close_up"].exists()
    assert res["wide_silhouette"].exists()
    assert "garment_05_foundation_1_close.jpg" in res["close_up"].name
    assert "garment_05_foundation_2_wide.jpg" in res["wide_silhouette"].name

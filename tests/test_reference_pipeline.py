"""Unit tests for No-Face Chin-Down Reference Pipeline & Managers."""

from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from src.models import Product
from src.flow_prompt_engine import GoogleFlowPromptEngine
from src.reference_template_manager import ReferenceTemplateManager
from src.product_media_manager import ProductMediaManager
from src.flow_adapter import GoogleFlowAdapter


def test_reference_template_manager_default():
    """Verifies that default no-face template path exists on Drive D."""
    tpl = ReferenceTemplateManager.get_default_noface_template()
    assert tpl.exists(), f"Default template must exist at {tpl}"
    assert tpl.suffix in [".jpg", ".png", ".jpeg"]
    assert "data" in str(tpl)


def test_product_media_manager_get_or_create():
    """Verifies product media manager creates/locates a valid reference image on Drive D."""
    ref = ProductMediaManager.get_or_create_product_ref("PROD-TEST-REF-01")
    assert ref.exists()
    assert "data" in str(ref)


def test_flow_prompt_engine_noface_synthesis():
    """Verifies No-Face Chin-Down prompt generation has correct framing and product name."""
    product = Product(
        product_id="TEST-BLAZER-01",
        name="Blazer Korean Slim Fit Sage Green",
        price_idr=185000.0,
        commission_rate=0.15,
        category="Women Outerwear",
        shop_name="UrbanChic ID"
    )
    prompt = GoogleFlowPromptEngine.synthesize_noface_video_prompt(product)
    assert "chin to waist" in prompt
    assert "Blazer Korean Slim Fit Sage Green" in prompt
    assert "9:16 vertical" in prompt
    assert "no full face visible" in prompt


@patch("subprocess.run")
def test_flow_adapter_generate_video_with_references(mock_subproc):
    """Verifies GoogleFlowAdapter passes both --start-image and --reference to the Go binary."""
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_subproc.return_value = mock_res

    adapter = GoogleFlowAdapter()
    
    start_img = Path("data/templates/noface_chin_down_ref.jpg")
    prod_ref = Path("data/product_images/test_prod.jpg")
    prod_ref.parent.mkdir(parents=True, exist_ok=True)
    prod_ref.write_text("fake image content")

    # Mock output dir having a video
    out_video = adapter.output_dir / "test_out.mp4"
    out_video.write_text("fake video")

    with patch.object(adapter, "is_authenticated", return_value=True):
        vid = adapter.generate_video(
            prompt="No-face fashion try on",
            start_image=start_img,
            references=[prod_ref],
            aspect="9:16",
            duration="6s"
        )
        assert vid == out_video

        # Check command args passed to subprocess
        called_cmd = mock_subproc.call_args[0][0]
        assert "--start-image" in called_cmd
        assert str(start_img.resolve()) in called_cmd
        assert "--reference" in called_cmd
        assert str(prod_ref.resolve()) in called_cmd


def test_crop_clean_garment_reference(tmp_path):
    """Verifies cropping phone screenshot removes letterboxing and produces a clean image."""
    from PIL import Image
    fake_ss = tmp_path / "screenshot.jpg"
    img = Image.new("RGB", (739, 1600), color=(0, 0, 0))
    img.save(fake_ss)

    out_crop = ProductMediaManager.crop_clean_garment_reference(fake_ss, tmp_path / "clean.jpg")
    assert out_crop.exists()
    with Image.open(out_crop) as cropped:
        assert cropped.size[1] < 1600  # Height trimmed


def test_crop_chin_down_reference(tmp_path):
    """Verifies chin-down cropping isolates upper-body torso."""
    from PIL import Image
    fake_ss = tmp_path / "screenshot.jpg"
    img = Image.new("RGB", (739, 1600), color=(100, 100, 100))
    img.save(fake_ss)

    out_chin = ProductMediaManager.crop_chin_down_reference(fake_ss, tmp_path / "chin_down.jpg")
    assert out_chin.exists()
    with Image.open(out_chin) as cropped:
        assert cropped.size[0] < 739
        assert cropped.size[1] < 1600


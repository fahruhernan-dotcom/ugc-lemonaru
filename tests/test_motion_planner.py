"""Unit tests for the Product Motion Planning and Demonstration Pipeline."""

import pytest
from pathlib import Path
from src.models import Product
from src.motion_planner import ProductMotionPlanner, MotionPhase
from src.flow_prompt_engine import GoogleFlowPromptEngine
from src.affiliate_pipeline import AffiliatePipeline


@pytest.fixture
def sample_cardigan_product():
    return Product(
        product_id="TEST-GARMENT-01",
        name="Cardigan Rajut Crop Cokelat Set Inner Ribbon",
        price_idr=145000.0,
        commission_rate=0.15,
        category="Fashion Wanita",
        shop_name="Velora Boutique"
    )


@pytest.fixture
def sample_skincare_product():
    return Product(
        product_id="TEST-SKINCARE-01",
        name="Glow Serum Hyaluronic Hydrating",
        price_idr=89000.0,
        commission_rate=0.20,
        category="Skincare",
        shop_name="Glow Lab"
    )


def test_category_detection(sample_cardigan_product, sample_skincare_product):
    cat_cardigan = ProductMotionPlanner.detect_category(sample_cardigan_product)
    assert cat_cardigan == ProductMotionPlanner.CATEGORY_SET

    cat_skincare = ProductMotionPlanner.detect_category(sample_skincare_product)
    assert cat_skincare == ProductMotionPlanner.CATEGORY_SKINCARE

    bottom_prod = Product(
        product_id="TEST-BOTTOMS",
        name="Highwaist Loose Kulot Pants",
        price_idr=99000.0,
        commission_rate=0.10,
        category="Fashion",
        shop_name="Velora"
    )
    assert ProductMotionPlanner.detect_category(bottom_prod) == ProductMotionPlanner.CATEGORY_BOTTOMS


def test_generate_timeline_structure(sample_cardigan_product):
    timeline = ProductMotionPlanner.generate_timeline(sample_cardigan_product, duration_sec=10)
    assert len(timeline) == 4

    # Check phase continuity
    assert timeline[0].start_sec == 0.0
    assert timeline[0].end_sec == 2.0
    assert timeline[1].start_sec == 2.0
    assert timeline[1].end_sec == 5.0
    assert timeline[2].start_sec == 5.0
    assert timeline[2].end_sec == 8.0
    assert timeline[3].start_sec == 8.0
    assert timeline[3].end_sec == 10.0

    # Check focal zones and actions
    assert "ribbon" in timeline[1].focal_zone.lower() or "collar" in timeline[1].focal_zone.lower()
    assert "ribbed" in timeline[2].focal_zone.lower() or "fabric" in timeline[2].focal_zone.lower()


def test_format_prompt_choreography(sample_cardigan_product):
    timeline = ProductMotionPlanner.generate_timeline(sample_cardigan_product, duration_sec=10)
    choreography = ProductMotionPlanner.format_prompt_choreography(timeline)
    assert "[0-2s: Establish Outfit]" in choreography
    assert "[2-5s: Feature & Focal Detail]" in choreography
    assert "[5-8s: Material Demonstration]" in choreography
    assert "[8-10s: Closing & Proportions]" in choreography


def test_synthesize_choreographed_tryon_prompt(sample_cardigan_product):
    prompt = GoogleFlowPromptEngine.synthesize_choreographed_tryon_prompt(sample_cardigan_product)
    assert "lower jaw down to waist" in prompt
    assert "iPhone 15 Pro back camera" in prompt
    assert "[0-2s:" in prompt
    assert "[2-5s:" in prompt
    assert "[5-8s:" in prompt
    assert "[8-10s:" in prompt


def test_affiliate_pipeline_dry_run(sample_cardigan_product, tmp_path):
    pipeline = AffiliatePipeline(output_dir=tmp_path)
    res = pipeline.process_product(sample_cardigan_product, dry_run=True)

    assert res["success"] is True
    pkg_dir = Path(res["package_dir"])
    assert pkg_dir.exists()
    assert (pkg_dir / "brief.json").exists()
    assert (pkg_dir / "copywriting.txt").exists()

    brief_data = (pkg_dir / "brief.json").read_text(encoding="utf-8")
    assert "Establish Outfit" in brief_data
    assert "Material Demonstration" in brief_data


def test_peplum_product_motion_and_prompt():
    peplum_prod = Product(
        product_id="GARMENT-05",
        name="CLASSY - TESSA Peplum Top Wanita Blouse Tanpa Lengan",
        price_idr=129000.0,
        commission_rate=0.15,
        category="Fashion Wanita",
        shop_name="CLASSY Official"
    )
    cat = ProductMotionPlanner.detect_category(peplum_prod)
    assert cat == ProductMotionPlanner.CATEGORY_PEPLUM_TOP

    timeline = ProductMotionPlanner.generate_timeline(peplum_prod, duration_sec=10)
    assert len(timeline) == 4
    assert timeline[0].name == "Establish Silhouette"
    assert "shoulder" in timeline[1].focal_zone.lower()
    assert "smocked" in timeline[2].focal_zone.lower()
    assert "peplum" in timeline[3].focal_zone.lower()

    prompt = GoogleFlowPromptEngine.synthesize_choreographed_tryon_prompt(peplum_prod)
    assert "faceless" not in prompt.lower()
    assert "peplum" in prompt.lower()
    assert "shoulder tie ribbon" in prompt.lower()
    assert "blue denim" in prompt.lower()


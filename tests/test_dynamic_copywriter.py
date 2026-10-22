"""Unit tests for the Dynamic UGC Copywriter Engine."""

import pytest
from src.models import Product
from src.dynamic_copywriter import DynamicUgcCopywriter
from src.motion_planner import ProductMotionPlanner


@pytest.fixture
def peplum_top_product():
    return Product(
        product_id="GARMENT-05",
        name="CLASSY - TESSA Peplum Top Wanita Blouse Tanpa Lengan",
        category="fashion_peplum_top",
        price_idr=129000.0,
        commission_rate=0.15,
        sales_count=1840,
        rating=4.9,
        shop_name="CLASSY Official",
        stock_available=250
    )


@pytest.fixture
def cardigan_product():
    return Product(
        product_id="GARMENT-01",
        name="Cardigan Rajut Crop Cokelat Set Inner Ribbon",
        category="fashion_set",
        price_idr=145000.0,
        commission_rate=0.15,
        sales_count=2300,
        rating=4.8,
        shop_name="Velora Boutique",
        stock_available=180
    )


@pytest.fixture
def skincare_product():
    return Product(
        product_id="SKINCARE-01",
        name="Glow Hydrating Niacinamide Serum",
        category="skincare",
        price_idr=79000.0,
        commission_rate=0.20,
        sales_count=450,
        rating=4.9,
        shop_name="Glow Lab",
        stock_available=100
    )


def test_dynamic_hook_generation(peplum_top_product, cardigan_product, skincare_product):
    hook_peplum = DynamicUgcCopywriter.generate_hook(peplum_top_product)
    assert "peplum" in hook_peplum.lower() or "pinggang" in hook_peplum.lower()

    hook_cardigan = DynamicUgcCopywriter.generate_hook(cardigan_product)
    assert "cardigan" in hook_cardigan.lower() or "set" in hook_cardigan.lower()

    hook_skincare = DynamicUgcCopywriter.generate_hook(skincare_product)
    assert "kulit" in hook_skincare.lower() or "serum" in hook_skincare.lower()


def test_complete_script_assembly(peplum_top_product):
    script = DynamicUgcCopywriter.generate_complete_script(peplum_top_product)
    
    assert "hook" in script
    assert "problem_solution" in script
    assert "material_demonstration" in script
    assert "cta" in script
    assert "full_spoken_script" in script
    assert "formatted_markdown" in script

    # Verify key Indonesian TikTok conversion triggers
    assert "keranjang kuning" in script["cta"].lower()
    assert "smocked" in script["material_demonstration"].lower()
    assert "CLASSY Official" in script["cta"]


def test_caption_and_hashtags(peplum_top_product, cardigan_product):
    cap_peplum = DynamicUgcCopywriter.generate_caption_and_hashtags(peplum_top_product)
    assert "#peplumtop" in cap_peplum["hashtags"]
    assert "#racuntiktok" in cap_peplum["hashtags"]
    assert "keranjang kuning" in cap_peplum["caption"].lower()

    cap_cardigan = DynamicUgcCopywriter.generate_caption_and_hashtags(cardigan_product)
    assert "#cardiganrajut" in cap_cardigan["hashtags"]


def test_build_content_brief(peplum_top_product):
    brief = DynamicUgcCopywriter.build_content_brief(peplum_top_product)
    assert brief.product_id == peplum_top_product.id
    assert brief.hook_type == "SOCIAL_PROOF_FOMO"  # > 500 sales
    assert len(brief.shot_list) == 4
    assert brief.target_aspect_ratio == "9:16"
    assert brief.estimated_duration_seconds == 10
    assert "Rp 129,000" in " ".join(brief.product_facts)


def test_snackable_10s_script(peplum_top_product):
    snackable = DynamicUgcCopywriter.generate_snackable_10s_script(peplum_top_product)
    assert "spoken_script" in snackable
    assert 15 <= snackable["word_count"] <= 25
    assert "keranjang kuning" in snackable["spoken_script"].lower()
    assert "peplum" in snackable["spoken_script"].lower()

    # Verify brief with snackable mode
    brief = DynamicUgcCopywriter.build_content_brief(peplum_top_product, mode="snackable_10s")
    assert brief.estimated_duration_seconds == 10
    assert len(brief.script_body.split()) <= 25

    # Verify brief with full review mode
    brief_full = DynamicUgcCopywriter.build_content_brief(peplum_top_product, mode="full_review_45s")
    assert brief_full.estimated_duration_seconds == 45
    assert len(brief_full.script_body.split()) > 40

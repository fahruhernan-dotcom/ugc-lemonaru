"""Unit tests for deterministic 6D scoring and eligibility gates."""

import pytest
from src.models import Product
from src.scoring import ProductScorer


def test_hard_stop_gates():
    # 1. Low stock failure
    p_low_stock = Product(
        product_id="TEST-STOCK",
        name="Kemeja Linen",
        price_idr=100000.0,
        commission_rate=0.10,
        shop_name="Shop A",
        stock_available=5  # < 10
    )
    score_stock = ProductScorer.calculate_score(p_low_stock)
    assert not score_stock.is_eligible
    assert any("Stock" in r for r in score_stock.ineligibility_reasons)

    # 2. Low commission failure
    p_low_comm = Product(
        product_id="TEST-COMM",
        name="Kemeja Linen",
        price_idr=100000.0,
        commission_rate=0.03,  # < 5%
        shop_name="Shop A",
        stock_available=50
    )
    score_comm = ProductScorer.calculate_score(p_low_comm)
    assert not score_comm.is_eligible
    assert any("Commission rate" in r for r in score_comm.ineligibility_reasons)

    # 3. Low price margin failure
    p_low_price = Product(
        product_id="TEST-PRICE",
        name="Kemeja Linen",
        price_idr=15000.0,  # < 25,000 IDR
        commission_rate=0.15,
        shop_name="Shop A",
        stock_available=50
    )
    score_price = ProductScorer.calculate_score(p_low_price)
    assert not score_price.is_eligible
    assert any("Price" in r for r in score_price.ineligibility_reasons)


def test_missing_rating_handling():
    # Missing rating should NOT fabricate 5.0 or fail with exception
    p_no_rating = Product(
        product_id="TEST-NO-RATING",
        name="Kemeja Linen Oversized",
        price_idr=120000.0,
        commission_rate=0.12,
        shop_name="Shop A",
        stock_available=30,
        rating=None
    )
    score = ProductScorer.calculate_score(p_no_rating)
    assert score.score_breakdown["reputation_details"]["rating_status"] == "UNVERIFIED_MISSING_DATA"
    assert score.creator_reputation == 50.0  # Neutral calibrated baseline


def test_winning_eligible_product():
    p_winner = Product(
        product_id="PROD-ID-001",
        name="Kemeja Linen Oversized Pria Wanita Adem",
        price_idr=139000.0,
        commission_rate=0.15,
        sales_count=1280,
        rating=4.8,
        shop_name="Zaskia Official Store",
        stock_available=85,
        image_urls=["img1.jpg", "img2.jpg", "img3.jpg"]
    )
    score = ProductScorer.calculate_score(p_winner)
    assert score.is_eligible, f"Winner must be eligible, got reasons: {score.ineligibility_reasons}"
    assert score.final_score >= 70.0, f"Expected final score >= 70.0, got {score.final_score}"
    assert len(score.ineligibility_reasons) == 0

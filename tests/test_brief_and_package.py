"""Unit tests for content brief generation and ready-to-publish package export."""

import json
from pathlib import Path
import pytest
from src.brief_generator import BriefGenerator
from src.models import Product, ProductScore
from src.package_exporter import PackageExporter
from src.scoring import ProductScorer


def test_brief_structure_and_factual_claims():
    product = Product(
        product_id="TEST-BRIEF-001",
        name="Kemeja Linen Oversized",
        price_idr=139000.0,
        commission_rate=0.15,
        sales_count=1200,
        rating=4.8,
        shop_name="Zaskia Store",
        stock_available=50
    )
    score = ProductScorer.calculate_score(product)
    brief = BriefGenerator.generate_brief(product, score)

    # 1. Verification of Brief Components
    assert brief.hook_text, "Hook text must not be empty"
    assert brief.hook_type in ["SOCIAL_PROOF_FOMO", "PRICE_TO_VALUE_DISRUPTION", "PROBLEM_SOLUTION_RELATABLE"]
    assert len(brief.shot_list) == 4, "Shot list must have 4 scenes (0-30s timeline)"
    assert brief.cta_text, "CTA text must not be empty"
    assert brief.caption, "Caption must not be empty"
    assert len(brief.hashtags) >= 3, "Hashtags must contain at least 3 relevant tags"

    # 2. Anti-hallucination factual claims check
    assert any("Rp 139,000" in f for f in brief.product_facts)
    assert any("Zaskia Store" in f for f in brief.product_facts)


def test_package_export(tmp_path):
    product = Product(
        product_id="TEST-PKG-001",
        name="Blazer Slim Fit Korean Look",
        price_idr=185000.0,
        commission_rate=0.18,
        sales_count=850,
        rating=4.9,
        shop_name="UrbanChic",
        stock_available=40
    )
    score = ProductScorer.calculate_score(product)
    brief = BriefGenerator.generate_brief(product, score)

    pkg_dir = PackageExporter.export_package(product, brief, score, base_dir=tmp_path)
    assert pkg_dir.exists()

    # Verify all 5 files exist
    metadata_file = pkg_dir / "metadata.json"
    brief_file = pkg_dir / "brief.md"
    caption_file = pkg_dir / "caption.txt"
    checklist_file = pkg_dir / "compliance_checklist.json"
    shot_list_file = pkg_dir / "shot_list.json"

    assert metadata_file.exists()
    assert brief_file.exists()
    assert caption_file.exists()
    assert checklist_file.exists()
    assert shot_list_file.exists()

    # Verify metadata explicitly declares UNPUBLISHED status
    with open(metadata_file, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["publication_status"] == "UNPUBLISHED_DRAFT"
    assert meta["tiktok_post"]["is_published"] is False
    assert meta["affiliate_anchor"]["status"] == "NOT_ATTACHED"

    # Verify compliance checklist has 5 checkpoints
    with open(checklist_file, "r", encoding="utf-8") as f:
        comp = json.load(f)
    assert len(comp["checkpoints"]) == 5
    assert comp["checkpoints"][0]["name"] == "commercial_content_disclosure"
    assert comp["checkpoints"][1]["name"] == "ai_generated_content_label"

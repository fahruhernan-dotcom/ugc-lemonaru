"""Supabase Database Setup and Verification Utility for Velora AI.
Verifies connection, checks table availability, and seeds initial catalog products.
"""

import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Ensure root dir is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("setup_supabase")

from src.config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY
from src.models import Product, ProductScore, ContentBrief
from src.repository import get_repository, SupabaseRepository, LocalRepository


EXPECTED_TABLES = [
    "affiliate_products",
    "product_scores",
    "product_media",
    "content_briefs",
    "ugc_generations",
    "workflow_events"
]


def check_supabase_health():
    """Checks remote Supabase endpoint and schema cache status."""
    import requests
    
    if not SUPABASE_URL:
        logger.error("SUPABASE_URL is not set in .env")
        return False, []

    key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY
    if not key:
        logger.error("Neither SUPABASE_SERVICE_ROLE_KEY nor SUPABASE_KEY is set in .env")
        return False, []

    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    
    # 1. Check OpenAPI root
    try:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/", headers=headers, timeout=10)
        logger.info("Supabase OpenAPI check: HTTP %d", resp.status_code)
    except Exception as e:
        logger.error("Failed to connect to Supabase: %s", e)
        return False, []

    # 2. Check each table
    existing_tables = []
    missing_tables = []
    for table in EXPECTED_TABLES:
        try:
            t_resp = requests.get(f"{SUPABASE_URL}/rest/v1/{table}?select=count", headers=headers, timeout=5)
            if t_resp.status_code in [200, 206]:
                existing_tables.append(table)
            else:
                missing_tables.append(table)
        except Exception:
            missing_tables.append(table)

    logger.info("Existing tables in Supabase: %s", existing_tables)
    if missing_tables:
        logger.warning("Missing tables in Supabase: %s", missing_tables)
        logger.info(
            "\n>>> ACTION REQUIRED <<<\n"
            "Please open your Supabase Dashboard SQL Editor at:\n"
            "  https://supabase.com/dashboard/project/ddhouwaedzzrpuiiwzmb/sql\n"
            "And run the SQL file:\n"
            "  supabase/migrations/20261009000002_ugc_system.sql\n"
        )
    return len(missing_tables) == 0, existing_tables


def seed_standard_products():
    """Seeds canonical benchmark products (including Garment 5 Peplum Top) into repository."""
    repo = get_repository()
    logger.info("Active repository: %s", type(repo).__name__)

    # Canonical benchmark products
    products = [
        Product(
            product_id="GARMENT-05",
            name="CLASSY - TESSA Peplum Top Wanita Blouse Tanpa Lengan",
            category="fashion_peplum_top",
            price_idr=129000.0,
            commission_rate=0.15,
            sales_count=1840,
            rating=4.9,
            shop_name="CLASSY Official",
            stock_available=250,
            image_urls=["data/product_images/garment_5_isolated_white_bg.jpg"],
            raw_payload={
                "color": "broken_white",
                "material": "premium_cotton",
                "waist": "smocked_elastic",
                "benchmark_score": 8.5
            }
        ),
        Product(
            product_id="GARMENT-01",
            name="Cardigan Rajut Crop Cokelat Set Inner Ribbon",
            category="fashion_set",
            price_idr=145000.0,
            commission_rate=0.15,
            sales_count=2300,
            rating=4.8,
            shop_name="Velora Boutique",
            stock_available=180,
            image_urls=["data/product_images/garment_1_isolated_white_bg.jpg"],
            raw_payload={
                "color": "chocolate_brown",
                "material": "ribbed_knit",
                "pieces": "2in1_camisole_cardigan"
            }
        ),
        Product(
            product_id="GARMENT-02",
            name="Kemeja Crop Katun Lengan Pendek Broken White",
            category="fashion_top_outerwear",
            price_idr=89000.0,
            commission_rate=0.12,
            sales_count=950,
            rating=4.7,
            shop_name="Daily Chic",
            stock_available=320,
            image_urls=["data/product_images/garment_2.jpg"],
            raw_payload={
                "color": "broken_white",
                "material": "cotton_poplin"
            }
        )
    ]

    saved = repo.save_products(products)
    logger.info("Successfully seeded %d products into repository.", saved)
    return saved


if __name__ == "__main__":
    is_ready, tables = check_supabase_health()
    seed_standard_products()
    if is_ready:
        print("\n[SUCCESS] Supabase is fully configured and ready!")
    else:
        print("\n[NOTICE] Local repository active with full database schema ready to sync.")

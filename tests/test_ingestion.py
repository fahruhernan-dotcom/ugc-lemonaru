"""Unit tests for catalog ingestion, normalization, and deduplication."""

import io
from pathlib import Path
import pytest

from src.ingestion import (
    CatalogIngestor,
    parse_commission_rate,
    parse_price,
    parse_rating,
    parse_sales_count,
)


def test_parse_price_formats():
    assert parse_price("139000") == 139000.0
    assert parse_price("Rp 139.000") == 139000.0
    assert parse_price("Rp 139.000,50") == 139000.50
    assert parse_price(150000) == 150000.0
    assert parse_price("-50000") is None
    assert parse_price("invalid") is None
    assert parse_price(None) is None


def test_parse_commission_rate():
    assert parse_commission_rate("15%") == 0.15
    assert parse_commission_rate("0.15") == 0.15
    assert parse_commission_rate(15) == 0.15
    assert parse_commission_rate(0.08) == 0.08
    assert parse_commission_rate("150%") is None  # > 100% invalid
    assert parse_commission_rate(None) is None


def test_parse_sales_count():
    assert parse_sales_count("1250") == 1250
    assert parse_sales_count("1.2k") == 1200
    assert parse_sales_count("500 terjual") == 500
    assert parse_sales_count(100) == 100
    assert parse_sales_count(None) == 0


def test_parse_rating_no_fabrication():
    assert parse_rating("4.8") == 4.8
    assert parse_rating("4,5") == 4.5
    assert parse_rating(4.9) == 4.9
    # Must NOT fabricate missing data into 5.0 or 0
    assert parse_rating("") is None
    assert parse_rating(None) is None
    assert parse_rating("6.0") is None  # Out of bounds


def test_ingest_sample_catalog_csv():
    catalog_path = Path(__file__).resolve().parent.parent / "data" / "sample_fashion_catalog.csv"
    assert catalog_path.exists(), "Sample catalog CSV must exist"

    products, stats = CatalogIngestor.ingest_csv(catalog_path)

    # 8 rows total: 1 invalid row, 1 duplicate row -> 6 valid products
    assert stats.total_rows == 8
    assert stats.rejected_count == 1
    assert stats.duplicate_count == 1
    assert len(products) == 6

    # Verify deduplication for PROD-ID-001 took the higher sales count (1280 vs 1250)
    prod_001 = next(p for p in products if p.product_id == "PROD-ID-001")
    assert prod_001.sales_count == 1280
    assert prod_001.price_idr == 139000.0
    assert prod_001.commission_rate == 0.15

    # Verify missing rating is preserved as None (PROD-ID-004)
    prod_004 = next(p for p in products if p.product_id == "PROD-ID-004")
    assert prod_004.rating is None

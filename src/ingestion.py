"""Product catalog ingestion, validation, normalization, and deduplication."""

import csv
import io
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

from src.models import Product


class IngestionStats(BaseModel):
    total_rows: int = 0
    valid_count: int = 0
    rejected_count: int = 0
    duplicate_count: int = 0
    rejection_reasons: List[Dict[str, Any]] = Field(default_factory=list)


def parse_price(val: Any) -> Optional[float]:
    """Parse numeric price from Indonesian currency string or number."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if math.isnan(val) or val <= 0:
            return None
        return float(val)
    
    s_raw = str(val).strip().upper()
    if s_raw.startswith("-") or "-" in s_raw:
        return None
    
    s = re.sub(r"[^\d,\.]", "", s_raw)
    if not s:
        return None
    
    # Handle Indonesian format: 150.000 or 150.000,00
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "." in s and len(s.split(".")[-1]) == 3:
        # e.g. 150.000 -> thousands separator
        s = s.replace(".", "")
    elif "," in s:
        s = s.replace(",", ".")
        
    try:
        p = float(s)
        return p if p > 0 else None
    except ValueError:
        return None


def parse_commission_rate(val: Any) -> Optional[float]:
    """Parse commission rate into a float between 0.0 and 1.0."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        if math.isnan(val) or val < 0:
            return None
        return float(val) / 100.0 if val > 1.0 else float(val)
    
    s = str(val).strip().replace("%", "").replace(",", ".")
    if not s:
        return None
    try:
        r = float(s)
        if r > 1.0:
            r = r / 100.0
        return r if 0.0 <= r <= 1.0 else None
    except ValueError:
        return None


def parse_sales_count(val: Any) -> int:
    """Parse sales count, handling formats like '1.2k', '500 terjual'."""
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return 0 if math.isnan(val) or val < 0 else int(val)
    
    s = str(val).strip().lower()
    s = re.sub(r"(terjual|sold|\+)", "", s).strip()
    if "k" in s:
        num = re.sub(r"[^\d\.]", "", s)
        try:
            return int(float(num) * 1000)
        except ValueError:
            return 0
    s = re.sub(r"[^\d]", "", s)
    try:
        return int(s) if s else 0
    except ValueError:
        return 0


def parse_rating(val: Any) -> Optional[float]:
    """Parse rating between 0.0 and 5.0 without fabricating missing values."""
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        if math.isnan(val):
            return None
        return float(val) if 0.0 <= val <= 5.0 else None
    
    s = str(val).strip().replace(",", ".")
    if not s:
        return None
    try:
        r = float(s)
        return r if 0.0 <= r <= 5.0 else None
    except ValueError:
        return None


def parse_stock(val: Any) -> int:
    """Parse available stock integer without fabricating."""
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return 0 if math.isnan(val) or val < 0 else int(val)
    s = re.sub(r"[^\d]", "", str(val).strip())
    try:
        return int(s) if s else 0
    except ValueError:
        return 0


class CatalogIngestor:
    """Ingests and validates product catalog rows from CSV or list of dictionaries."""

    REQUIRED_FIELDS = ["name", "shop_name"]

    @classmethod
    def ingest_csv(cls, file_path_or_buffer: Union[str, Path, io.StringIO]) -> Tuple[List[Product], IngestionStats]:
        stats = IngestionStats()
        rows: List[Dict[str, Any]] = []

        if isinstance(file_path_or_buffer, (str, Path)):
            p = Path(file_path_or_buffer)
            if not p.exists():
                raise FileNotFoundError(f"Catalog file not found: {p}")
            with open(p, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        else:
            reader = csv.DictReader(file_path_or_buffer)
            rows = list(reader)

        stats.total_rows = len(rows)
        return cls.process_records(rows, stats)

    @classmethod
    def process_records(cls, raw_records: List[Dict[str, Any]], stats: Optional[IngestionStats] = None) -> Tuple[List[Product], IngestionStats]:
        if stats is None:
            stats = IngestionStats(total_rows=len(raw_records))

        seen_product_ids: Dict[str, Product] = {}
        valid_products: List[Product] = []

        for idx, row in enumerate(raw_records, start=1):
            # Normalize column names to lowercase with underscores
            norm_row = {
                k.lower().strip().replace(" ", "_").replace("-", "_"): v
                for k, v in row.items() if k is not None
            }

            # Map possible ID fields
            raw_id = (
                norm_row.get("product_id") or 
                norm_row.get("id") or 
                norm_row.get("item_id") or 
                norm_row.get("sku")
            )
            raw_name = norm_row.get("name") or norm_row.get("product_name") or norm_row.get("title")
            raw_shop = norm_row.get("shop_name") or norm_row.get("shop") or norm_row.get("seller") or norm_row.get("store")

            # Validation
            rejections = []
            if not raw_id:
                rejections.append("Missing product_id / item_id")
            if not raw_name or not str(raw_name).strip():
                rejections.append("Missing product name")
            if not raw_shop or not str(raw_shop).strip():
                rejections.append("Missing shop_name")

            price = parse_price(norm_row.get("price_idr") or norm_row.get("price"))
            if price is None:
                rejections.append("Invalid or missing price_idr (must be > 0)")

            comm_rate = parse_commission_rate(norm_row.get("commission_rate") or norm_row.get("commission") or norm_row.get("rate"))
            if comm_rate is None:
                rejections.append("Invalid or missing commission_rate (must be 0-100%)")

            if rejections:
                stats.rejected_count += 1
                stats.rejection_reasons.append({
                    "row_index": idx,
                    "product_id": raw_id,
                    "reasons": rejections,
                    "raw_data": row
                })
                continue

            product_id_str = str(raw_id).strip()

            # Deduplication
            if product_id_str in seen_product_ids:
                stats.duplicate_count += 1
                # Update with higher stock/sales if duplicate encountered
                existing = seen_product_ids[product_id_str]
                new_sales = parse_sales_count(norm_row.get("sales_count") or norm_row.get("sales"))
                new_stock = parse_stock(norm_row.get("stock_available") or norm_row.get("stock"))
                if new_sales > existing.sales_count or new_stock > existing.stock_available:
                    existing.sales_count = max(existing.sales_count, new_sales)
                    existing.stock_available = max(existing.stock_available, new_stock)
                continue

            # Parse optional fields cleanly
            sales_count = parse_sales_count(norm_row.get("sales_count") or norm_row.get("sales"))
            rating = parse_rating(norm_row.get("rating") or norm_row.get("score"))
            stock = parse_stock(norm_row.get("stock_available") or norm_row.get("stock"))
            category = str(norm_row.get("category") or "fashion").strip().lower()
            affiliate_url = str(norm_row.get("affiliate_url") or norm_row.get("url") or "").strip() or None

            # Images
            raw_images = norm_row.get("image_urls") or norm_row.get("images") or ""
            image_urls: List[str] = []
            if isinstance(raw_images, list):
                image_urls = [str(x).strip() for x in raw_images if x]
            elif isinstance(raw_images, str) and raw_images.strip():
                image_urls = [x.strip() for x in raw_images.split(",") if x.strip()]

            product = Product(
                product_id=product_id_str,
                name=str(raw_name).strip(),
                category=category,
                price_idr=price,
                commission_rate=comm_rate,
                sales_count=sales_count,
                rating=rating,
                shop_name=str(raw_shop).strip(),
                stock_available=stock,
                affiliate_url=affiliate_url,
                image_urls=image_urls,
                status="active" if stock > 0 else "out_of_stock",
                raw_payload=row
            )

            seen_product_ids[product_id_str] = product
            valid_products.append(product)
            stats.valid_count += 1

        return valid_products, stats

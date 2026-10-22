"""End-to-End TikTok Affiliate Automation Pipeline for Velora AI.
Orchestrates:
1. Product metadata ingestion
2. Catalog image preprocessing (clean crop & chin-down isolation)
3. 4-Phase micro-motion choreography planning
4. Timed prompt synthesis
5. Video generation dispatch via Google Flow Studio
6. Package export to ready_to_publish/
"""

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Dict, Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models import Product
from src.product_media_manager import ProductMediaManager
from src.motion_planner import ProductMotionPlanner
from src.flow_prompt_engine import GoogleFlowPromptEngine
from src.dynamic_copywriter import DynamicUgcCopywriter
from src.config import DATA_DIR, OUTPUT_DIR, ROOT_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("affiliate_pipeline")

READY_DIR = ROOT_DIR / "ready_to_publish"
READY_DIR.mkdir(parents=True, exist_ok=True)


class AffiliatePipeline:
    """Master orchestrator for AI-driven TikTok Affiliate video generation."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = (output_dir or READY_DIR).resolve()
        self.media_manager = ProductMediaManager()

    def process_product(
        self,
        product: Product,
        raw_image_path: Optional[Path] = None,
        dry_run: bool = False,
        project_id: str = "0cd53e0c-dae6-4b49-b362-727a82c2dd22"
    ) -> Dict[str, Any]:
        """Runs the complete automation pipeline for a single affiliate product."""
        logger.info("==================================================")
        logger.info("PROCESSING AFFILIATE PRODUCT: %s", product.name)
        logger.info("Category: %s | Price: Rp %s", product.category, f"{product.price_idr:,.0f}")
        logger.info("==================================================")

        # 1. Image Preprocessing (Clean Crop, Chin-Down, and AI White BG Isolation)
        crop_info = {}
        if raw_image_path and raw_image_path.exists():
            crop_clean = self.media_manager.crop_clean_garment_reference(raw_image_path)
            chin_crop = self.media_manager.crop_chin_down_reference(crop_clean)
            isolated_crop = self.media_manager.extract_isolated_garment_reference(chin_crop)
            crop_info = {
                "raw": str(raw_image_path),
                "clean": str(crop_clean),
                "chin_down": str(chin_crop),
                "isolated_white_bg": str(isolated_crop)
            }
            logger.info("Preprocessed reference crops (Isolated): %s", isolated_crop)

        # 2. Category Detection & Motion Choreography Planning
        detected_category = ProductMotionPlanner.detect_category(product)
        timeline = ProductMotionPlanner.generate_timeline(product, duration_sec=10)
        logger.info("Detected Category: %s (%d motion phases)", detected_category, len(timeline))

        # 3. Motion-Conditioned Prompt Synthesis
        choreographed_prompt = GoogleFlowPromptEngine.synthesize_choreographed_tryon_prompt(
            product, scene="front", duration_sec=10
        )
        logger.info("Synthesized 4-Phase Prompt (%d chars):\n%s", len(choreographed_prompt), choreographed_prompt)

        # 4. Create Target Publication Package Directory
        pkg_name = f"PKG_{product.product_id.replace('-', '_').upper()}"
        pkg_dir = self.output_dir / pkg_name
        pkg_dir.mkdir(parents=True, exist_ok=True)

        # 5. Generate TikTok Copywriting Brief dynamically (Anti-Hardcoded)
        script_data = DynamicUgcCopywriter.generate_complete_script(product)
        caption_data = DynamicUgcCopywriter.generate_caption_and_hashtags(product)
        (pkg_dir / "copywriting.txt").write_text(script_data["formatted_markdown"], encoding="utf-8")
        (pkg_dir / "caption.txt").write_text(caption_data["caption"], encoding="utf-8")

        # 6. Save Pipeline Metadata
        metadata = {
            "product_id": product.product_id,
            "product_name": product.name,
            "category": detected_category,
            "price_idr": product.price_idr,
            "commission_amount_idr": product.commission_amount_idr,
            "timeline": [
                {
                    "phase": p.name,
                    "time_range": f"{p.start_sec}-{p.end_sec}s",
                    "focal_zone": p.focal_zone,
                    "action": p.hand_action,
                    "intent": p.audience_intent
                }
                for p in timeline
            ],
            "prompt": choreographed_prompt,
            "crop_info": crop_info
        }
        (pkg_dir / "brief.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        # Copy clean reference image to package
        if crop_info.get("chin_down"):
            dest_img = pkg_dir / "reference_chin_down.jpg"
            shutil.copy2(crop_info["chin_down"], dest_img)

        # 7. Browser Studio Generation Dispatch (if not dry run)
        dispatch_result = {"status": "skipped_dry_run"}
        if not dry_run:
            from src.flow_selenium_operator import GoogleFlowSeleniumOperator
            op = GoogleFlowSeleniumOperator()
            try:
                ref_filename = Path(crop_info.get("chin_down", f"{product.product_id}_chin_down_ref.jpg")).name
                logger.info("Dispatching to Google Flow Studio with ref: %s", ref_filename)
                dispatch_result = op.submit_studio_tryon(
                    project_id=project_id,
                    reference_name=ref_filename,
                    prompt_text=choreographed_prompt,
                    auto_approve=True
                )
            finally:
                op.close()

        result = {
            "success": True,
            "package_dir": str(pkg_dir),
            "metadata": metadata,
            "dispatch": dispatch_result
        }
        logger.info("Pipeline completed successfully for %s! Package at: %s", product.product_id, pkg_dir)
        return result


def main():
    parser = argparse.ArgumentParser(description="Velora AI TikTok Affiliate Automation Pipeline")
    parser.add_argument("--product-id", default=None, help="Product identifier registered in database")
    parser.add_argument("--image", default=None, help="Custom image path for product")
    parser.add_argument("--dry-run", action="store_true", help="Execute prompt & timeline without browser")
    args = parser.parse_args()

    from src.repository import get_repository
    repo = get_repository()

    if args.product_id:
        product = repo.get_product(args.product_id)
        if not product:
            available = [p.product_id for p in repo.list_products()]
            print(f"❌ Produk '{args.product_id}' tidak ditemukan di database Supabase!")
            print(f"   Daftar produk di database: {available}")
            return
    else:
        prods = repo.list_products()
        if not prods:
            print("❌ Database Supabase belum memiliki produk terdaftar.")
            return
        product = prods[0]
        print(f"📦 [DB FETCH] Mengambil produk dari database: {product.name} ({product.product_id})")

    # Locate raw image from args, DB product media, or product.image_urls
    raw_img = None
    if args.image and Path(args.image).exists():
        raw_img = Path(args.image)
    else:
        media_list = repo.list_product_media(product.id)
        for m in media_list:
            if Path(m.file_path).exists():
                raw_img = Path(m.file_path)
                break
        if not raw_img and product.image_urls:
            p_img = Path(product.image_urls[0])
            if p_img.exists():
                raw_img = p_img

    pipeline = AffiliatePipeline()
    res = pipeline.process_product(product, raw_image_path=raw_img, dry_run=args.dry_run)
    print("\nResult:")
    print(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()

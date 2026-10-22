"""Product Media & Reference Image Manager for Velora AI.
Extracts, downloads, and caches real physical product photos from catalogs/suppliers.
Ensures zero-write to Drive C by strictly saving all media to Drive D (data/product_images).
"""

import logging
from pathlib import Path
from typing import Optional
import urllib.request
from PIL import Image

from src.config import DATA_DIR

logger = logging.getLogger("velora.product_media")

PRODUCT_IMAGES_DIR = DATA_DIR / "product_images"
PRODUCT_IMAGES_DIR.mkdir(parents=True, exist_ok=True)


class ProductMediaManager:
    """Manages physical product photos for dual-reference Google Flow conditioning."""

    @staticmethod
    def download_product_image(product_id: str, image_url: str) -> Path:
        """Downloads a product image from an affiliate or catalog URL to Drive D."""
        target_file = PRODUCT_IMAGES_DIR / f"{product_id}_ref.jpg"
        logger.info("Downloading product reference for %s from %s", product_id, image_url)
        
        req = urllib.request.Request(
            image_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp, open(target_file, "wb") as f:
            f.write(resp.read())

        # Validate with PIL
        with Image.open(target_file) as img:
            img.verify()
        logger.info("Product reference verified and stored at: %s", target_file)
        return target_file.resolve()

    @staticmethod
    def get_or_create_product_ref(
        product_id: str,
        package_dir: Optional[Path] = None,
        fallback_name: Optional[str] = None
    ) -> Path:
        """Locates an existing product reference image or provides a clean placeholder."""
        # 1. Check in package dir
        if package_dir and package_dir.exists():
            for candidate in [
                "chin_down_ref.jpg", "clean_crop.jpg", "product_ref.jpg",
                "product.jpg", "product_ref.png", "image.jpg"
            ]:
                p = package_dir / candidate
                if p.exists():
                    return p.resolve()

        # 2. Check in data/product_images/ with priority for clean crops
        import re
        pid_clean = product_id.lower().replace("-", "_")
        pid_num = re.sub(r"[^0-9]", "", product_id).lstrip("0")
        
        candidates = [
            f"{product_id}_isolated_white_bg.jpg",
            f"{product_id}_chin_down_ref.jpg",
            f"{product_id}_clean_crop.jpg",
            f"{product_id}_ref.jpg",
            f"{product_id}.jpg",
            f"{pid_clean}_isolated_white_bg.jpg",
            f"{pid_clean}_chin_down_ref.jpg",
            f"{pid_clean}_clean_crop.jpg",
            f"{pid_clean}_ref.jpg",
            f"{pid_clean}.jpg",
        ]
        if pid_num:
            candidates.extend([
                f"garment_{pid_num}_isolated_white_bg.jpg",
                f"garment_{pid_num}_chin_down_ref.jpg",
                f"garment_{pid_num}_clean_crop.jpg",
                f"garment_{pid_num}.jpg",
                f"garment_{pid_num.zfill(2)}_isolated_white_bg.jpg",
                f"garment_{pid_num.zfill(2)}.jpg"
            ])
        for c_name in candidates:
            cached = PRODUCT_IMAGES_DIR / c_name
            if cached.exists():
                return cached.resolve()

        # 3. Create a clean neutral fashion catalog reference on Drive D if none exists
        target_ref = PRODUCT_IMAGES_DIR / f"{product_id}_ref.jpg"
        logger.info("Creating initial product reference image for %s at %s", product_id, target_ref)
        img = Image.new("RGB", (720, 1280), color=(245, 243, 240))
        img.save(target_ref, quality=95)
        return target_ref.resolve()

    @staticmethod
    def crop_clean_garment_reference(input_path: Path, output_path: Optional[Path] = None) -> Path:
        """Strips smartphone letterboxing and UI overlays from catalog screenshots."""
        inp = Path(input_path).resolve()
        out = Path(output_path or inp.parent / f"{inp.stem}_clean_crop.jpg").resolve()
        
        with Image.open(inp) as img:
            w, h = img.size
            # If screenshot has letterboxing (e.g. 739x1600), crop the active inner area
            if h / w > 1.8:
                # Typically top 19% is status/nav bar and bottom 20% is search/bar
                top_y = int(h * 0.192)
                bottom_y = int(h * 0.808)
                cropped = img.crop((0, top_y, w, bottom_y))
            else:
                cropped = img.copy()
            cropped.save(out, quality=95)
        logger.info("Created clean cropped garment reference: %s", out)
        return out

    @staticmethod
    def crop_chin_down_reference(input_path: Path, output_path: Optional[Path] = None) -> Path:
        """Isolates the upper-body garment from lower chin down to hips for maximum try-on fidelity."""
        inp = Path(input_path).resolve()
        out = Path(output_path or inp.parent / f"{inp.stem}_chin_down_ref.jpg").resolve()
        
        with Image.open(inp) as img:
            w, h = img.size
            if h / w > 1.8:
                # From full phone screenshot
                cropped = img.crop((int(w * 0.06), int(h * 0.206), int(w * 0.92), int(h * 0.537)))
            else:
                # From already cropped photo
                cropped = img.crop((int(w * 0.05), int(h * 0.15), int(w * 0.95), int(h * 0.85)))
            cropped.save(out, quality=95)
        logger.info("Created strict chin-down garment reference: %s", out)
        return out

    @staticmethod
    def extract_isolated_garment_reference(
        input_path: Path,
        output_path: Optional[Path] = None,
        bg_color: tuple = (255, 255, 255)
    ) -> Path:
        """Uses AI segmentation (rembg U2Net) to completely remove noisy background,
        producing a pristine isolated garment on a solid clean white background.
        """
        import os
        from rembg import remove, new_session

        # Model cache strictly on Drive D
        u2net_dir = Path("data/models/u2net").resolve()
        u2net_dir.mkdir(parents=True, exist_ok=True)
        os.environ["U2NET_HOME"] = str(u2net_dir)

        inp = Path(input_path).resolve()
        out = Path(output_path or inp.parent / f"{inp.stem}_isolated_white_bg.jpg").resolve()

        with Image.open(inp) as img:
            rgb_img = img.convert("RGB")
            session = new_session("u2net")
            out_rgba = remove(rgb_img, session=session)

            # Composite onto solid white background
            bg_image = Image.new("RGBA", out_rgba.size, (*bg_color, 255))
            final_composite = Image.alpha_composite(bg_image, out_rgba).convert("RGB")
            final_composite.save(out, quality=95)

        logger.info("Extracted clean isolated garment reference: %s", out)
        return out



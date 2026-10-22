"""No-Face Fashion Reference Template Manager for Velora AI.
Extracts, caches, and provides chin-down try-on reference frames for Google Flow conditioning.
Ensures zero-write to Drive C by storing all templates in Drive D (data/templates).
"""

import logging
from pathlib import Path
from typing import Optional
from PIL import Image
import imageio

from src.config import DATA_DIR

logger = logging.getLogger("velora.reference_template")

TEMPLATES_DIR = DATA_DIR / "templates"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_NOFACE_TEMPLATE = TEMPLATES_DIR / "noface_chin_down_ref.jpg"


class ReferenceTemplateManager:
    """Manages visual framing and posture reference templates for Google Flow."""

    @staticmethod
    def get_default_noface_template() -> Path:
        """Returns the default No-Face Chin-Down template image path."""
        if not DEFAULT_NOFACE_TEMPLATE.exists():
            # If default template does not exist, try to extract from local video if available
            ref_vid = Path(__file__).resolve().parent.parent / "ooB9ckveF5Ag1irCW1zAAPudiTEAHIDwIGCFnV.mp4"
            if ref_vid.exists():
                ReferenceTemplateManager.extract_template_from_video(ref_vid, DEFAULT_NOFACE_TEMPLATE)
            else:
                # Create a placeholder 576x1024 neutral fashion template
                img = Image.new("RGB", (576, 1024), color=(240, 235, 230))
                img.save(DEFAULT_NOFACE_TEMPLATE, quality=95)
        return DEFAULT_NOFACE_TEMPLATE.resolve()

    @staticmethod
    def extract_template_from_video(
        video_path: Path,
        output_image_path: Optional[Path] = None,
        second: float = 2.5
    ) -> Path:
        """Extracts a high-quality frame from a video at a specified timestamp."""
        out_path = output_image_path or (TEMPLATES_DIR / f"{video_path.stem}_ref.jpg")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        reader = imageio.get_reader(str(video_path))
        try:
            fps = reader.get_meta_data().get("fps", 30.0)
            target_idx = max(0, int(fps * second))
            frame_data = reader.get_data(target_idx)
            img = Image.fromarray(frame_data)
            img.save(out_path, quality=95)
            logger.info("Successfully extracted template frame to: %s", out_path)
            return out_path.resolve()
        finally:
            reader.close()

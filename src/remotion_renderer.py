"""Remotion Programmatic Video Rendering Engine for Velora AI.
Bridges Python UGC pipeline with React Remotion video compositions.
"""

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("remotion_renderer")


class RemotionRenderer:
    """Operator to render programmatic video overlays via Remotion CLI."""

    def __init__(self, remotion_dir: Optional[Path] = None):
        if remotion_dir is None:
            self.remotion_dir = Path(__file__).resolve().parent.parent / "remotion"
        else:
            self.remotion_dir = Path(remotion_dir).resolve()

    def is_available(self) -> bool:
        """Checks whether Node.js, npm, and Remotion directory are available."""
        if not (self.remotion_dir / "package.json").exists():
            return False
        return bool(shutil.which("npx") or shutil.which("npm"))

    def sync_video_to_public(self, video_path: Path, target_name: str = "active-video.mp4") -> str:
        """Copies an input video to remotion/public/ so Remotion staticFile() can resolve it."""
        video_path = Path(video_path).resolve()
        if not video_path.exists():
            raise FileNotFoundError(f"Source video not found: {video_path}")

        public_dir = self.remotion_dir / "public"
        public_dir.mkdir(parents=True, exist_ok=True)
        dest_path = public_dir / target_name
        shutil.copy2(video_path, dest_path)
        logger.info("Synced video to Remotion public dir: %s", dest_path)
        return target_name

    def render_composition(
        self,
        composition_id: str = "VeloraUGC",
        output_path: Optional[Path] = None,
        props: Optional[Dict[str, Any]] = None,
        port: int = 3030,
        concurrency: Optional[int] = None,
    ) -> Path:
        """Renders a Remotion composition to an MP4 video file."""
        if not self.is_available():
            raise RuntimeError("Remotion project not found or Node.js/npx unavailable.")

        if output_path is None:
            output_path = self.remotion_dir / f"{composition_id.lower()}_render.mp4"
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "npx",
            "remotion",
            "render",
            composition_id,
            str(output_path),
            f"--port={port}",
        ]

        if concurrency:
            cmd.append(f"--concurrency={concurrency}")

        if props:
            props_file = self.remotion_dir / "public" / "active_props.json"
            props_file.parent.mkdir(parents=True, exist_ok=True)
            props_file.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
            cmd.append(f"--props={props_file.resolve()}")

        logger.info("Executing Remotion render: %s in %s", " ".join(cmd), self.remotion_dir)
        res = subprocess.run(
            cmd,
            cwd=str(self.remotion_dir),
            capture_output=True,
            text=True,
            shell=True,
            check=False,
        )

        if res.returncode != 0:
            logger.error("Remotion render failed: %s", res.stderr)
            raise RuntimeError(f"Remotion render failed with exit code {res.returncode}: {res.stderr or res.stdout}")

        logger.info("Remotion video rendered successfully: %s", output_path)
        return output_path

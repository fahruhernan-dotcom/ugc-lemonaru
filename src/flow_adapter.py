"""Google Flow Agent Adapter for Velora AI.
Repository: https://github.com/kodelyx/flow-agent
Direct bridge to Google Flow Engine (flow-windows.exe) and Selenium Browser Operator
for 9:16 AI image and video generation.
"""

import json
import logging
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import FLOW_AGENT_DIR, FLOW_BIN_PATH, FLOW_EXTENSION_DIR
from src.flow_selenium_operator import GoogleFlowSeleniumOperator
from src.flow_prompt_engine import GoogleFlowPromptEngine

logger = logging.getLogger(__name__)


class FlowAuthError(RuntimeError):
    """Raised when Google Flow session cookies are not yet linked."""
    pass


class GoogleFlowAdapter:
    """Unified interface to Google Flow Agent (flow-windows.exe + Selenium).
    Generates 9:16 vertical fashion scenes and animations directly via Google Flow.
    """

    def __init__(self, bin_path: Optional[Path] = None, work_dir: Optional[Path] = None):
        self.bin_path = (bin_path or FLOW_BIN_PATH).resolve()
        self.work_dir = (work_dir or (FLOW_AGENT_DIR / "bin")).resolve()
        self.cookies_dir = self.work_dir / "cookies"
        self.output_dir = self.work_dir / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        self._selenium_operator: Optional[GoogleFlowSeleniumOperator] = None
        self._browser_agent: Optional[Any] = None

    def get_selenium_operator(self) -> GoogleFlowSeleniumOperator:
        """Returns or instantiates the GoogleFlowSeleniumOperator."""
        if not self._selenium_operator:
            self._selenium_operator = GoogleFlowSeleniumOperator(bin_path=self.bin_path)
        return self._selenium_operator

    def get_browser_agent(self):
        """Returns or instantiates the GoogleFlowBrowserAgent."""
        if not self._browser_agent:
            from src.flow_browser_agent import GoogleFlowBrowserAgent
            self._browser_agent = GoogleFlowBrowserAgent(operator=self.get_selenium_operator())
        return self._browser_agent

    def setup_agent_settings(self, confirm: str = "Never", aspect_ratio: str = "9:16") -> Dict[str, Any]:
        """Uses browser agent to set Confirm=Never and aspect=9:16 in Google Flow."""
        agent = self.get_browser_agent()
        agent.open_studio()
        return agent.configure_agent_settings(confirm=confirm, aspect_ratio=aspect_ratio)

    def check_doctor(self) -> Dict[str, Any]:
        """Runs `flow-windows.exe doctor --json` to inspect Google Flow connection."""
        if not self.bin_path.exists():
            return {
                "ok": False,
                "error": f"Binary Google Flow tidak ditemukan di {self.bin_path}"
            }

        cmd = [str(self.bin_path), "doctor", "--json"]
        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.work_dir),
                capture_output=True,
                text=True,
                check=False
            )
            stdout = res.stdout.strip()
            start_idx = stdout.find("{")
            if start_idx != -1:
                return json.loads(stdout[start_idx:])
            return {"ok": False, "raw_output": stdout, "stderr": res.stderr}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def is_authenticated(self) -> bool:
        """Returns True if at least one active Google Flow cookie account is present."""
        cookie_files = list(self.cookies_dir.glob("account_*.json")) + list(self.cookies_dir.glob("cookies.json"))
        return len(cookie_files) > 0

    def start_bridge(self) -> subprocess.Popen:
        """Starts the WebSocket bridge on ws://127.0.0.1:9222 so the Chrome extension
        can automatically sync Google Flow credentials into cookies/.
        """
        cmd = [str(self.bin_path), "bridge"]
        logger.info("Starting Google Flow bridge daemon...")
        proc = subprocess.Popen(
            cmd,
            cwd=str(self.work_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return proc

    def open_selenium_login(self, timeout_seconds: int = 180) -> bool:
        """Launches Chrome via Selenium with the Flow Bridge extension loaded
        and navigates to Google Flow so the operator can authenticate.
        """
        op = self.get_selenium_operator()
        return op.wait_for_user_login(timeout_seconds=timeout_seconds)

    def sync_selenium_cookies(self, wait_seconds: int = 15) -> Dict[str, Any]:
        """Opens Chrome via Selenium and automatically synchronizes cookies with the Go bridge."""
        op = self.get_selenium_operator()
        return op.sync_cookies_with_bridge(wait_seconds=wait_seconds)

    def generate_image(
        self,
        prompt: str,
        aspect: str = "9:16",
        model: str = "narwhal",
        timeout: int = 180
    ) -> Path:
        """Generates a 9:16 vertical image via Google Flow."""
        if not self.is_authenticated():
            raise FlowAuthError(
                "Google Flow cookies belum terpasang. "
                "Jalankan 'python publisher.py --flow-login' untuk membuka browser "
                "dan sinkronisasi akun Google Flow via Selenium."
            )

        cmd = [
            str(self.bin_path),
            "image",
            prompt,
            aspect,
            "--model", model
        ]
        res = subprocess.run(
            cmd,
            cwd=str(self.work_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        if res.returncode != 0:
            raise RuntimeError(f"Google Flow image generation failed: {res.stderr or res.stdout}")

        images = sorted(self.output_dir.glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True) + \
                 sorted(self.output_dir.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not images:
            raise RuntimeError("Google Flow image completed but output file not found.")
        return images[0]

    def generate_foundation_photos(
        self,
        product: Any,
        reference_garment: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        model: str = "narwhal",
        timeout: int = 180
    ) -> Dict[str, Path]:
        """Generates the 2 foundation photos for the Velora SOP:
        1. Foto 1 (Dekat / Macro): Dagu ke pinggang (detail tekstur kain & kerah).
        2. Foto 2 (Jauh / Wide): Tulang selangka ke paha/lutut (siluet outfit lengkap).
        Saves photos to output_dir (defaults to data/product_images/foundation/).
        """
        out_dir = output_dir or (Path(__file__).resolve().parent.parent / "data" / "product_images" / "foundation")
        out_dir.mkdir(parents=True, exist_ok=True)

        prod_id = getattr(product, "product_id", "GARMENT-01").replace("-", "_").lower()

        p1_prompt = GoogleFlowPromptEngine.synthesize_foundation_photo_prompt(product, photo_type="close_up")
        logger.info("Generating Foundation Photo 1 (Close-Up) for %s...", prod_id)
        p1_raw = self.generate_image(prompt=p1_prompt, aspect="9:16", model=model, timeout=timeout)
        p1_target = out_dir / f"{prod_id}_foundation_1_close.jpg"
        shutil.copy2(p1_raw, p1_target)

        # Brief cooldown between batchexecute calls
        time.sleep(3)

        p2_prompt = GoogleFlowPromptEngine.synthesize_foundation_photo_prompt(product, photo_type="wide_silhouette")
        logger.info("Generating Foundation Photo 2 (Wide Silhouette) for %s...", prod_id)
        p2_raw = self.generate_image(prompt=p2_prompt, aspect="9:16", model=model, timeout=timeout)
        p2_target = out_dir / f"{prod_id}_foundation_2_wide.jpg"
        shutil.copy2(p2_raw, p2_target)

        return {
            "close_up": p1_target,
            "wide_silhouette": p2_target
        }

    def generate_video(
        self,
        prompt: str,
        start_image: Optional[Path] = None,
        references: Optional[List[Path]] = None,
        aspect: str = "9:16",
        duration: str = "10s",
        quality: str = "720p",
        timeout: int = 300
    ) -> Path:
        """Generates or animates a 9:16 video clip via Google Flow with optional multi-references."""
        if not self.is_authenticated():
            raise FlowAuthError(
                "Google Flow cookies belum terpasang. "
                "Jalankan 'python publisher.py --flow-login' untuk membuka browser "
                "dan sinkronisasi akun Google Flow via Selenium."
            )

        dur_val = 10
        if isinstance(duration, int):
            dur_val = duration
        elif isinstance(duration, str):
            clean_d = duration.replace("s", "").strip()
            if clean_d.isdigit():
                dur_val = int(clean_d)

        cmd = [
            str(self.bin_path),
            "generate",
            "--prompt", prompt,
            "--aspect", str(aspect),
            "--duration", str(dur_val),
            "--quality", str(quality),
            "--project-id", "0cd53e0c-dae6-4b49-b362-727a82c2dd22"
        ]
        if start_image:
            cmd += ["--start-image", str(Path(start_image).resolve())]
        if references:
            for ref in references:
                if ref and Path(ref).exists():
                    cmd += ["--reference", str(Path(ref).resolve())]

        res = subprocess.run(
            cmd,
            cwd=str(self.work_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        if res.returncode != 0 and "PUBLIC_ERROR_UNUSUAL_ACTIVITY" in ((res.stderr or "") + (res.stdout or "")):
            logger.warning("Rate limit / cooldown detected from Google Flow. Waiting 20 seconds before retry...")
            time.sleep(20)
            res = subprocess.run(
                cmd,
                cwd=str(self.work_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )

        if res.returncode != 0:
            raise RuntimeError(f"Google Flow video generation failed: {res.stderr or res.stdout}")

        videos = sorted(self.output_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not videos:
            raise RuntimeError("Google Flow video completed but output file not found.")
        return videos[0]

    def generate_multiscene_video(
        self,
        scene_prompts: List[str],
        references: Optional[List[Path]] = None,
        duration_per_scene: int = 10,
        aspect: str = "9:16",
        quality: str = "720p",
        output_file: Optional[Path] = None,
        timeout_per_scene: int = 300
    ) -> Path:
        """Generates multiple scenes in sequence and stitches them into a seamless TikTok video."""
        if not scene_prompts:
            raise ValueError("scene_prompts must not be empty.")

        rendered_clips = []
        for idx, prompt_text in enumerate(scene_prompts, 1):
            logger.info("Rendering Scene %d/%d (%ds): %s", idx, len(scene_prompts), duration_per_scene, prompt_text[:60])
            clip = self.generate_video(
                prompt=prompt_text,
                references=references,
                aspect=aspect,
                duration=duration_per_scene,
                quality=quality,
                timeout=timeout_per_scene
            )
            rendered_clips.append(clip)

        target_out = output_file or (self.output_dir / f"multiscene_{int(time.time())}.mp4")
        target_out.parent.mkdir(parents=True, exist_ok=True)

        if len(rendered_clips) == 1:
            shutil.copy2(rendered_clips[0], target_out)
            return target_out

        # Stitch via FFmpeg concat filter on Drive D
        from src.config import DATA_DIR
        temp_dir = DATA_DIR / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        concat_list = temp_dir / f"concat_{int(time.time())}.txt"

        lines = [f"file '{str(p.resolve()).replace(chr(92), '/')}'" for p in rendered_clips]
        concat_list.write_text("\n".join(lines), encoding="utf-8")

        try:
            import imageio_ffmpeg
            ffmpeg_exe = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_exe = shutil.which("ffmpeg") or "ffmpeg"

        cmd = [
            ffmpeg_exe, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-vf", "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-threads", "1",
            "-c:a", "aac",
            str(target_out)
        ]
        logger.info("Stitching %d scenes into: %s", len(rendered_clips), target_out)
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0 or not target_out.exists():
            logger.warning("FFmpeg concat fallback: using last scene directly. Err: %s", res.stderr)
            shutil.copy2(rendered_clips[-1], target_out)

        return target_out

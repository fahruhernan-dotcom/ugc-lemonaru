"""Google Flow CDP Operator for DoniesDaily Pipeline.
Automates prompt generation and video asset downloads from official Google Flow
using Playwright connected via Chrome DevTools Protocol (:9222) on VPS persistent profile.
"""

import asyncio
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger("flow_cdp_operator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DEFAULT_PROJECT_URL = "https://flow.google.com/project/964abbc7-2441-4277-a4c6-93d1d7e755f9"
CDP_URL = "http://localhost:9222"

class FlowCDPOperator:
    def __init__(self, cdp_url: str = CDP_URL, project_url: str = DEFAULT_PROJECT_URL):
        self.cdp_url = cdp_url
        self.project_url = project_url

    def stop_chrome(self):
        """Stops Chrome and VNC cleanly to prevent memory leaks and zombie processes."""
        logger.info("🛑 Reaping Chrome and VNC to protect system memory...")
        try:
            subprocess.run(["/home/ubuntu/tools/flow_vnc_server.sh", "stop"], check=True, timeout=15)
        except Exception as e:
            logger.warning(f"Error while stopping flow VNC: {e}")

    def clean_cache(self, max_cache_mb: int = 300):
        """Purges Chrome cache if it exceeds threshold to prevent disk creep."""
        cache_dir = Path("/home/ubuntu/apps/ugc-lemonaru/data/chrome_persistent/Default/Cache")
        if cache_dir.exists():
            try:
                res = subprocess.run(["du", "-sm", str(cache_dir)], capture_output=True, text=True)
                size_mb = int(res.stdout.split()[0])
                if size_mb > max_cache_mb:
                    logger.info(f"🧹 Purging Chrome disk cache ({size_mb}MB > {max_cache_mb}MB)...")
                    subprocess.run(["rm", "-rf", str(cache_dir)], check=True)
            except Exception as e:
                logger.warning(f"Error purging Chrome cache: {e}")

    def ensure_chrome_running(self):
        """Verifies Chrome CDP listener on port 9222 is alive, launches if needed."""
        self.clean_cache()
        check = subprocess.run(["ss", "-tulpn"], capture_output=True, text=True)
        if "9222" not in check.stdout:
            logger.info("Starting Google Chrome persistent profile with CDP on :9222...")
            subprocess.run(["/home/ubuntu/tools/flow_vnc_server.sh", "start"], check=True)
            time.sleep(4)

    async def get_flow_page(self, browser: Browser) -> Page:
        context = browser.contexts[0]
        pages = context.pages
        for p in pages:
            if "flow.google.com" in p.url:
                if "project" not in p.url or "character" in p.url:
                    await p.goto(self.project_url)
                    await p.wait_for_timeout(3000)
                return p
        # If no flow page open, navigate page 0
        p = pages[0] if pages else await context.new_page()
        await p.goto(self.project_url)
        await p.wait_for_timeout(3000)
        return p

    async def send_prompt_and_wait(self, page: Page, prompt_text: str, timeout_sec: int = 50) -> bool:
        """Types prompt into Google Flow canvas input box, submits, and waits for completion."""
        logger.info(f"📤 Submitting prompt to Google Flow: '{prompt_text[:60]}...'")
        
        # Try locator for textarea / input first
        input_el = page.locator('textarea, [contenteditable="true"], input[type="text"]').last
        if await input_el.count() > 0 and await input_el.is_visible():
            await input_el.click()
            await input_el.fill(prompt_text)
            await page.keyboard.press("Enter")
        else:
            # Fallback to xdotool input coordinate (1050, 770) + submit button (1245, 815)
            env = {"DISPLAY": ":99"}
            p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE, env=env)
            p.communicate(input=prompt_text.encode("utf-8"))
            
            subprocess.run(["xdotool", "mousemove", "1050", "770", "click", "1"], env=env)
            await asyncio.sleep(0.5)
            subprocess.run(["xdotool", "key", "ctrl+a", "key", "BackSpace", "key", "ctrl+v"], env=env)
            await asyncio.sleep(0.5)
            subprocess.run(["xdotool", "mousemove", "1245", "815", "click", "1"], env=env)

        logger.info("⏳ Waiting for video generation render to finish...")
        # Poll canvas for completion (submit button returns to arrow_upward/arrow_forward or loading indicator clears)
        start_t = time.time()
        while time.time() - start_t < timeout_sec:
            await asyncio.sleep(4)
            # Check if generate button has re-enabled
            arrow = page.locator('button:has-text("arrow_upward"), button:has-text("arrow_forward"), [aria-label*="end"]')
            if await arrow.count() > 0:
                logger.info(f"✨ Generation finished in ~{int(time.time() - start_t)}s!")
                await asyncio.sleep(2)
                return True
        logger.warning(f"⚠️ Render wait hit {timeout_sec}s timeout, continuing...")
        return True

    async def download_tile(self, page: Page, tile_index: int, output_file: Path) -> bool:
        """Clicks a tile on the canvas, opens download menu, downloads 720p, and saves to output_file."""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        tiles = await page.locator("flow-grid-tile-container").all()
        if tile_index >= len(tiles):
            logger.warning(f"Tile index {tile_index} out of range (total: {len(tiles)})")
            return False

        t = tiles[tile_index]
        aria = await t.get_attribute("aria-label") or f"tile_{tile_index}"
        logger.info(f"📥 Downloading tile {tile_index} ('{aria}')...")
        await t.click()
        await page.wait_for_timeout(2500)

        dl_btn = page.locator('button[aria-label="Download media"], button:has-text("download"), [aria-label*="ownload"]').first
        if await dl_btn.count() > 0:
            await dl_btn.click()
            await page.wait_for_timeout(1500)

            p720 = page.locator('text="720p"').first
            p1080 = page.locator('text="1080p"').first
            target_opt = p720 if await p720.count() > 0 else (p1080 if await p1080.count() > 0 else dl_btn)

            try:
                async with page.expect_download(timeout=15000) as dl_info:
                    await target_opt.click()
                download = await dl_info.value
                await download.save_as(output_file)
                logger.info(f"✅ Saved {output_file.name} ({output_file.stat().st_size} bytes)")
                success = True
            except Exception as e:
                logger.error(f"❌ Failed to download tile: {e}")
                success = False
        else:
            logger.error("❌ Download button not found in preview modal")
            success = False

        # Close modal
        back = page.locator('button[aria-label="Back"], button:has-text("arrow_back")').first
        if await back.count() > 0:
            await back.click()
        else:
            await page.keyboard.press("Escape")
        await page.wait_for_timeout(2000)
        return success

    async def generate_scenes(
        self,
        prompts: List[str],
        output_dir: Path
    ) -> List[Path]:
        """Runs the generation loop for all prompt scenes and downloads them to output_dir."""
        self.ensure_chrome_running()
        output_dir.mkdir(parents=True, exist_ok=True)
        downloaded: List[Path] = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(self.cdp_url)
                page = await self.get_flow_page(browser)

                # Generate prompts one by one
                for idx, p_text in enumerate(prompts):
                    out_path = output_dir / f"scene_{idx + 1}.mp4"
                    if out_path.exists() and out_path.stat().st_size > 100000:
                        logger.info(f"Scene {idx + 1} already downloaded: {out_path.name}")
                        downloaded.append(out_path)
                        continue

                    await self.send_prompt_and_wait(page, p_text)
                    # The newest generated tile is tile index 1 (tile 0 is often collection/header)
                    saved = await self.download_tile(page, 1, out_path)
                    if saved:
                        downloaded.append(out_path)
        finally:
            self.stop_chrome()

        return downloaded

if __name__ == "__main__":
    op = FlowCDPOperator()
    print("FlowCDPOperator initialized successfully.")

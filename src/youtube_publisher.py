"""YouTube Shorts Studio Uploader Engine — Playwright-based.
Automates uploading and publishing video files to YouTube Studio using persistent session cookies.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from playwright.async_api import async_playwright

logger = logging.getLogger("youtube_publisher")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DEFAULT_COOKIE_PATH = Path("/home/ubuntu/.config/youtube/doniesdaily_cookies.json")


class YouTubePublisher:
    def __init__(self, cookie_path: Path = DEFAULT_COOKIE_PATH):
        self.cookie_path = cookie_path
        if not self.cookie_path.exists():
            raise FileNotFoundError(f"YouTube cookie file not found at {self.cookie_path}")
        with open(self.cookie_path, "r", encoding="utf-8") as f:
            self.cookies = json.load(f)

    def _prepare_cookies(self):
        cookies_list = []
        for c in self.cookies:
            item = dict(c)
            # Ensure boolean secure
            item["secure"] = bool(item.get("secure", False))
            cookies_list.append(item)
            # Duplicate for .google.com if domain is .youtube.com
            if ".youtube.com" in item.get("domain", ""):
                gc = dict(item)
                gc["domain"] = ".google.com"
                cookies_list.append(gc)
        return cookies_list

    async def upload_shorts(
        self,
        video_path: str,
        title: str,
        description: str,
        publish_mode: str = "public", # "public" or "unlisted" or "draft"
        headless: bool = True
    ) -> Dict[str, Any]:
        """Uploads a video to YouTube Studio and sets title, description, and visibility."""
        video_file = Path(video_path).resolve()
        if not video_file.exists():
            return {"success": False, "error": f"Video file not found: {video_file}"}

        cookies_to_inject = self._prepare_cookies()

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            await context.add_cookies(cookies_to_inject)
            page = await context.new_page()

            try:
                logger.info("Navigating to YouTube Studio...")
                await page.goto("https://studio.youtube.com", wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(4)

                # Check if studio loaded or redirected to login
                if "signin" in page.url:
                    return {"success": False, "error": "Cookie session expired or redirected to signin"}

                logger.info("Opening upload dialog...")
                # Try finding Create button or direct upload button
                create_btn = await page.query_selector("#create-icon") or await page.query_selector("button[aria-label='Create']") or await page.query_selector("#upload-icon")
                if create_btn:
                    await create_btn.click()
                    await asyncio.sleep(1)

                # Click Upload videos item
                upload_item = await page.query_selector("tp-yt-paper-item#text-item-0") or await page.query_selector("text='Upload videos'") or await page.query_selector("#upload-button")
                if upload_item:
                    await upload_item.click()
                    await asyncio.sleep(2)

                # Wait for file input (attached in DOM, even if hidden)
                logger.info("Waiting for file input...")
                file_input = await page.wait_for_selector("input[type='file']", state="attached", timeout=15000)
                if not file_input:
                    return {"success": False, "error": "Could not find file input element"}

                logger.info(f"Setting input file: {video_file}")
                await file_input.set_input_files(str(video_file))
                logger.info("File uploaded to browser. Waiting for upload details dialog...")
                await asyncio.sleep(8)

                # Fill Title
                logger.info("Filling title and description...")
                # YouTube Studio title input uses contenteditable div or #textbox
                title_box = await page.query_selector("#title-textarea #textbox") or await page.query_selector("#textbox[aria-label*='title']")
                if title_box:
                    await title_box.fill(title)
                else:
                    logger.warning("Could not find title box, trying fallback click")

                # Fill Description
                desc_box = await page.query_selector("#description-textarea #textbox") or await page.query_selector("#textbox[aria-label*='description']")
                if desc_box:
                    await desc_box.fill(description)

                # Audience: "No, it's not made for kids" (Name: VIDEO_MADE_FOR_KIDS_NOT_MFK)
                logger.info("Setting audience to Not Made for Kids...")
                not_for_kids = await page.query_selector("tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']") or await page.query_selector("#radioLabel:has-text('No, it\\'s not made for kids')")
                if not_for_kids:
                    await not_for_kids.click()

                await asyncio.sleep(2)

                # Step through Next buttons (Video elements, Checks, Visibility)
                logger.info("Stepping through details wizard...")
                for step in range(3):
                    next_btn = await page.query_selector("#next-button")
                    if next_btn and await next_btn.is_enabled():
                        await next_btn.click()
                        await asyncio.sleep(2)

                # Set Visibility
                if publish_mode == "public":
                    logger.info("Selecting Public visibility...")
                    public_radio = await page.query_selector("tp-yt-paper-radio-button[name='PUBLIC']") or await page.query_selector("#radioLabel:has-text('Public')")
                    if public_radio:
                        await public_radio.click()
                elif publish_mode == "unlisted":
                    logger.info("Selecting Unlisted visibility...")
                    unlisted_radio = await page.query_selector("tp-yt-paper-radio-button[name='UNLISTED']") or await page.query_selector("#radioLabel:has-text('Unlisted')")
                    if unlisted_radio:
                        await unlisted_radio.click()

                await asyncio.sleep(2)

                # Click Done / Publish
                logger.info("Publishing video...")
                done_btn = await page.query_selector("#done-button")
                if done_btn and await done_btn.is_enabled():
                    await done_btn.click()
                    logger.info("Publish button clicked! Waiting for confirmation...")
                    await asyncio.sleep(6)

                # Grab video URL if available
                video_url = ""
                link_elem = await page.query_selector("a.ytcp-video-info") or await page.query_selector("a[href*='youtu.be']")
                if link_elem:
                    video_url = await link_elem.get_attribute("href") or ""

                # Take confirmation screenshot
                screenshot_path = f"/tmp/yt_upload_{int(asyncio.get_event_loop().time())}.png"
                await page.screenshot(path=screenshot_path)
                logger.info(f"Upload process complete! Screenshot: {screenshot_path}")

                await browser.close()
                return {
                    "success": True,
                    "title": title,
                    "video_url": video_url,
                    "screenshot": screenshot_path,
                    "mode": publish_mode
                }

            except Exception as e:
                logger.error(f"Error during YouTube upload: {e}")
                err_screenshot = "/tmp/yt_upload_error.png"
                await page.screenshot(path=err_screenshot)
                await browser.close()
                return {"success": False, "error": str(e), "screenshot": err_screenshot}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python youtube_publisher.py <video_path> <title> [description]")
        sys.exit(1)

    vid = sys.argv[1]
    tit = sys.argv[2]
    desc = sys.argv[3] if len(sys.argv) > 3 else "#Shorts #Cat #KucingLucu"

    pub = YouTubePublisher()
    result = asyncio.run(pub.upload_shorts(vid, tit, desc, publish_mode="public"))
    print(json.dumps(result, indent=2))

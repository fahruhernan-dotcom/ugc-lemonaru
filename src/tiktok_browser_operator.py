"""TikTok Browser Operator via Playwright + Persistent Chrome Profile.
Adapts the proven automation architecture from 'Juragan by Anak Bawang/Automasi_Medsos/auto_post_browser.py':
1. Launches genuine Chrome with persistent user-data-dir on Drive D.
2. Directs temp files to Drive D to avoid drive C space limits.
3. User authenticates manually once in genuine Chrome (QR code or credentials).
4. Playwright inspects, uploads video packages, and drafts posts to TikTok Creator Studio.
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional
from playwright.sync_api import sync_playwright

from src.config import DATA_DIR, OUTPUT_DIR, ROOT_DIR

# Route all temporary files to Drive D:
TEMP_DIR = DATA_DIR / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(TEMP_DIR.resolve())
os.environ["TMP"] = str(TEMP_DIR.resolve())
tempfile.tempdir = str(TEMP_DIR.resolve())

logger = logging.getLogger("velora.tiktok_browser")

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DEFAULT_PORT = 9222
TIKTOK_PROFILE_DIR = DATA_DIR / "chrome_profile_tiktok"
TIKTOK_STUDIO_URL = "https://www.tiktok.com/tiktokstudio"
TIKTOK_UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload"


def is_remote_chrome_running(port: int = DEFAULT_PORT) -> bool:
    """Checks if Chrome Remote Debugging port is currently open and responsive."""
    try:
        url = f"http://127.0.0.1:{port}/json/version"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode())
            logger.info(f"Connected to Chrome CDP: {data.get('Browser', 'Unknown')}")
            return True
    except Exception:
        return False


def launch_chrome_for_tiktok(
    port: int = DEFAULT_PORT,
    profile_dir: Optional[Path] = None,
    target_url: str = TIKTOK_UPLOAD_URL
) -> bool:
    """Launches local Chrome with remote debugging and persistent user profile."""
    if is_remote_chrome_running(port):
        logger.info(f"Chrome remote debugging is already running on port {port}.")
        return True

    p_dir = profile_dir or TIKTOK_PROFILE_DIR
    p_dir.mkdir(parents=True, exist_ok=True)

    if not Path(CHROME_PATH).exists():
        logger.error(f"Chrome executable not found at: {CHROME_PATH}")
        return False

    cmd = [
        CHROME_PATH,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={p_dir.resolve()}",
        "--no-first-run",
        "--no-default-browser-check",
        target_url
    ]
    logger.info(f"Launching Chrome with profile: {p_dir.resolve()}")
    subprocess.Popen(cmd)

    for _ in range(10):
        time.sleep(1)
        if is_remote_chrome_running(port):
            logger.info("Chrome remote debugging port is ready.")
            return True

    logger.warning("Timed out waiting for Chrome remote debugging port.")
    return False


class TikTokBrowserOperator:
    """Controls TikTok Creator Studio using Playwright."""

    def __init__(self, port: int = DEFAULT_PORT, profile_dir: Optional[Path] = None):
        self.port = port
        self.profile_dir = profile_dir or TIKTOK_PROFILE_DIR
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.mode = "cdp"  # "cdp" or "persistent"

    def launch_persistent(self, headless: bool = False, target_url: str = TIKTOK_UPLOAD_URL) -> bool:
        """Launches Chrome using Playwright persistent context directly."""
        try:
            self.pw = sync_playwright().start()
            self.context = self.pw.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir.resolve()),
                executable_path=CHROME_PATH,
                headless=headless,
                args=[
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-blink-features=AutomationControlled",
                ],
                viewport={"width": 1280, "height": 900}
            )
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            self.mode = "persistent"
            logger.info("Playwright launched persistent Chrome context successfully.")
            if target_url:
                self.page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            return True
        except Exception as e:
            logger.error(f"Failed to launch persistent context: {e}")
            return False

    def connect_cdp(self) -> bool:
        """Connects Playwright to running Chrome instance via CDP."""
        if not is_remote_chrome_running(self.port):
            logger.info("Chrome not running, launching now...")
            if not launch_chrome_for_tiktok(self.port):
                return False

        self.pw = sync_playwright().start()
        try:
            self.browser = self.pw.chromium.connect_over_cdp(f"http://127.0.0.1:{self.port}")
            self.context = self.browser.contexts[0]
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
            self.mode = "cdp"
            logger.info("Playwright successfully attached to Chrome via CDP.")
            return True
        except Exception as e:
            logger.error(f"Failed to connect Playwright over CDP: {e}")
            return False

    def connect(self) -> bool:
        """Preferred connect method: tries CDP first if active, else launches persistent context."""
        if is_remote_chrome_running(self.port):
            return self.connect_cdp()
        return self.launch_persistent(headless=False)

    def close(self):
        """Cleanly releases Playwright connections without terminating background profile."""
        try:
            if self.mode == "cdp" and self.browser:
                self.browser.disconnect()
            elif self.mode == "persistent" and self.context:
                self.context.close()
        except Exception:
            pass
        try:
            if self.pw:
                self.pw.stop()
        except Exception:
            pass

    def check_login_status(self) -> Dict[str, Any]:
        """Checks if current Chrome page is logged in to TikTok."""
        if not self.page:
            return {"status": "ERROR", "message": "Browser page not connected"}

        current_url = self.page.url
        logger.info(f"Inspecting current page URL: {current_url}")

        if "/login" in current_url:
            logged_in = False
        else:
            try:
                avatar = self.page.locator('[data-e2e="profile-icon"], img[class*="avatar"], div[class*="avatar"]').first
                login_btn = self.page.locator('button:text("Log in"), button:text("Masuk"), a[href*="login"]').first
                if avatar.is_visible(timeout=3000):
                    logged_in = True
                elif ("tiktokstudio" in current_url or "creator-center" in current_url) and not login_btn.is_visible(timeout=2000):
                    logged_in = True
                else:
                    logged_in = False
            except Exception:
                logged_in = False

        screenshot_path = OUTPUT_DIR / "tiktok_login_check.png"
        try:
            self.page.screenshot(path=str(screenshot_path))
        except Exception:
            pass

        return {
            "status": "LOGGED_IN" if logged_in else "AWAITING_LOGIN",
            "current_url": current_url,
            "logged_in": logged_in,
            "screenshot": str(screenshot_path)
        }

    def inspect_upload_interface(self) -> Dict[str, Any]:
        """Navigates to Creator Center upload page and checks available controls."""
        if not self.page:
            return {"status": "ERROR", "message": "Not connected"}

        logger.info(f"Navigating to: {TIKTOK_UPLOAD_URL}")
        try:
            self.page.goto(TIKTOK_UPLOAD_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)
        except Exception as e:
            logger.warning(f"Navigation warning: {e}")

        # Check for file input
        file_input = self.page.locator('input[type="file"]').first
        has_file_input = False
        try:
            has_file_input = file_input.count() > 0
        except Exception:
            pass

        # Check for caption editor
        caption_area = self.page.locator('[contenteditable="true"], textarea, div[class*="caption"]').first
        has_caption_area = False
        try:
            has_caption_area = caption_area.is_visible(timeout=2000)
        except Exception:
            pass

        screenshot_path = OUTPUT_DIR / "tiktok_upload_inspection.png"
        try:
            self.page.screenshot(path=str(screenshot_path))
        except Exception:
            pass

        return {
            "status": "SUCCESS",
            "url": self.page.url,
            "is_login_page": "/login" in self.page.url,
            "has_file_input": has_file_input,
            "has_caption_area": has_caption_area,
            "inspection_screenshot": str(screenshot_path)
        }

    def toggle_aigc_disclosure(self) -> bool:
        """Toggles AI-generated content disclosure switch via Playwright."""
        if not self.page:
            return False
        try:
            aigc_switch = self.page.locator('//span[contains(text(), "AI-generated") or contains(text(), "buatan AI")]/following::*[@role="switch"][1]').first
            if aigc_switch.is_visible(timeout=2000):
                is_checked = aigc_switch.get_attribute("aria-checked") == "true"
                if not is_checked:
                    aigc_switch.click()
                    logger.info("Playwright toggled AIGC switch ON.")
                    return True
                return True
        except Exception:
            pass
        return False

    def save_as_draft(self) -> bool:
        """Finds and clicks 'Save as draft' button via Playwright."""
        if not self.page:
            return False
        try:
            draft_btn = self.page.locator('button:text("Save as draft"), button:text("Simpan draf"), button:text("Draft")').first
            if draft_btn.is_visible(timeout=3000):
                draft_btn.click()
                logger.info("Playwright clicked 'Save as draft'.")
                time.sleep(4)
                return True
        except Exception:
            pass
        return False

    def prepare_package_upload(self, package_path: str, save_draft: bool = True, publish_live: bool = False) -> Dict[str, Any]:
        """Loads video, caption, toggles AIGC, and stages as draft in TikTok upload page."""
        pkg_dir = Path(package_path)
        if not pkg_dir.exists():
            return {"status": "ERROR", "message": f"Package not found: {package_path}"}

        video_file = pkg_dir / "video.mp4"
        caption_file = pkg_dir / "caption.txt"

        if not video_file.exists():
            return {"status": "ERROR", "message": f"video.mp4 not found in package: {pkg_dir}"}

        caption_text = ""
        if caption_file.exists():
            with open(caption_file, "r", encoding="utf-8") as f:
                caption_text = f.read().strip()

        logger.info(f"Preparing upload for: {video_file.name}")
        self.page.goto(TIKTOK_UPLOAD_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(4)

        if "/login" in self.page.url:
            return {
                "status": "ERROR",
                "message": "Not logged in to TikTok. Run python publisher.py --login first.",
                "current_url": self.page.url
            }

        file_input = self.page.locator('input[type="file"]').first
        file_input.wait_for(state="attached", timeout=15000)
        file_input.set_input_files(str(video_file.resolve()))
        logger.info("File attached to upload element.")

        time.sleep(8)  # Wait for TikTok transcoding / upload progress

        # Fill caption if editor visible
        caption_applied = False
        try:
            caption_box = self.page.locator('[contenteditable="true"]').first
            if caption_box.is_visible(timeout=5000):
                caption_box.click()
                self.page.keyboard.type(caption_text, delay=10)
                caption_applied = True
                logger.info("Caption typed successfully.")
        except Exception as e:
            logger.warning(f"Could not type caption automatically: {e}")

        # Toggle AIGC
        aigc_toggled = self.toggle_aigc_disclosure()

        # Handle Draft Staging
        draft_saved = False
        if save_draft and not publish_live:
            draft_saved = self.save_as_draft()

        screenshot_path = OUTPUT_DIR / f"tiktok_playwright_prepared_{pkg_dir.name}.png"
        try:
            self.page.screenshot(path=str(screenshot_path))
        except Exception:
            pass

        return {
            "status": "STAGED_AS_DRAFT" if draft_saved else "PREPARED",
            "package_id": pkg_dir.name,
            "video_path": str(video_file),
            "caption_applied": caption_applied,
            "aigc_disclosed": aigc_toggled,
            "draft_saved": draft_saved,
            "screenshot": str(screenshot_path),
            "next_step": "Open TikTok App on mobile -> Drafts -> Attach Yellow Cart Product Link -> Post" if draft_saved else "Inspect in Studio"
        }


def run_interactive_login():
    """Runs guided interactive login assistant in real Chrome."""
    print("=" * 65)
    print("📱 TIKTOK CREATOR STUDIO LOGIN ASSISTANT (PLAYWRIGHT)")
    print("=" * 65)
    print("1. Jendela Chrome akan terbuka di layar Anda.")
    print("2. Silakan login ke TikTok di jendela tersebut:")
    print("   👉 Rekomendasi: Klik 'Use QR code', lalu buka aplikasi TikTok di HP,")
    print("      ketuk menu 'Profil' -> pojok kanan atas -> 'Kode QR' / 'Pindai'.")
    print("3. Setelah berhasil masuk ke TikTok Studio,")
    print("   kembali ke terminal ini dan tekan ENTER.")
    print("=" * 65)

    op = TikTokBrowserOperator()
    try:
        op.launch_persistent(headless=False)
        input("\n👉 Tekan ENTER di sini jika Anda SUDAH berhasil login di Chrome... ")
        status = op.check_login_status()
        print("\nHasil Pemeriksaan Status Login:")
        print(json.dumps(status, indent=2))
    finally:
        op.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="TikTok Browser Operator CLI.")
    parser.add_argument("--login", action="store_true", help="Launch interactive login assistant")
    parser.add_argument("--status", action="store_true", help="Check login status")
    parser.add_argument("--inspect", action="store_true", help="Inspect upload UI")
    parser.add_argument("--upload-pkg", type=str, help="Path to ready_to_publish package")

    args = parser.parse_args()

    if args.login:
        run_interactive_login()
        return

    op = TikTokBrowserOperator()
    if not op.connect():
        print("Could not launch or connect to Chrome.")
        sys.exit(1)

    try:
        if args.status:
            res = op.check_login_status()
            print(json.dumps(res, indent=2))
        elif args.inspect:
            res = op.inspect_upload_interface()
            print(json.dumps(res, indent=2))
        elif args.upload_pkg:
            res = op.prepare_package_upload(args.upload_pkg)
            print(json.dumps(res, indent=2))
        else:
            print("Specify --login, --status, --inspect, or --upload-pkg <path>")
    finally:
        op.close()


if __name__ == "__main__":
    main()

"""TikTok Selenium Operator using undetected-chromedriver.
Mirrors the proven automation pattern from 'Juragan by Anak Bawang/Automasi_Medsos/auto_post_selenium.py':
1. Uses undetected-chromedriver with a persistent Chrome profile on Drive D.
2. Directs temporary files to Drive D to avoid disk space bottlenecks.
3. Supports interactive QR/manual login with session persistence.
4. Automates video file attachment and caption pasting with pyperclip.
"""

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure TEMP is on Drive D before importing libraries that write to temp
from src.config import DATA_DIR, OUTPUT_DIR, ROOT_DIR

TEMP_DIR = DATA_DIR / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(TEMP_DIR.resolve())
os.environ["TMP"] = str(TEMP_DIR.resolve())
tempfile.tempdir = str(TEMP_DIR.resolve())

logger = logging.getLogger("velora.tiktok_selenium")

SELENIUM_PROFILE_DIR = DATA_DIR / "chrome_profile_tiktok_selenium"
TIKTOK_STUDIO_URL = "https://www.tiktok.com/tiktokstudio"
TIKTOK_UPLOAD_URL = "https://www.tiktok.com/tiktokstudio/upload"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def get_chrome_version() -> Optional[int]:
    """Retrieves major Chrome version from Windows registry."""
    try:
        cmd = r'reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version'
        output = subprocess.check_output(cmd, shell=True, text=True)
        match = re.search(r"version\s+REG_SZ\s+(\d+)", output)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    try:
        cmd = r'reg query "HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Google Chrome" /v DisplayVersion'
        output = subprocess.check_output(cmd, shell=True, text=True)
        match = re.search(r"DisplayVersion\s+REG_SZ\s+(\d+)", output)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return None


class TikTokSeleniumOperator:
    """Controls TikTok Creator Studio using undetected-chromedriver."""

    def __init__(self, profile_dir: Optional[Path] = None):
        self.profile_dir = profile_dir or SELENIUM_PROFILE_DIR
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.driver = None

    def start_driver(self) -> Any:
        """Initializes undetected-chromedriver with persistent profile."""
        if self.driver:
            return self.driver

        import undetected_chromedriver as uc

        chrome_ver = get_chrome_version()
        options = uc.ChromeOptions()
        options.add_argument(f"--user-data-dir={self.profile_dir.resolve()}")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")

        logger.info(f"Initializing Undetected ChromeDriver (Chrome major ver: {chrome_ver})...")
        try:
            if chrome_ver:
                self.driver = uc.Chrome(options=options, version_main=chrome_ver, use_subprocess=True)
            else:
                self.driver = uc.Chrome(options=options, use_subprocess=True)
        except Exception as e:
            logger.warning(f"Fallback init without version_main: {e}")
            self.driver = uc.Chrome(options=options, use_subprocess=True)

        self.driver.set_window_size(1280, 900)
        return self.driver

    def close(self):
        """Quits the browser session cleanly."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def check_login_status(self) -> Dict[str, Any]:
        """Navigates to TikTok Studio and checks if logged in."""
        driver = self.start_driver()
        from selenium.webdriver.common.by import By

        driver.get(TIKTOK_STUDIO_URL)
        time.sleep(4)

        current_url = driver.current_url
        is_login_page = "/login" in current_url

        logged_in = False
        username = None

        if not is_login_page:
            if "tiktokstudio" in current_url or "creator-center" in current_url:
                logged_in = True

            try:
                # Try finding username element
                user_elems = driver.find_elements(By.XPATH, '//*[contains(@class, "user-name") or contains(text(), "velorastudio")]')
                for ue in user_elems:
                    txt = ue.text.strip()
                    if txt:
                        username = txt
                        break
            except Exception:
                pass

        screenshot_path = OUTPUT_DIR / "tiktok_selenium_login_check.png"
        driver.save_screenshot(str(screenshot_path))

        return {
            "status": "LOGGED_IN" if logged_in else "AWAITING_LOGIN",
            "current_url": current_url,
            "logged_in": logged_in,
            "username": username or "velorastudiofashion",
            "screenshot": str(screenshot_path)
        }

    def dismiss_dialogs_and_popups(self) -> None:
        """Dismisses content check modals, tour guides, and tooltips in TikTok Studio."""
        if not self.driver:
            return
        from selenium.webdriver.common.by import By
        for attempt in range(4):
            clicked = False
            try:
                # 1. Turn on content checks button or Cancel
                turn_on_btns = self.driver.find_elements(
                    By.XPATH,
                    '//button[normalize-space()="Turn on" or contains(text(), "Turn on") or normalize-space()="Cancel"]'
                )
                for b in turn_on_btns:
                    if b.is_displayed():
                        try:
                            b.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", b)
                        logger.info("Handled content check dialog via '%s'", b.text)
                        time.sleep(1)
                        clicked = True
                        break

                # 2. Dismiss guides / tooltips (Got it, Close, etc.)
                guide_btns = self.driver.find_elements(
                    By.XPATH,
                    '//button[contains(., "Got it") or contains(., "got it") or contains(., "Next") or contains(@aria-label, "close") or contains(@aria-label, "Close")] | //div[@role="tooltip"]//button | //div[contains(@class, "popover")]//button'
                )
                for b in guide_btns:
                    if b.is_displayed():
                        try:
                            b.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", b)
                        logger.info("Dismissed guide dialog via '%s'", b.text)
                        time.sleep(1)
                        clicked = True
                        break
            except Exception as e:
                logger.debug("Error while dismissing dialogs: %s", e)
            if not clicked:
                break
            time.sleep(1)

    def _scroll_page_down(self) -> None:
        """Scrolls window and all internal scrollable containers to the bottom."""
        if not self.driver:
            return
        scroll_script = """
        window.scrollTo(0, 99999);
        let elements = document.querySelectorAll('div, main, section, form');
        for (let el of elements) {
            if (el.scrollHeight > el.clientHeight && el.clientHeight > 200) {
                el.scrollTop = el.scrollHeight;
            }
        }
        """
        try:
            self.driver.execute_script(scroll_script)
            time.sleep(1)
        except Exception:
            pass

    def toggle_aigc_disclosure(self) -> bool:
        """Finds and toggles the AI-generated content switch in TikTok Studio."""
        if not self.driver:
            return False
        from selenium.webdriver.common.by import By

        self._scroll_page_down()

        # 1. Click 'Show more' button to expand hidden settings
        try:
            show_more_btns = self.driver.find_elements(
                By.XPATH,
                '//*[normalize-space()="Show more" or contains(text(), "Show more") or contains(text(), "Tampilkan lebih banyak")]'
            )
            for sm in show_more_btns:
                if sm.is_displayed():
                    try:
                        sm.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", sm)
                    logger.info("Clicked 'Show more' to reveal advanced settings.")
                    time.sleep(1)
                    break
        except Exception as e:
            logger.debug("Error clicking Show more: %s", e)

        self._scroll_page_down()

        # Expand disclosure accordion / section if collapsed
        try:
            disclosure_headers = self.driver.find_elements(
                By.XPATH,
                '//div[contains(text(), "Content disclosure") or contains(text(), "Pengungkapan konten") or contains(text(), "Commercial content") or contains(text(), "Promotional")]'
            )
            for dh in disclosure_headers:
                if dh.is_displayed():
                    try:
                        dh.click()
                        time.sleep(1)
                    except Exception:
                        pass
        except Exception:
            pass

        selectors = [
            '//span[contains(text(), "AI-generated") or contains(text(), "buatan AI")]/following::*[@role="switch"][1]',
            '//span[contains(text(), "AI-generated") or contains(text(), "buatan AI")]/ancestor::label//input[@type="checkbox"]',
            '//span[contains(text(), "AI-generated") or contains(text(), "buatan AI")]/ancestor::div[contains(@class, "switch")]',
            '//div[contains(text(), "AI-generated") or contains(text(), "buatan AI")]/following::*[@role="switch"][1]',
            '//*[@aria-label="AI-generated content" or @aria-label="Konten buatan AI"]',
            '//input[@type="checkbox" and (contains(@name, "aigc") or contains(@id, "aigc"))]',
        ]
        for sel in selectors:
            try:
                elems = self.driver.find_elements(By.XPATH, sel)
                for el in elems:
                    if el.is_displayed():
                        checked = el.get_attribute("aria-checked") or el.get_attribute("checked")
                        if checked not in ["true", True, "checked"]:
                            try:
                                el.click()
                            except Exception:
                                self.driver.execute_script("arguments[0].click();", el)
                            logger.info("AIGC toggle enabled successfully.")
                            return True
                        logger.info("AIGC toggle already enabled.")
                        return True
            except Exception:
                continue
        logger.info("AIGC toggle element not found or already default.")
        return False

    def save_as_draft(self) -> bool:
        """Finds and clicks 'Save as draft' button in TikTok Studio."""
        if not self.driver:
            return False
        from selenium.webdriver.common.by import By

        self._scroll_page_down()

        # Log all buttons visible for diagnostics
        try:
            all_btn_info = self.driver.execute_script("""
                return Array.from(document.querySelectorAll('button')).map(b => ({
                    text: b.innerText.trim(),
                    visible: b.offsetParent !== null
                })).filter(b => b.text.length > 0);
            """)
            logger.info("Buttons found on page: %s", all_btn_info)
        except Exception:
            pass

        selectors = [
            '//button[contains(text(), "Save as draft") or contains(text(), "Simpan draf") or contains(text(), "Draft")]',
            '//button[contains(., "Save as draft") or contains(., "Simpan draf")]',
            '//div[contains(@class, "draft-btn")]//button',
            '//button[@data-e2e="save-draft-button"]',
        ]
        for sel in selectors:
            try:
                btns = self.driver.find_elements(By.XPATH, sel)
                for btn in btns:
                    if btn.is_displayed():
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                        time.sleep(0.5)
                        try:
                            btn.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", btn)
                        logger.info("Clicked 'Save as draft' button.")
                        time.sleep(5)
                        return True
            except Exception:
                continue

        # JS fallback click on any button with 'draft' or 'draf'
        try:
            clicked_via_js = self.driver.execute_script("""
                let btns = Array.from(document.querySelectorAll('button'));
                for (let b of btns) {
                    let txt = (b.innerText || '').toLowerCase();
                    if (txt.includes('draft') || txt.includes('draf')) {
                        b.click();
                        return true;
                    }
                }
                return false;
            """)
            if clicked_via_js:
                logger.info("Clicked draft button via JavaScript fallback.")
                time.sleep(5)
                return True
        except Exception as exc:
            logger.warning("Error in JS draft button fallback: %s", exc)

        return False

    def prepare_package_upload(self, package_path: str, save_draft: bool = True, publish_live: bool = False) -> Dict[str, Any]:
        """Uploads package video, enters caption, enables AIGC tag, and stages as draft."""
        driver = self.start_driver()
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
        import pyperclip

        pkg_dir = Path(package_path)
        video_file = pkg_dir / "video.mp4"
        caption_file = pkg_dir / "caption.txt"

        if not video_file.exists():
            return {"status": "ERROR", "message": f"video.mp4 not found in {package_path}"}

        caption_text = ""
        if caption_file.exists():
            with open(caption_file, "r", encoding="utf-8") as f:
                caption_text = f.read().strip()

        logger.info(f"Navigating to upload: {TIKTOK_UPLOAD_URL}")
        driver.get(TIKTOK_UPLOAD_URL)
        time.sleep(5)

        if "/login" in driver.current_url:
            return {
                "status": "ERROR",
                "message": "Not logged in to TikTok. Run python publisher.py --login first.",
                "current_url": driver.current_url
            }

        # Wait for file input
        file_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//input[@type="file"]'))
        )
        file_input.send_keys(str(video_file.resolve()))
        logger.info(f"Attached video file: {video_file.name}")

        # Wait for upload & transcoding to begin
        time.sleep(8)

        # Dismiss any popups or modals
        self.dismiss_dialogs_and_popups()

        # Fill caption with pyperclip (clipboard paste)
        caption_applied = False
        if caption_text:
            caption_selectors = [
                '//*[@contenteditable="true"]',
                '//div[contains(@class, "notranslate") and @contenteditable="true"]',
                '//div[@data-e2e="caption-editor"]',
                '//textarea[contains(@class, "caption")]',
            ]
            for sel in caption_selectors:
                try:
                    boxes = driver.find_elements(By.XPATH, sel)
                    for box in boxes:
                        if box.is_displayed():
                            try:
                                box.click()
                            except Exception:
                                driver.execute_script("arguments[0].focus();", box)
                            time.sleep(0.5)
                            box.send_keys(Keys.CONTROL, "a")
                            time.sleep(0.2)
                            box.send_keys(Keys.BACKSPACE)
                            time.sleep(0.2)
                            pyperclip.copy(caption_text)
                            box.send_keys(Keys.CONTROL, "v")
                            time.sleep(0.5)
                            box.send_keys(Keys.ESCAPE)
                            caption_applied = True
                            logger.info("Caption successfully pasted via pyperclip and autocomplete dismissed.")
                            break
                    if caption_applied:
                        break
                except Exception as e:
                    logger.debug(f"Caption selector attempt error: {e}")

        # Enable AIGC disclosure toggle
        aigc_toggled = self.toggle_aigc_disclosure()

        # Dismiss dialogs again if any appeared after interaction
        self.dismiss_dialogs_and_popups()

        # Handle Draft Staging vs Live Publishing
        draft_saved = False
        post_published = False

        if save_draft and not publish_live:
            draft_saved = self.save_as_draft()

        screenshot_path = OUTPUT_DIR / f"tiktok_selenium_prepared_{pkg_dir.name}.png"
        driver.save_screenshot(str(screenshot_path))

        return {
            "status": "STAGED_AS_DRAFT" if draft_saved else ("PUBLISHED" if post_published else "PREPARED"),
            "package_id": pkg_dir.name,
            "video_path": str(video_file),
            "caption_applied": caption_applied,
            "aigc_disclosed": aigc_toggled,
            "draft_saved": draft_saved,
            "screenshot": str(screenshot_path),
            "next_step": "Open TikTok App on mobile -> Drafts -> Attach Yellow Cart Product Link -> Post" if draft_saved else "Inspect in Studio"
        }


def run_interactive_login(mode: str = "playwright"):
    """Interactive login helper for either Playwright or Selenium."""
    print("=" * 65)
    print(f"📱 TIKTOK CREATOR STUDIO LOGIN ASSISTANT ({mode.upper()})")
    print("=" * 65)
    print("1. Jendela Chrome akan dibuka dengan profil TikTok Anda.")
    print("2. Silakan login ke TikTok di jendela tersebut:")
    print("   👉 Rekomendasi: Klik 'Use QR code', lalu buka aplikasi TikTok di HP,")
    print("      ketuk menu 'Profil' -> pojok kanan atas -> 'Kode QR' / 'Pindai'.")
    print("3. Setelah berhasil masuk ke beranda TikTok Studio,")
    print("   kembali ke terminal ini dan tekan ENTER.")
    print("=" * 65)

    if mode == "selenium":
        op = TikTokSeleniumOperator()
        try:
            op.start_driver()
            op.driver.get(TIKTOK_STUDIO_URL)
            input("\n👉 Tekan ENTER jika Anda SUDAH berhasil login di Chrome... ")
            status = op.check_login_status()
            print("\nHasil Pemeriksaan Status Login:")
            print(json.dumps(status, indent=2))
        finally:
            op.close()
    else:
        from src.tiktok_browser_operator import TikTokBrowserOperator
        op = TikTokBrowserOperator()
        try:
            op.launch_persistent()
            input("\n👉 Tekan ENTER jika Anda SUDAH berhasil login di Chrome... ")
            status = op.check_login_status()
            print("\nHasil Pemeriksaan Status Login:")
            print(json.dumps(status, indent=2))
        finally:
            op.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TikTok Selenium Operator CLI")
    parser.add_argument("--login", action="store_true", help="Run interactive login assistant")
    parser.add_argument("--status", action="store_true", help="Check login status")
    parser.add_argument("--upload-pkg", type=str, help="Upload package to TikTok Studio")
    args = parser.parse_args()

    op = TikTokSeleniumOperator()
    if args.login:
        run_interactive_login(mode="selenium")
    elif args.status:
        try:
            res = op.check_login_status()
            print(json.dumps(res, indent=2))
        finally:
            op.close()
    elif args.upload_pkg:
        try:
            res = op.prepare_package_upload(args.upload_pkg)
            print(json.dumps(res, indent=2))
        finally:
            op.close()
    else:
        print("Usage: python -m src.tiktok_selenium_operator --login | --status | --upload-pkg <path>")

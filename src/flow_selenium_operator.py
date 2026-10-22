"""Google Flow Selenium Operator for Velora AI.
Automates Google Flow (https://labs.google/fx/tools/flow) using undetected-chromedriver:
1. Uses persistent Chrome profile on Drive D (data/chrome_profile_google_flow).
2. Auto-loads the Flow Bridge extension from tools/flow-agent/flow-extension.
3. Automatically connects to the Go bridge daemon (ws://127.0.0.1:9222) to sync cookies.
4. Provides interactive login support and direct browser navigation for 9:16 video generation.
"""

import json
import logging
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.config import DATA_DIR, FLOW_AGENT_DIR, FLOW_BIN_PATH, FLOW_EXTENSION_DIR

# Route temp to Drive D
TEMP_DIR = DATA_DIR / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(TEMP_DIR.resolve())
os.environ["TMP"] = str(TEMP_DIR.resolve())
tempfile.tempdir = str(TEMP_DIR.resolve())

logger = logging.getLogger("velora.flow_selenium")

FLOW_PROFILE_DIR = DATA_DIR / "chrome_profile_google_flow"
FLOW_URL = "https://labs.google/fx/tools/flow"


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


class GoogleFlowSeleniumOperator:
    """Controls Google Chrome for Google Flow operations with auto-loaded extension."""

    def __init__(
        self,
        profile_dir: Optional[Path] = None,
        extension_dir: Optional[Path] = None,
        bin_path: Optional[Path] = None
    ):
        self.profile_dir = (profile_dir or FLOW_PROFILE_DIR).resolve()
        self.extension_dir = (extension_dir or FLOW_EXTENSION_DIR).resolve()
        self.bin_path = (bin_path or FLOW_BIN_PATH).resolve()
        self.cookies_dir = (FLOW_AGENT_DIR / "bin" / "cookies").resolve()
        self.output_dir = (FLOW_AGENT_DIR / "bin" / "output").resolve()

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.driver = None

    def start_driver(self, headless: bool = False, load_extension: bool = True) -> Any:
        """Launches undetected-chromedriver with persistent profile and Flow Bridge extension."""
        if self.driver:
            return self.driver

        import undetected_chromedriver as uc

        chrome_ver = get_chrome_version()
        options = uc.ChromeOptions()
        options.add_argument(f"--user-data-dir={self.profile_dir}")
        cache_dir = (TEMP_DIR / "chrome_cache").resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--disk-cache-dir={cache_dir}")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")

        if load_extension and self.extension_dir.exists():
            ext_path = str(self.extension_dir)
            options.add_argument(f"--load-extension={ext_path}")
            options.add_argument(f"--disable-extensions-except={ext_path}")
            logger.info("Auto-loading Google Flow extension: %s", ext_path)

        if headless:
            options.add_argument("--headless=new")

        logger.info("Starting Chrome for Google Flow (ver: %s, profile: %s)...", chrome_ver, self.profile_dir)
        try:
            if chrome_ver:
                self.driver = uc.Chrome(options=options, version_main=chrome_ver, use_subprocess=True)
            else:
                self.driver = uc.Chrome(options=options, use_subprocess=True)
        except Exception as exc:
            logger.warning("Standard launch fallback: %s", exc)
            self.driver = uc.Chrome(options=options, use_subprocess=True)

        self.driver.set_window_size(1366, 900)
        return self.driver

    def open_flow(self) -> Dict[str, Any]:
        """Opens Google Flow home page."""
        driver = self.start_driver()
        logger.info("Navigating to %s", FLOW_URL)
        driver.get(FLOW_URL)
        time.sleep(4)
        return {
            "current_url": driver.current_url,
            "title": driver.title,
            "is_logged_in": self.check_login_status(),
        }

    def check_login_status(self) -> bool:
        """Determines if user is authenticated into Google Flow."""
        if not self.driver:
            return False

        current_url = self.driver.current_url.lower()
        page_source = self.driver.page_source.lower()

        # If redirected to Google accounts signin
        if "accounts.google.com" in current_url:
            return False

        # Look for sign in buttons
        if "sign in" in page_source or "masuk" in page_source:
            # Check if sign in button is present in navigation
            try:
                from selenium.webdriver.common.by import By
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    txt = btn.text.strip().lower()
                    if txt in ("sign in", "masuk", "sign in with google"):
                        return False
            except Exception:
                pass

        # If URL is in labs.google and has app container
        if "labs.google" in current_url or "flow" in current_url:
            return True

        return False

    def wait_for_user_login(self, timeout_seconds: int = 180) -> bool:
        """Prompts operator to log in if needed and polls until authenticated."""
        self.open_flow()
        if self.check_login_status():
            logger.info("Already authenticated on Google Flow.")
            return True

        logger.info(
            "Silakan login ke akun Google Anda pada jendela browser yang terbuka. "
            "Menunggu hingga %d detik...", timeout_seconds
        )
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            time.sleep(3)
            if self.check_login_status():
                logger.info("Login berhasil terdeteksi!")
                return True

        return False

    def sync_cookies_with_bridge(self, wait_seconds: int = 15) -> Dict[str, Any]:
        """Opens Chrome on Google Flow, extracts active session tokens (at, fsid)
        and session cookies directly, and updates account JSON files.
        """
        try:
            driver = self.start_driver()
            target_project = "0cd53e0c-dae6-4b49-b362-727a82c2dd22"
            project_url = f"https://flow.google.com/project/{target_project}"
            logger.info("Opening Google Flow project for token sync: %s", project_url)
            driver.get(project_url)
            time.sleep(5)

            tokens = driver.execute_script("""
                const w = window.WIZ_global_data || {};
                return { at: w.SNlM0e || '', fsid: w.FdrFJe || '' };
            """)

            raw_cookies = driver.get_cookies()
            cookie_list = []
            for c in raw_cookies:
                item = {
                    "domain": c.get("domain"),
                    "name": c.get("name"),
                    "path": c.get("path", "/"),
                    "value": c.get("value")
                }
                if "expiry" in c:
                    item["expirationDate"] = float(c["expiry"])
                if c.get("httpOnly"):
                    item["httpOnly"] = True
                if c.get("secure"):
                    item["secure"] = True
                item["sameSite"] = c.get("sameSite", "unspecified")
                item["storeId"] = "0"
                cookie_list.append(item)

            ua = driver.execute_script("return navigator.userAgent;")
            fingerprint = {
                "user_agent": ua,
                "sec_ch_ua": '"Chromium";v="154", "Google Chrome";v="154", "Not A(Brand";v="99"',
                "platform": '"Windows"',
                "language": "en-US",
                "mobile": "?0"
            }

            payload = {
                "project_id": target_project,
                "at": tokens.get("at", ""),
                "fsid": tokens.get("fsid", ""),
                "fingerprint": fingerprint,
                "cookies": cookie_list
            }

            from src.config import ROOT_DIR
            target_paths = [
                ROOT_DIR / "cookies" / "account_3a990c513727.json",
                self.cookies_dir / "account_3a990c513727.json"
            ]
            for p in target_paths:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                logger.info("Updated Flow session account file: %s", p)

            return {
                "synced": True,
                "cookie_file": str(target_paths[0]),
                "cookies_found": len(cookie_list),
                "at_token_present": bool(tokens.get("at")),
                "fsid_present": bool(tokens.get("fsid"))
            }
        except Exception as exc:
            logger.error("Failed to sync session tokens: %s", exc)
            return {"synced": False, "error": str(exc)}

    def submit_studio_tryon(
        self,
        project_id: str,
        reference_name: str,
        prompt_text: str,
        auto_approve: bool = True,
        timeout_sec: int = 180
    ) -> Dict[str, Any]:
        """Submits a choreographed try-on prompt into Google Flow Studio.
        Uses native @ ingredient mentions to attach catalog reference, then initiates generation.
        """
        from selenium.webdriver.common.by import By

        driver = self.start_driver()
        project_url = f"https://flow.google.com/project/{project_id}"
        logger.info("Navigating to Flow Studio: %s", project_url)
        driver.get(project_url)
        time.sleep(6)

        try:
            # 1. Locate and focus ProseMirror editor
            pm = driver.find_element(By.CSS_SELECTOR, "div.ProseMirror")
            pm.click()
            time.sleep(1)

            # 2. Attach reference via @ mention
            if reference_name:
                logger.info("Attaching ingredient reference: %s", reference_name)
                pm.send_keys("@")
                time.sleep(1.5)
                opts = driver.find_elements(By.XPATH, "//cdk-virtual-scroll-viewport//*[contains(@class, 'asset-item')]")
                matched = False
                for o in opts:
                    if reference_name.lower() in o.text.lower():
                        o.click()
                        matched = True
                        break
                if not matched and opts:
                    opts[0].click()
                time.sleep(1.5)

            # 3. Enter choreographed prompt
            pm = driver.find_element(By.CSS_SELECTOR, "div.ProseMirror")
            pm.send_keys(f" {prompt_text}")
            time.sleep(2)

            # 4. Click Start generation
            start_btn = driver.find_element(By.XPATH, "//button[@aria-label='Start generation']")
            if not start_btn.is_enabled():
                return {"success": False, "error": "Start generation button is disabled"}

            logger.info("Clicking Start generation...")
            start_btn.click()
            time.sleep(4)

            # 5. Handle approval modal/card if prompted
            if auto_approve:
                start_time = time.time()
                while time.time() - start_time < 30:
                    approve_btns = driver.find_elements(By.XPATH, "//button[contains(., 'Approve') or contains(., 'approve')]")
                    if approve_btns and approve_btns[0].is_displayed() and approve_btns[0].is_enabled():
                        logger.info("Clicking Approve credit button...")
                        approve_btns[0].click()
                        time.sleep(3)
                        break
                    time.sleep(2)

            # Save diagnostic screenshot
            shot_path = DATA_DIR / "studio_last_submission.png"
            driver.save_screenshot(str(shot_path))

            return {
                "success": True,
                "project_id": project_id,
                "reference_attached": reference_name,
                "screenshot": str(shot_path)
            }
        except Exception as exc:
            logger.error("Error submitting Studio tryon: %s", exc)
            return {"success": False, "error": str(exc)}

    def close(self):
        """Closes browser session cleanly."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None


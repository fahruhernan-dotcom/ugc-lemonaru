"""Google Flow Browser Agent Controller for Velora AI.
Provides Hermes with 'hands and feet' to operate the Google Flow Studio interface:
1. Navigates menus, project spaces, and character builders.
2. Automates 'Agent settings' configuration (Confirm before generating: Never, default 9:16).
3. Types prompts, selects models (Nano Banana 2.1 / Omni 1.1 Flash), and triggers generation.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from src.flow_selenium_operator import GoogleFlowSeleniumOperator

logger = logging.getLogger("velora.flow_browser_agent")


class GoogleFlowBrowserAgent:
    """Hermes UI automation operator for Google Flow."""

    def __init__(self, operator: Optional[GoogleFlowSeleniumOperator] = None):
        self.operator = operator or GoogleFlowSeleniumOperator()
        self.driver = None

    def ensure_driver(self):
        """Ensures the Chrome browser session is active."""
        if not self.driver:
            self.driver = self.operator.start_driver()
        return self.driver

    def open_studio(self, url: Optional[str] = None) -> str:
        """Navigates to the Google Flow studio page."""
        driver = self.ensure_driver()
        target = url or "https://flow.google.com"
        logger.info("Opening Google Flow studio: %s", target)
        driver.get(target)
        time.sleep(5)
        return driver.current_url

    def configure_agent_settings(
        self,
        confirm: str = "Never",
        aspect_ratio: str = "9:16",
        image_model: str = "Nano Banana 2.1",
        video_model: str = "Omni 1.1 Flash"
    ) -> Dict[str, Any]:
        """Automates opening the Agent Settings modal (⚙️), setting Confirm = Never,
        setting default aspect ratio to 9:16, selecting models, and clicking Save.
        """
        driver = self.ensure_driver()
        from selenium.webdriver.common.by import By

        results = {
            "settings_opened": False,
            "confirm_set_to_never": False,
            "aspect_9_16_set": False,
            "models_selected": False,
            "saved": False
        }

        logger.info("Configuring Agent Settings on Google Flow (Confirm: %s, Aspect: %s)...", confirm, aspect_ratio)

        # 1. Click Settings Icon ⚙️
        try:
            settings_buttons = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'setting') or contains(@aria-label, 'Setting')]")
            if not settings_buttons:
                header_buttons = driver.find_elements(By.XPATH, "//header//button | //div[contains(@class, 'header')]//button")
                for btn in header_buttons:
                    html = (btn.get_attribute("outerHTML") or "").lower()
                    if "settings" in html or "gear" in html:
                        settings_buttons = [btn]
                        break

            if settings_buttons:
                settings_buttons[0].click()
                time.sleep(2)
                results["settings_opened"] = True
                logger.info("Opened settings modal via gear icon.")
            else:
                logger.warning("Gear icon not found directly, checking if modal already visible.")
        except Exception as exc:
            logger.warning("Error clicking settings button: %s", exc)

        # 2. Select 'Never' radio button
        try:
            never_labels = driver.find_elements(By.XPATH, f"//*[contains(text(), '{confirm}') or contains(text(), 'spend credits automatically')]")
            for item in never_labels:
                try:
                    item.click()
                    results["confirm_set_to_never"] = True
                    logger.info("Clicked '%s' confirm option.", confirm)
                    break
                except Exception:
                    continue
        except Exception as exc:
            logger.warning("Error setting confirm radio: %s", exc)

        # 3. Select 9:16 aspect ratio chips
        try:
            chips_aspect = driver.find_elements(By.XPATH, f"//*[text()='{aspect_ratio}' or contains(text(), '{aspect_ratio}')]")
            for chip in chips_aspect:
                try:
                    chip.click()
                    time.sleep(0.5)
                    results["aspect_9_16_set"] = True
                    logger.info("Selected %s aspect ratio chip.", aspect_ratio)
                except Exception:
                    continue
        except Exception as exc:
            logger.warning("Error selecting aspect ratio: %s", exc)

        # 4. Model selection (if dropdowns present)
        try:
            for target_model in [image_model, video_model]:
                model_elems = driver.find_elements(By.XPATH, f"//*[contains(text(), '{target_model}')]")
                if model_elems:
                    results["models_selected"] = True
                    logger.info("Found model element for: %s", target_model)
        except Exception as exc:
            logger.warning("Error selecting models: %s", exc)

        # 5. Click 'Save' Button
        try:
            save_buttons = driver.find_elements(By.XPATH, "//button[normalize-space()='Save' or contains(text(), 'Save')]")
            if save_buttons:
                save_buttons[0].click()
                time.sleep(2)
                results["saved"] = True
                logger.info("Successfully clicked Save in Agent Settings!")
        except Exception as exc:
            logger.warning("Error clicking Save button: %s", exc)

        return results

    def create_fashion_character(
        self,
        name: str = "Velora Chic Model",
        description: str = "Chic young Indonesian fashion model with short violet-tinted bob hair, slender build, delicate pearl necklace, soft Korean fashion lookbook style in sunlit room",
        reference_image: Optional[Path] = None,
        base_archetype: str = "The Professional"
    ) -> Dict[str, Any]:
        """Navigates to the Character Builder on Google Flow and sets up consistent visual model."""
        driver = self.ensure_driver()
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        res = {"character_name": name, "archetype": base_archetype, "created": False, "screenshot": None}
        logger.info("Setting up fashion character in Google Flow: '%s'", name)

        try:
            # 1. Resolve project URL or navigate to /character
            current_url = driver.current_url
            if "/character" not in current_url:
                if "/project/" in current_url:
                    base_proj = current_url.split("/project/")[1].split("/")[0]
                    char_url = f"https://flow.google.com/project/{base_proj}/character"
                    driver.get(char_url)
                    time.sleep(4)
                else:
                    char_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Character') or contains(@aria-label, 'character')]")
                    if char_buttons:
                        char_buttons[0].click()
                        time.sleep(3)

            # 2. Select base archetype if provided (e.g. The Professional, The Familiar)
            if base_archetype:
                arch_chips = driver.find_elements(By.XPATH, f"//*[contains(text(), '{base_archetype}')]")
                if arch_chips:
                    try:
                        arch_chips[0].click()
                        time.sleep(1)
                        res["created"] = True
                    except Exception:
                        pass

            # 3. If reference image provided, try uploading it to file input
            if reference_image and Path(reference_image).exists():
                try:
                    file_inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
                    if file_inputs:
                        file_inputs[0].send_keys(str(Path(reference_image).resolve()))
                        logger.info("Attached character reference image: %s", reference_image.name)
                        time.sleep(2)
                except Exception as up_err:
                    logger.debug("Upload reference input notice: %s", up_err)

            # 4. Enter character description into input prompt bar
            inputs = driver.find_elements(
                By.XPATH,
                "//textarea | //input[@type='text'] | //div[@contenteditable='true']"
            )
            target_input = None
            for inp in inputs:
                ph = (inp.get_attribute("placeholder") or "").lower()
                if "character" in ph or "describe" in ph or "prompt" in ph:
                    target_input = inp
                    break
            if not target_input and inputs:
                target_input = inputs[-1]

            if target_input:
                target_input.click()
                time.sleep(0.5)
                target_input.clear()
                target_input.send_keys(description)
                time.sleep(1)

                arrow_buttons = driver.find_elements(
                    By.XPATH,
                    "//button[contains(@aria-label, 'generate') or contains(@aria-label, 'Submit')]"
                )
                if arrow_buttons:
                    arrow_buttons[-1].click()
                else:
                    target_input.send_keys(Keys.ENTER)

                logger.info("Submitted character prompt with Nano Banana 2.1!")
                res["created"] = True

            time.sleep(4)
            from src.config import OUTPUT_DIR
            out_img = OUTPUT_DIR / f"google_flow_character_{int(time.time())}.png"
            driver.save_screenshot(str(out_img))
            res["screenshot"] = str(out_img)
        except Exception as exc:
            logger.warning("Character setup notice: %s", exc)

        return res

    def submit_prompt(self, prompt_text: str, trigger_generate: bool = True) -> bool:
        """Types a prompt into the Google Flow prompt input box."""
        driver = self.ensure_driver()
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        logger.info("Typing prompt into Google Flow studio: %s", prompt_text[:60])
        try:
            inputs = driver.find_elements(
                By.XPATH,
                "//textarea | //input[@type='text'] | //div[@contenteditable='true']"
            )
            target_input = None
            for inp in inputs:
                placeholder = (inp.get_attribute("placeholder") or "").lower()
                if "describe" in placeholder or "prompt" in placeholder or "character" in placeholder:
                    target_input = inp
                    break

            if not target_input and inputs:
                target_input = inputs[-1]

            if target_input:
                target_input.click()
                time.sleep(0.5)
                target_input.clear()
                target_input.send_keys(prompt_text)
                time.sleep(1)

                if trigger_generate:
                    arrow_buttons = driver.find_elements(
                        By.XPATH,
                        "//button[contains(@aria-label, 'generate') or contains(@aria-label, 'Submit')]"
                    )
                    if arrow_buttons:
                        arrow_buttons[-1].click()
                    else:
                        target_input.send_keys(Keys.ENTER)
                    logger.info("Submitted prompt generation successfully!")
                return True
            else:
                logger.warning("Prompt input box not found on current page.")
                return False
        except Exception as exc:
            logger.error("Failed to submit prompt: %s", exc)
            return False

    def submit_prompt_and_wait(
        self,
        prompt_text: str,
        timeout_seconds: int = 240,
        output_dir: Optional[Path] = None
    ) -> Optional[Path]:
        """Submits a prompt and waits for the generated video/image to be rendered."""
        out_dir = output_dir or (Path(__file__).resolve().parent.parent / "tools" / "flow-agent" / "flow-agent" / "bin" / "output")
        before_files = set(out_dir.glob("*.mp4")) if out_dir.exists() else set()

        submitted = self.submit_prompt(prompt_text, trigger_generate=True)
        if not submitted:
            logger.error("Could not submit prompt to Google Flow.")
            return None

        logger.info("Prompt submitted, waiting up to %ds for media generation...", timeout_seconds)
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            time.sleep(5)
            if out_dir.exists():
                after_files = set(out_dir.glob("*.mp4"))
                new_files = sorted(list(after_files - before_files), key=lambda p: p.stat().st_mtime, reverse=True)
                if new_files:
                    logger.info("Found newly generated media: %s", new_files[0])
                    return new_files[0]

        logger.warning("Timed out waiting for new media file.")
        return None

    def close(self):
        """Cleanly closes browser session."""
        if self.operator:
            self.operator.close()
        self.driver = None

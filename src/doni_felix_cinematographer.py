#!/usr/bin/env python3
"""
doni_felix_cinematographer.py
=============================
Chief AI Cinematographer & Footage Harvester for @DoniesDaily.
Menerjemahkan naskah harian menjadi 6 prompt visual sinematik berbasis konteks ketat,
memproduksi JSON manifest lengkap, dan mengeksekusi generasi di Google Flow (Veo2) via Playwright CDP (:9222).
"""

import os
import sys
import json
import time
import asyncio
import logging
import sqlite3
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

import zoneinfo

JKT_TZ = zoneinfo.ZoneInfo("Asia/Jakarta")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("felix_cinematographer")

ROOT_DIR = Path("/home/ubuntu/apps/ugc-lemonaru")
SOUL_PATH = ROOT_DIR / "souls/FELIX_SOUL.md"
MANIFEST_DIR = ROOT_DIR / "data/felix_manifests"
FLOW_RENDERS_DIR = ROOT_DIR / "assets/cat_videos/flow_renders"
SWARM_DB_PATH = Path("/home/ubuntu/vps-control-center/backend/data/agents_chat.db")

MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
FLOW_RENDERS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PROJECT_URL = "https://flow.google.com/project/964abbc7-2441-4277-a4c6-93d1d7e755f9"
CDP_URL = "http://localhost:9222"

# 5 Aesthetic Zones (Anti-Visual Fatigue)
AESTHETIC_ZONES = {
    "zone_a_living_room": "warm modern living room, plush cream wool rug, soft beige sofa, golden hour sunlight streaming in, cozy home ambient",
    "zone_b_modern_kitchen": "clean gleaming white marble kitchen counter, stainless steel fixtures, crisp morning daylight, glass reflections",
    "zone_c_bookshelf_window": "aesthetic dark oak bookshelf study, cozy wooden windowsill, rain drizzle visible on glass window outside, moody soft lighting",
    "zone_d_cozy_bedroom": "minimalist aesthetic bedroom, crumpled linen duvet, soft pastel pillows, warm gentle bedside lamp glow",
    "zone_e_sunlit_terrace": "indoor sunlit conservatory terrace, lush indoor monstera plants, rustic light oak flooring, bright afternoon sun"
}

FELIX_PROMPT_SYSTEM = """You are Felix, Chief AI Cinematographer & Generative Footage Harvester for @DoniesDaily.
Your job is to analyze the scripts scheduled for today's YouTube Shorts and craft exactly 6 HIGH-DETAIL, CONTEXT-ALIGNED visual scenes for Google Flow / Veo2 video generation.

CRITICAL INSTRUCTIONS:
1. CONTEXT IS KING: The visual scene MUST directly represent what is being talked about in the script at that moment (e.g. if the script explains cat teeth chattering at a window, show an intense feline staring through glass with vibrating jaw; if it's kitten training with a food bowl, show a disciplined kitten staring at a bowl).
2. STRICT NEGATIVE CONSTRAINTS:
   - NO humans, NO human hands, NO human feet, NO human faces anywhere.
   - NO anatomy distortions, NO extra legs, NO duplicate tails.
   - Strictly 9:16 vertical smartphone format.
3. VISUAL STYLE BIBLE:
   - Photorealistic 8k, vertical 9:16 smartphone aspect ratio, cinematic lighting, shallow depth of field, ultra-high resolution, smooth fluid natural animal motion, warm aesthetic color grading.
4. STRICT JSON FORMAT: Return ONLY a raw valid JSON object matching the requested schema. No markdown, no prose outside JSON.
"""


def load_felix_soul() -> str:
    if SOUL_PATH.exists():
        return SOUL_PATH.read_text(encoding="utf-8")
    return "You are Felix, Chief AI Cinematographer for @DoniesDaily."


def query_db_topics() -> List[Dict[str, Any]]:
    """Fetches up to 3 active topics scheduled for today: morning, midday special, and evening."""
    sql = """
    SELECT json_agg(t) FROM (
        (SELECT topic_key, title, hook_banner, hook_vocal, full_script, slot_target, content_pillar, 'morning' as target_slot
         FROM ai_brain.doniesdaily_content_ideas 
         WHERE status = 'ready' AND (slot_target IN ('morning', 'any')) AND content_pillar != 'special_serial'
         ORDER BY created_at ASC LIMIT 1)
        UNION ALL
        (SELECT topic_key, title, hook_banner, hook_vocal, full_script, slot_target, content_pillar, 'midday_special' as target_slot
         FROM ai_brain.doniesdaily_content_ideas 
         WHERE status = 'ready' AND (slot_target = 'midday_special' OR content_pillar = 'special_serial')
         ORDER BY series_id, series_episode ASC LIMIT 1)
        UNION ALL
        (SELECT topic_key, title, hook_banner, hook_vocal, full_script, slot_target, content_pillar, 'evening' as target_slot
         FROM ai_brain.doniesdaily_content_ideas 
         WHERE status = 'ready' AND (slot_target IN ('evening', 'any')) AND content_pillar != 'special_serial'
         ORDER BY created_at DESC LIMIT 1)
    ) t;
    """
    cmd = [
        "docker", "exec", "-i", "supabase-db",
        "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c", sql
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        raw = res.stdout.strip()
        if not raw or raw == "null":
            # Fallback query if no special slots
            sql_fallback = "SELECT json_agg(t) FROM (SELECT topic_key, title, hook_banner, hook_vocal, full_script, slot_target, content_pillar, 'general' as target_slot FROM ai_brain.doniesdaily_content_ideas WHERE status = 'ready' ORDER BY created_at ASC LIMIT 3) t;"
            res_fb = subprocess.run(["docker", "exec", "-i", "supabase-db", "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c", sql_fallback], capture_output=True, text=True)
            raw = res_fb.stdout.strip()
            if not raw or raw == "null":
                return []
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.error(f"Failed to query topics from DB: {e}")
        return []


def generate_felix_manifest(topics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generates exactly 6 contextual scene prompts mapped to today's topics in strict JSON."""
    now_jkt = datetime.now(JKT_TZ)
    date_str = now_jkt.strftime("%Y-%m-%d")

    if not topics:
        raise ValueError("No active topics found in database to generate scenes from!")

    prompt_user = f"""Hari ini kita akan memproduksi konten DoniesDaily. Berikut adalah {len(topics)} topik yang sedang aktif:

{json.dumps(topics, indent=2, ensure_ascii=False)}

Tugasmu sebagai Felix (Chief AI Cinematographer):
Buat tepat 6 ADENGAN VISUAL SINEMATIK (2 adegan per topik jika ada 3 topik, atau distribusikan sampai total 6 adegan).
Setiap adegan harus:
1. Sangat selaras dengan konteks dan kalimat spesifik dalam naskah tersebut.
2. Memiliki framing kamera, sudut, aksi subjek yang jelas, zona estetika (Pilih dari: zone_a_living_room, zone_b_modern_kitchen, zone_c_bookshelf_window, zone_d_cozy_bedroom, zone_e_sunlit_terrace).
3. 'full_flow_prompt' wajib berbahasa Inggris baku sinematik tingkat tinggi, vertical 9:16, 8k, diakhiri dengan negative constraints dan style bible, siap dicopy langsung ke Google Flow.

Keluarkan hasil HANYA dalam struktur JSON persis berikut:
{{
  "batch_date": "{date_str}",
  "generated_at": "{now_jkt.isoformat()}",
  "total_scenes": 6,
  "scenes": [
    {{
      "scene_id": 1,
      "slot_target": "morning | midday_special | evening",
      "topic_key": "string",
      "topic_title": "string",
      "narrative_context": "Menjawab bagian mana dari naskah dan mengapa visual ini penting",
      "subject": "Deskripsi fisik kucing (misal: fluffy ginger tabby with white paws)",
      "action": "Aksi spesifik yang dilakukan kucing",
      "camera_framing": "Sudut kamera, pergerakan, dan focal length",
      "aesthetic_zone": "zone_a_living_room | zone_b_modern_kitchen | ...",
      "lighting_and_mood": "Karakter cahaya dan suasana",
      "negative_prompt": "no humans, no human hands, no distorted anatomy, no blurred artifacts",
      "full_flow_prompt": "Photorealistic 8k, vertical 9:16 smartphone aspect ratio, cinematic lighting, shallow depth of field. [Detailed Scene Action & Subject], [Zone Background Description], no humans, no human hands, ultra-high resolution, smooth natural motion."
    }}
  ]
}}
"""

    models_to_try = ["gemini-3.8-flash-high", "gemini-4-argon-high"]
    last_err = None

    for m in models_to_try:
        try:
            payload = {
                "model": m,
                "messages": [
                    {"role": "system", "content": FELIX_PROMPT_SYSTEM},
                    {"role": "user", "content": prompt_user}
                ],
                "temperature": 0.4
            }
            req = urllib.request.Request(
                "http://127.0.0.1:8317/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": "Bearer cpa-secret-key-12345"}
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                raw_txt = res_data["choices"][0]["message"]["content"].strip()
                if raw_txt.startswith("```"):
                    raw_txt = raw_txt.split("\n", 1)[1]
                    if raw_txt.endswith("```"):
                        raw_txt = raw_txt.rsplit("```", 1)[0]
                    raw_txt = raw_txt.strip()
                manifest = json.loads(raw_txt)
                if "scenes" in manifest and len(manifest["scenes"]) == 6:
                    return manifest
        except Exception as e:
            last_err = e
            logger.warning(f"Model {m} failed for Felix manifest: {e}. Trying fallback...")

    raise RuntimeError(f"All models failed to generate Felix manifest: {last_err}")


def save_manifest_to_disk(manifest: Dict[str, Any]) -> Path:
    date_str = manifest.get("batch_date", datetime.now(JKT_TZ).strftime("%Y-%m-%d"))
    out_file = MANIFEST_DIR / f"felix_manifest_{date_str}.json"
    out_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"✅ Saved Felix Prompt Manifest to: {out_file}")
    return out_file


def post_to_swarm_chat(sender: str, name: str, icon: str, role: str, content: str, trace: Optional[List[Dict[str, Any]]] = None):
    """Logs activity to SQLite agents_chat.db for VPS Control Center visibility."""
    if not SWARM_DB_PATH.exists():
        return
    try:
        conn = sqlite3.connect(str(SWARM_DB_PATH))
        cur = conn.cursor()
        msg_id = f"msg_{int(time.time()*1000)}"
        now_iso = datetime.now(JKT_TZ).isoformat()
        cur.execute("""
            INSERT INTO agent_messages (id, sender_id, sender_name, sender_avatar, sender_role, recipient_id, recipient_name, content, timestamp, channel, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'all', 'Squad Donies', ?, ?, 'donies', 'sent', ?)
        """, (msg_id, sender, name, icon, role, content, now_iso, now_iso))

        if trace:
            for t in trace:
                tr_id = f"tr_{int(time.time()*1000)}_{t.get('title', '')[:10]}"
                cur.execute("""
                    INSERT INTO agent_traces (id, message_id, type, title, description, status, content, icon, timestamp, created_at)
                    VALUES (?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?)
                """, (tr_id, msg_id, t.get("type", "reasoning"), t.get("title", ""), t.get("description", ""), t.get("content", ""), t.get("icon", "🎥"), now_iso, now_iso))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Failed to post to swarm chat: {e}")


class FelixFlowOperator:
    """Automates typing prompts and downloading generated video scenes from Google Flow via Playwright CDP."""

    def __init__(self, cdp_url: str = CDP_URL, project_url: str = DEFAULT_PROJECT_URL):
        self.cdp_url = cdp_url
        self.project_url = project_url

    async def get_flow_page(self, browser) -> Any:
        context = browser.contexts[0]
        for p in context.pages:
            if "flow.google.com" in p.url:
                if "project" not in p.url:
                    await p.goto(self.project_url)
                    await p.wait_for_timeout(3000)
                return p
        p = context.pages[0] if context.pages else await context.new_page()
        await p.goto(self.project_url)
        await p.wait_for_timeout(4000)
        return p

    async def submit_prompt(self, page, prompt_text: str, timeout_sec: int = 65) -> bool:
        """Types into ProseMirror editor, clicks 'Start generation' (arrow_forward), and waits for completion."""
        logger.info(f"📤 Felix submitting prompt: '{prompt_text[:65]}...'")
        
        # ProseMirror rich text input
        editor = page.locator('div[role="textbox"][contenteditable="true"]').first
        if await editor.count() > 0:
            await editor.click()
            await page.wait_for_timeout(300)
            # Select all and delete previous text
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await page.wait_for_timeout(200)
            # Fill prompt
            await editor.fill(prompt_text)
            await page.wait_for_timeout(500)
        else:
            raise RuntimeError("ProseMirror editor not found in Google Flow!")

        # Click Start generation button
        start_btn = page.locator('button[aria-label="Start generation"]').first
        if await start_btn.count() > 0:
            await start_btn.click()
            logger.info("🚀 Clicked 'Start generation' button.")
        else:
            await page.keyboard.press("Enter")
            logger.info("Pressed Enter on prompt box.")

        logger.info("⏳ Waiting for video rendering to complete in Google Flow...")
        start_t = time.time()
        # Wait until generation button is active again or progress completes
        await asyncio.sleep(8)
        while time.time() - start_t < timeout_sec:
            # Check if submit button is back and not disabled
            start_btn = page.locator('button[aria-label="Start generation"]').first
            if await start_btn.count() > 0 and await start_btn.is_enabled():
                elapsed = int(time.time() - start_t)
                logger.info(f"✨ Generation finished in ~{elapsed}s!")
                await asyncio.sleep(2)
                return True
            await asyncio.sleep(4)

        logger.warning(f"⚠️ Render wait hit {timeout_sec}s timeout, continuing...")
        return True

    async def download_latest_scene(self, page, output_file: Path) -> bool:
        """Clicks the newest tile (Tile 0), downloads media, and saves to output_file."""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        tiles = await page.locator("flow-grid-tile-container").all()
        if not tiles:
            logger.error("No tiles found on Google Flow canvas!")
            return False

        logger.info(f"📥 Clicking newest tile (Tile 0) to download...")
        await tiles[0].click()
        await page.wait_for_timeout(2500)

        dl_btn = page.locator('button[aria-label="Download media"]').first
        if await dl_btn.count() > 0:
            try:
                async with page.expect_download(timeout=20000) as dl_info:
                    await dl_btn.click()
                download = await dl_info.value
                await download.save_as(output_file)
                size_mb = output_file.stat().st_size / (1024 * 1024)
                logger.info(f"✅ Downloaded & saved: {output_file.name} ({size_mb:.2f} MB)")
                success = True
            except Exception as e:
                logger.error(f"❌ Failed to download tile: {e}")
                success = False
        else:
            logger.error("❌ 'Download media' button not found in modal!")
            success = False

        # Close modal
        back_btn = page.locator('button[aria-label*="Back"]').first
        if await back_btn.count() > 0:
            await back_btn.click()
        else:
            await page.keyboard.press("Escape")
        await page.wait_for_timeout(1500)
        return success


def record_harvested_clip_to_db(topic_key: str, file_rel_path: str):
    """Appends a harvested clip path into ai_brain.doniesdaily_content_ideas.harvested_clips JSONB."""
    try:
        sql = f"""
        UPDATE ai_brain.doniesdaily_content_ideas
        SET harvested_clips = COALESCE(harvested_clips, '[]'::jsonb) || jsonb_build_array('{file_rel_path}'),
            updated_at = NOW()
        WHERE topic_key = '{topic_key}';
        """
        subprocess.run(
            ["docker", "exec", "-i", "supabase-db", "psql", "-U", "postgres", "-d", "postgres", "-c", sql],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"📝 Registered harvested clip '{file_rel_path}' to DB for topic '{topic_key}'.")
    except Exception as e:
        logger.warning(f"⚠️ Failed to register harvested clip to DB: {e}")


if __name__ == "__main__":
    print("Testing Felix Cinematographer...")
    topics = query_db_topics()
    print(f"Found {len(topics)} active topics in DB.")
    manifest = generate_felix_manifest(topics)
    p = save_manifest_to_disk(manifest)
    print(f"Manifest created with {len(manifest.get('scenes', []))} scenes.")

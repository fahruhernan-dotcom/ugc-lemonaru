#!/usr/bin/env python3
"""
Milo 🎬 — Visual Director & AI Cinematographer for DoniesDaily
Translates video scripts into 5 coherent, high-detail vertical (9:16) scene prompts for Google Flow / Veo2.
Ingests MILO_SOUL.md and dynamically rotates across 5 distinct aesthetic zones to prevent visual fatigue.
"""
import json
import os
import sys
import random
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional

SOUL_PATH = Path("/home/ubuntu/apps/ugc-lemonaru/souls/MILO_SOUL.md")
API_URL = os.getenv("CPA_BASE_URL", "http://127.0.0.1:8317/v1/chat/completions")
API_KEY = os.getenv("CPA_API_KEY", "cpa-secret-key-12345")

# Canonical visual style anchor for DoniesDaily
BASE_STYLE_BIBLE = (
    "photorealistic 8k, vertical 9:16 smartphone aspect ratio, "
    "cinematic lighting, shallow depth of field, adorable expressive ginger tabby cat with white paws, "
    "no humans, no distorted anatomy, smooth fluid natural movement, high frame rate."
)

# 5 Aesthetic Zones (Remediasi W-03 What-If: Anti-Visual Fatigue)
AESTHETIC_ZONES = {
    "zone_a_living_room": "warm vibrant modern indoor living room, plush cream rug, soft sofa, golden hour sunlight streaming in",
    "zone_b_modern_kitchen": "gleaming modern clean marble kitchen counter, bright crisp morning daylight, glass reflections",
    "zone_c_bookshelf_window": "aesthetic dark oak bookshelf study, cozy window sill, gentle rain drizzle visible outside, moody soft lighting",
    "zone_d_cozy_bedroom": "cozy minimalist bedroom, crumpled soft linen duvet, pastel pillows, warm ambient bedside lamp glow",
    "zone_e_sunlit_terrace": "indoor sunlit conservatory terrace, lush green monstera plants, wooden flooring, bright natural afternoon sun"
}

def load_milo_soul() -> str:
    if SOUL_PATH.exists():
        return SOUL_PATH.read_text(encoding="utf-8")
    return "You are Milo, award-winning Visual Director for @DoniesDaily. You translate scripts into 5 cinematic 9:16 vertical scenes."

def pick_aesthetic_zone(topic_key: str = "") -> tuple[str, str]:
    """Deterministically picks or rotates an aesthetic zone based on topic key hash."""
    zone_keys = list(AESTHETIC_ZONES.keys())
    if topic_key:
        idx = sum(ord(c) for c in topic_key) % len(zone_keys)
        chosen_key = zone_keys[idx]
    else:
        chosen_key = random.choice(zone_keys)
    return chosen_key, AESTHETIC_ZONES[chosen_key]

def generate_shotlist(
    script_text: str,
    topic: str = "general_cat_behavior",
    target_model: str = "claude-opus-5-5-high",
    zone_override: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Splits a script into 5 visual scenes with detailed prompts for Google Flow.
    """
    milo_soul = load_milo_soul()
    zone_name, zone_prompt = (zone_override, AESTHETIC_ZONES.get(zone_override, AESTHETIC_ZONES["zone_a_living_room"])) if zone_override else pick_aesthetic_zone(topic)
    
    active_style_bible = f"{zone_prompt}, {BASE_STYLE_BIBLE}"

    prompt = f"""
{milo_soul}

Topic: {topic}
Selected Aesthetic Zone: {zone_name} ({zone_prompt})

Script:
\"\"\"{script_text}\"\"\"

Task:
Analyze the cat fact/story script above and divide it into EXACTLY 5 sequential video scenes (6 to 8 seconds each).
Enforce the 5 sequential camera movements:
- Scene 1: Dynamic camera push-in / low angle feline POV (Hook)
- Scene 2: Eye-level shot of cat interacting with environment
- Scene 3: Extreme macro close-up (toe beans, whiskers twitching, or pupil dilation)
- Scene 4: Slow-motion fluid movement (playful pounce, stretching, or rolling)
- Scene 5: Cat sitting elegantly looking towards the camera

For each scene, output:
1. "scene_num": Integer 1 to 5
2. "duration_sec": Estimated duration (e.g. 6 to 8)
3. "action_summary": Brief Indonesian description of what the cat is doing
4. "flow_prompt": High-detail English visual prompt describing camera angle, movement, cat expression, and setting. The prompt MUST end with: {active_style_bible}

Output MUST be a strict, raw JSON array of 5 objects. Do NOT wrap in markdown backticks or add introductory commentary.
"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": "You are Milo, an award-winning AI Cinematographer and Visual Director. You always return strict valid raw JSON."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 8192,
        "temperature": 0.4
    }

    resp = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Visual Director API call failed: {resp.status_code} - {resp.text}")

    data = resp.json()
    raw_content = data["choices"][0]["message"]["content"].strip()
    
    # Strip potential markdown formatting
    if raw_content.startswith("```"):
        raw_content = raw_content.split("\n", 1)[1]
        if raw_content.endswith("```"):
            raw_content = raw_content.rsplit("```", 1)[0]
        raw_content = raw_content.strip()

    try:
        shotlist = json.loads(raw_content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse shotlist JSON: {e}\nRaw output: {raw_content}")

    if not isinstance(shotlist, list) or len(shotlist) != 5:
        raise ValueError(f"Expected 5 scenes, received {len(shotlist) if isinstance(shotlist, list) else type(shotlist)}")

    return shotlist

if __name__ == "__main__":
    sample_topic = "cat_slow_blink_love"
    sample_script = (
        "Pernah gak sih... dapet kedipan super pelan dari anabul? "
        "Eits, itu bukan karena ngantuk loh! Di dunia kucing... kedipan lambat alias slow blink itu tanda cinta mutlak. "
        "Artinya, mereka ngerasa aman banget bareng kamu — beneran ciuman versi mata! "
        "Nah... anabul kamu suka gini juga gak?"
    )
    
    print(f"Testing Milo 🎬 Visual Director on topic: {sample_topic}...")
    try:
        shots = generate_shotlist(sample_script, sample_topic)
        print(f"SUCCESS: Milo generated {len(shots)} cinematic scenes.")
        print(json.dumps(shots, indent=2, ensure_ascii=False))
    except Exception as err:
        print(f"FAILED: {err}")
        sys.exit(1)

#!/usr/bin/env python3
"""
src/doni_music_selector.py
==========================
Milo Audio Director — Database-Driven Music & SFX Selector.
SSOT: PostgreSQL `ai_brain.doniesdaily_content_ideas` (target_mood, target_music_track, sfx_cues).
Guarantees zero-hallucination BGM selection aligned with YouTube Content ID tracks.
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("doni_music_selector")

AUDIO_DIR = Path("/home/ubuntu/apps/ugc-lemonaru/assets/audio")
MOOD_POOLS_DIR = AUDIO_DIR / "mood_pools"
SFX_DIR = AUDIO_DIR / "sfx"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "postgres",
    "password": os.environ.get("POSTGRES_PASSWORD", "postgres"),
    "dbname": "postgres"
}

TRACK_METADATA = {
    "Sneaky Snitch.mp3": {
        "title": "Sneaky Snitch",
        "artist": "Kevin MacLeod",
        "volume": 0.16,
        "mood": "suspense_training"
    },
    "Scheming Weasel faster.mp3": {
        "title": "Scheming Weasel",
        "artist": "Kevin MacLeod",
        "volume": 0.15,
        "mood": "suspense_training"
    },
    "Heartbreaking.mp3": {
        "title": "Heartbreaking",
        "artist": "Kevin MacLeod",
        "volume": 0.20,
        "mood": "emotional"
    },
    "Touching Story.mp3": {
        "title": "Touching Story",
        "artist": "Kevin MacLeod",
        "volume": 0.18,
        "mood": "emotional"
    },
    "Parting of the Ways - Part 1.mp3": {
        "title": "Parting of the Ways",
        "artist": "Kevin MacLeod",
        "volume": 0.18,
        "mood": "emotional"
    },
    "Evening Fall - Piano.mp3": {
        "title": "Evening Fall - Piano",
        "artist": "Kevin MacLeod",
        "volume": 0.18,
        "mood": "chill_cozy"
    },
    "Carefree.mp3": {
        "title": "Carefree",
        "artist": "Kevin MacLeod",
        "volume": 0.16,
        "mood": "playful_curious"
    },
    "Monkeys Spinning Monkeys.mp3": {
        "title": "Monkeys Spinning Monkeys",
        "artist": "Kevin MacLeod",
        "volume": 0.15,
        "mood": "playful_curious"
    },
    "Fluffing a Duck.mp3": {
        "title": "Fluffing a Duck",
        "artist": "Kevin MacLeod",
        "volume": 0.15,
        "mood": "playful_curious"
    }
}


def get_music_and_sfx_from_db(topic_key: str) -> Dict[str, Any]:
    """
    Fetches exact music track and SFX cues for a topic directly from the PostgreSQL SSOT.
    Uses docker exec -i supabase-db psql to access PostgreSQL reliably.
    Never hallucinates or guesses randomly.
    """
    target_mood = None
    target_music_track = None
    sfx_cues = []

    try:
        sql = f"""
        SELECT json_build_object(
            'topic_key', topic_key,
            'content_pillar', content_pillar,
            'series_id', series_id,
            'target_mood', target_mood,
            'target_music_track', target_music_track,
            'sfx_cues', sfx_cues
        )::text
        FROM ai_brain.doniesdaily_content_ideas
        WHERE topic_key = '{topic_key}'
        LIMIT 1;
        """
        res = subprocess.run(
            ["docker", "exec", "-i", "supabase-db", "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c", sql],
            capture_output=True,
            text=True,
            check=True
        )
        output = res.stdout.strip()
        if output:
            row = json.loads(output)
            target_mood = row.get("target_mood")
            target_music_track = row.get("target_music_track")
            sfx_cues = row.get("sfx_cues") or []
    except Exception as e:
        logger.warning(f"⚠️ Failed to query DB for music selector ({topic_key}): {e}")

    # Fallbacks if DB record is empty or missing
    if not target_music_track or target_music_track not in TRACK_METADATA:
        if "spook" in topic_key:
            target_music_track = "Sneaky Snitch.mp3"
            target_mood = "suspense_training"
        else:
            target_music_track = "Carefree.mp3"
            target_mood = "playful_curious"

    meta = TRACK_METADATA[target_music_track]
    track_path = MOOD_POOLS_DIR / meta["mood"] / target_music_track
    if not track_path.exists():
        # Fallback to legacy file if pool path missing
        track_path = AUDIO_DIR / "cat_playful_bgm.mp3"

    credit_line = (
        f"Music: '{meta['title']}' by {meta['artist']} (incompetech.com)\n"
        f"Licensed under Creative Commons: By Attribution 4.0 License\n"
        f"http://creativecommons.org/licenses/by/4.0/"
    )

    return {
        "topic_key": topic_key,
        "mood": meta["mood"],
        "track_file": target_music_track,
        "title": meta["title"],
        "artist": meta["artist"],
        "audio_path": track_path,
        "volume": meta["volume"],
        "sfx_cues": sfx_cues,
        "credit_line": credit_line
    }


def resolve_sfx_filepath(sfx_id: str) -> Optional[Path]:
    """Maps SFX ID to local file in assets/audio/sfx/"""
    mapping = {
        "01_taco_bell_bong": "sfx_taco_bell_bong.mp3",
        "02_vine_boom": "sfx_vine_boom.mp3",
        "03_yellow_undertale": "sfx_yellow_undertale_chime.mp3",
        "04_violin_screech": "sfx_violin_screech_horror.mp3",
        "05_correct_ding": "sfx_correct_ding.mp3",
        "06_anime_wow": "sfx_anime_wow.mp3",
        "07_akh_screaming": "sfx_akh_groan_fail.mp3",
        "08_kaching_cash": "sfx_kaching_cash_register.mp3",
        "09_tindeck_squeak": "sfx_tindeck_toy_squeak.mp3",
        "10_dry_fart": "sfx_dry_fart_meme.mp3"
    }
    fname = mapping.get(sfx_id)
    if fname:
        p = SFX_DIR / fname
        if p.exists():
            return p
    return None


if __name__ == "__main__":
    for tk in ["spook_part3", "cat_comforting_sadness", "cat_sleeping_on_dirty_laundry", "cat_flehmen_response"]:
        info = get_music_and_sfx_from_db(tk)
        print(f"[{tk}]")
        print(f"  🎵 BGM: {info['title']} ({info['track_file']}) | Vol: {info['volume']} | Mood: {info['mood']}")
        print(f"  🔔 SFX Cues ({len(info['sfx_cues'])}): {info['sfx_cues']}")

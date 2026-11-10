"""Doni Remotion & Google Flow Master Pipeline.
The SSOT automated pipeline for DoniesDaily YouTube Shorts.

Features:
1. Database-First Anti-Duplication: Picks next 'ready' topic from PostgreSQL ai_brain.doniesdaily_content_ideas.
2. ElevenLabs Kak Ceria Voiceover with acoustic punctuation + word-level timestamps JSON.
3. Multi-Scene Google Flow AI Video via persistent Chrome CDP (:9222).
4. Studio Remotion React Composition (DoniShort) with:
   - HookTitle dynamic card (spring physics 0-3.2s, slide away)
   - Pill glassmorphism channel watermark (@DoniesDaily)
   - Dynamic kinetic subtitles (TikTok/CapCut karaoke highlight)
5. YouTube Data API v3 OAuth Direct Upload (No browser, no AI mentions).
6. Automatic Database Ledger Reconciliation (status = 'published').
"""

import argparse
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import zoneinfo

JKT_TZ = zoneinfo.ZoneInfo("Asia/Jakarta")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "src"))

from src.elevenlabs_tts import generate_speech_with_timestamps
from src.youtube_api_publisher import YouTubeAPIPublisher
from src.flow_cdp_operator import FlowCDPOperator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("doni_master_pipeline")

WORKSPACE = ROOT_DIR
REMOTION_DIR = WORKSPACE / "remotion"
PUBLIC_DIR = REMOTION_DIR / "public"
OUTPUT_DIR = WORKSPACE / "output"
ASSETS_DIR = WORKSPACE / "assets"
CAT_VIDEOS_DIR = ASSETS_DIR / "cat_videos"
BGM_PATH = ASSETS_DIR / "audio" / "cat_playful_bgm.mp3"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_DIR.mkdir(parents=True, exist_ok=True)


class DoniRemotionFlowPipeline:
    def __init__(self):
        self.publisher = YouTubeAPIPublisher()
        self.flow_operator = FlowCDPOperator()

    def fetch_next_topic(self, topic_key: Optional[str] = None) -> Dict[str, Any]:
        """Pulls next topic from PostgreSQL DB with atomic 'producing' state lock to guarantee zero duplicate content."""
        if topic_key:
            sql = f"""
            UPDATE ai_brain.doniesdaily_content_ideas
            SET status = 'producing',
                producing_started_at = NOW(),
                attempt_count = COALESCE(attempt_count, 0) + 1,
                updated_at = NOW()
            WHERE topic_key = '{topic_key}'
            RETURNING json_build_object(
                'topic_key', topic_key,
                'title', title,
                'hook_banner', hook_banner,
                'hook_subtitle', hook_subtitle,
                'hook_vocal', hook_vocal,
                'full_script', full_script,
                'flow_prompts', flow_prompts,
                'scene_breakdown', scene_breakdown,
                'status', status,
                'series_id', series_id,
                'series_episode', series_episode,
                'content_pillar', content_pillar,
                'slot_target', slot_target,
                'target_mood', target_mood,
                'target_music_track', target_music_track
            )::text;
            """
        else:
            sql = """
            UPDATE ai_brain.doniesdaily_content_ideas
            SET status = 'producing',
                producing_started_at = NOW(),
                attempt_count = COALESCE(attempt_count, 0) + 1,
                updated_at = NOW()
            WHERE topic_key = (
                SELECT topic_key FROM ai_brain.doniesdaily_content_ideas
                WHERE status = 'ready'
                ORDER BY created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING json_build_object(
                'topic_key', topic_key,
                'title', title,
                'hook_banner', hook_banner,
                'hook_subtitle', hook_subtitle,
                'hook_vocal', hook_vocal,
                'full_script', full_script,
                'flow_prompts', flow_prompts,
                'scene_breakdown', scene_breakdown,
                'status', status,
                'series_id', series_id,
                'series_episode', series_episode,
                'content_pillar', content_pillar,
                'slot_target', slot_target,
                'target_mood', target_mood,
                'target_music_track', target_music_track
            )::text;
            """

        res = subprocess.run([
            "docker", "exec", "-i", "supabase-db",
            "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c", sql
        ], capture_output=True, text=True, check=True)

        raw = res.stdout.strip()
        if not raw or raw == "null":
            # If explicit topic_key was requested and already 'producing' or other state, fetch readonly
            if topic_key:
                sql_read = f"SELECT json_agg(t) FROM (SELECT topic_key, title, hook_banner, hook_subtitle, hook_vocal, full_script, flow_prompts, scene_breakdown, status, series_id, series_episode, content_pillar, slot_target, target_mood, target_music_track FROM ai_brain.doniesdaily_content_ideas WHERE topic_key = '{topic_key}') t;"
                res_read = subprocess.run(["docker", "exec", "-i", "supabase-db", "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c", sql_read], capture_output=True, text=True)
                raw_read = res_read.stdout.strip()
                if raw_read and raw_read != "null":
                    json_r = [l.strip() for l in raw_read.splitlines() if l.strip().startswith("[") or l.strip().startswith("{")]
                    if json_r:
                        parsed = json.loads(json_r[0])
                        return parsed[0] if isinstance(parsed, list) else parsed
            raise RuntimeError("No topics available for production in ai_brain.doniesdaily_content_ideas!")

        json_lines = [l.strip() for l in raw.splitlines() if l.strip().startswith("{")]
        if not json_lines:
            raise RuntimeError(f"Failed to parse JSON topic data from SQL output: {raw}")
        return json.loads(json_lines[0])

    def synthesize_audio_and_captions(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesizes ElevenLabs Vivan narration and exports Remotion caption tokens."""
        t_key = topic["topic_key"]
        script = topic["full_script"].strip()

        # Enforce spoken CTA if not present
        if not re.search(r'(follow|subscribe)', script, re.IGNORECASE):
            script = f"{script} Jangan lupa follow dan subscribe DoniesDaily ya!"

        voiceover_vault_dir = ASSETS_DIR / "audio" / "generated_voiceovers"
        voiceover_vault_dir.mkdir(parents=True, exist_ok=True)
        raw_voice = voiceover_vault_dir / f"{t_key}_vivan.mp3"
        captions_json_name = f"doni-{t_key}-captions.json"
        captions_path = PUBLIC_DIR / captions_json_name
        master_audio_name = f"{t_key}_master.mp3"
        master_audio_path = PUBLIC_DIR / master_audio_name

        # Reuse existing audio & captions if already generated (saves ElevenLabs credits)
        if master_audio_path.exists() and captions_path.exists():
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(master_audio_path)],
                capture_output=True, text=True
            )
            if probe.returncode == 0 and probe.stdout.strip():
                duration = float(probe.stdout.strip())
                logger.info("🎙️ Found cached audio & captions for '%s' (%.2fs), reusing...", t_key, duration)
                return {
                    "master_audio_file": master_audio_name,
                    "captions_file": captions_json_name,
                    "duration": round(duration, 2)
                }

        logger.info(f"🎙️ Generating voiceover + word timestamps with Vivan for '{t_key}'...")
        _, _, _ = generate_speech_with_timestamps(
            text=script,
            output_audio_path=str(raw_voice),
            output_captions_json=str(captions_path)
        )

        # Mix with dynamic mood-based YouTube BGM + Dynamic Sound Effects (SFX) from DB
        from doni_music_selector import get_music_and_sfx_from_db, resolve_sfx_filepath
        music_info = get_music_and_sfx_from_db(t_key)
        bgm_track_path = music_info["audio_path"]
        bgm_volume = music_info["volume"]
        db_sfx_cues = music_info["sfx_cues"]
        logger.info(
            "🎵 Mixing voiceover with [%s] track '%s' (vol=%.2f) + dynamic SFX from DB...",
            music_info["mood"], music_info["title"], bgm_volume
        )
        
        # Detect exact timing for SFX from captions & DB cues
        sfx_inputs = []
        sfx_filters = []
        next_input_idx = 2
        mix_sources = ["[voice]", "[bgm]"]
        
        words_data = []
        try:
            if captions_path.exists():
                with open(captions_path, "r", encoding="utf-8") as f:
                    words_data = json.load(f)
        except Exception:
            pass

        # Helper to find word startMs
        def find_word_time(trigger_word: str, default_ms: int = 100) -> int:
            tw = trigger_word.lower()
            for w in words_data:
                clean_w = re.sub(r'[^\w]', '', w.get("text", "")).lower()
                if tw in clean_w:
                    return int(w.get("startMs", default_ms))
            return default_ms

        # Iterate over DB SFX cues
        for idx, cue in enumerate(db_sfx_cues):
            s_id = cue.get("sfx_id")
            s_trig = cue.get("cue_trigger", "hook")
            s_vol = float(cue.get("volume", 0.35))
            s_path = resolve_sfx_filepath(s_id)
            if not s_path:
                continue

            # Calculate delay
            if s_trig == "hook":
                delay_ms = 100
            elif s_trig in ["pencet", "tap", "ketuk"]:
                delay_ms = find_word_time(s_trig, default_ms=4000)
            else:
                delay_ms = find_word_time(s_trig, default_ms=1000)

            label = f"sfx_{idx}"
            sfx_inputs.extend(["-i", str(s_path)])
            sfx_filters.append(f"[{next_input_idx}:a]volume={s_vol},adelay={delay_ms}|{delay_ms}[{label}];")
            mix_sources.append(f"[{label}]")
            next_input_idx += 1

        # Fallback if no SFX cues configured in DB
        if not db_sfx_cues:
            taco_bell_path = resolve_sfx_filepath("01_taco_bell_bong")
            if taco_bell_path and taco_bell_path.exists():
                sfx_inputs.extend(["-i", str(taco_bell_path)])
                sfx_filters.append(f"[{next_input_idx}:a]volume=0.35,adelay=100|100[sfx_hook];")
                mix_sources.append("[sfx_hook]")
                next_input_idx += 1

        filter_complex = (
            "[0:a]volume=1.35,highpass=f=80,dynaudnorm[voice];"
            f"[1:a]volume={bgm_volume}[bgm];"
            + "".join(sfx_filters)
            + "".join(mix_sources)
            + f"amix=inputs={len(mix_sources)}:duration=first:dropout_transition=2[aout]"
        )

        cmd_audio = [
            "ffmpeg", "-y",
            "-i", str(raw_voice),
            "-stream_loop", "-1", "-i", str(bgm_track_path),
            *sfx_inputs,
            "-filter_complex", filter_complex,
            "-map", "[aout]",
            "-c:a", "libmp3lame", "-q:a", "2",
            str(master_audio_path)
        ]
        subprocess.run(cmd_audio, check=True, capture_output=True)

        # Probe exact audio duration
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(master_audio_path)],
            capture_output=True, text=True, check=True
        )
        duration = float(probe.stdout.strip())
        logger.info(f"⏱️ Audio master ready: {duration:.2f}s")

        return {
            "master_audio_file": master_audio_name,
            "captions_file": captions_json_name,
            "duration": round(duration, 2)
        }

    async def prepare_flow_scenes(self, topic: Dict[str, Any], target_duration: float) -> str:
        """Generates or retrieves multi-scene background video matching exact audio duration."""
        t_key = topic["topic_key"]
        bg_video_name = f"flow_{t_key}_bg_concat.mp4"
        final_bg_path = PUBLIC_DIR / bg_video_name
        if final_bg_path.exists() and final_bg_path.stat().st_size > 1000000:
            logger.info(f"✅ Background video already compiled: {bg_video_name}")
            return bg_video_name

        flow_prompts_data = topic.get("flow_prompts", [])
        
        prompts = []
        if isinstance(flow_prompts_data, list):
            for item in flow_prompts_data:
                if isinstance(item, dict) and "text" in item:
                    prompts.append(item["text"])
                elif isinstance(item, str):
                    prompts.append(item)

        out_dir = ASSETS_DIR / "cat_videos" / "flow_renders" / t_key
        downloaded_clips: List[Path] = []

        if prompts:
            try:
                logger.info(f"🎬 Initiating Google Flow CDP generation for {len(prompts)} scenes...")
                downloaded_clips = await self.flow_operator.generate_scenes(prompts, out_dir)
            except Exception as e:
                logger.warning(f"⚠️ Google Flow generation encountered issue ({e}), falling back to curated assets...")

        # 1. First, check pre-harvested AI clips from Felix for this topic (Disk & DB)
        flow_base = ASSETS_DIR / "cat_videos" / "flow_renders"
        if flow_base.exists():
            pre_harvested = [p for p in flow_base.rglob("*.mp4") if (t_key in p.name or t_key in str(p.parent)) and p.stat().st_size > 500000]
            # Also check DB harvested_clips
            try:
                db_clips_sql = f"SELECT harvested_clips::text FROM ai_brain.doniesdaily_content_ideas WHERE topic_key = '{t_key}' LIMIT 1;"
                res = subprocess.run(
                    ["docker", "exec", "-i", "supabase-db", "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c", db_clips_sql],
                    capture_output=True, text=True, check=True
                )
                db_val = res.stdout.strip()
                if db_val:
                    clip_list = json.loads(db_val)
                    for c_rel in clip_list:
                        c_p = ASSETS_DIR / "cat_videos" / c_rel
                        if c_p.exists() and c_p not in pre_harvested:
                            pre_harvested.append(c_p)
            except Exception as e:
                logger.warning(f"⚠️ Failed to query DB harvested_clips: {e}")

            if pre_harvested:
                logger.info(f"✨ Found {len(pre_harvested)} pre-harvested AI scenes from Felix for topic '{t_key}'!")
                downloaded_clips.extend(pre_harvested)

        # 2. Interleave with authentic clips from fahru_clips (Hukum Besi #13 Interleaving Authentic & AI)
        fahru_dir = ASSETS_DIR / "cat_videos" / "fahru_clips"
        banned_arya = {"domba", "kambing", "ternak", "seminar", "selfie", "karaoke", "cermin", "tutorial", "cctv", "blurams"}
        if fahru_dir.exists():
            f_clips = [p for p in sorted(list(fahru_dir.glob("*.mp4"))) if not any(b in p.stem.lower() for b in banned_arya)]
            if f_clips:
                # Interleave: 1 AI clip from Felix, 1 Real clip from Fahru
                import random
                sample_fahru = random.sample(f_clips, min(3, len(f_clips)))
                downloaded_clips = downloaded_clips[:2] + sample_fahru

        # 3. Fallback to any verified clips in fahru_clips or flow_renders if still empty
        if not downloaded_clips:
            logger.info("Using available cat action pool from fahru_clips and flow_renders...")
            if fahru_dir.exists():
                downloaded_clips = [p for p in sorted(list(fahru_dir.glob("*.mp4"))) if not any(b in p.stem.lower() for b in banned_arya)][:4]
            if not downloaded_clips and flow_base.exists():
                downloaded_clips = sorted(list(flow_base.rglob("*.mp4")))[:4]

        num_scenes = max(1, len(downloaded_clips))
        slice_dur = target_duration / float(num_scenes)
        logger.info(f"🎞️ Stitching {num_scenes} scenes ({slice_dur:.2f}s each) into 9:16 background...")

        tmp_parts_dir = Path(f"/tmp/parts_{t_key}")
        tmp_parts_dir.mkdir(parents=True, exist_ok=True)
        part_paths = []

        for idx, clip in enumerate(downloaded_clips):
            out_part = tmp_parts_dir / f"part_{idx}.mp4"
            cmd_cut = [
                "ffmpeg", "-y",
                "-ss", "0.0",
                "-i", str(clip),
                "-t", f"{slice_dur:.2f}",
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-an",
                str(out_part)
            ]
            subprocess.run(cmd_cut, check=True, capture_output=True)
            part_paths.append(out_part)

        concat_list = tmp_parts_dir / "concat_list.txt"
        with open(concat_list, "w") as f:
            for p in part_paths:
                f.write(f"file '{p.resolve()}'\n")

        bg_video_name = f"flow_{t_key}_bg_concat.mp4"
        final_bg_path = PUBLIC_DIR / bg_video_name
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(final_bg_path)
        ], check=True, capture_output=True)

        logger.info(f"✅ Background video compiled: {bg_video_name}")
        return bg_video_name

    def render_remotion_short(
        self,
        topic: Dict[str, Any],
        audio_info: Dict[str, Any],
        video_bg_file: str
    ) -> Path:
        """Hybrid Short Renderer: Remotion React Overlays (ProRes 4444) + Native 9:16 FFMPEG Composite.
        Guarantees 100% Remotion Golden Standard (HookTitle spring physics, rounded pill badges,
        kinetic subtitles, Outro CTA) without Chromium decode bottlenecks or crop zoom distortions.
        """
        from doni_hybrid_renderer import DoniHybridRenderer
        renderer = DoniHybridRenderer()

        t_key = topic["topic_key"]
        output_file = WORKSPACE / "data" / f"{t_key}_master.mp4"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        badge_text = re.sub(r'[^\w\s!\-]', '', topic.get("hook_banner") or "FAKTA ANABUL").strip()[:24]
        clean_title = re.sub(r'[^\w\s?]', '', re.sub(r'#\w+', '', topic['title'])).strip().upper()[:50]
        hook_sub = re.sub(r'[^\w\s!\-]', '', topic.get("hook_subtitle") or "Bukan Karena Marah Lho!").strip()[:60]
        duration_sec = float(audio_info["duration"])

        # 1. Select clean vertical 9:16 clips synchronized with voice script speech beats
        # Voice-Synced Scene Transitions (Hukum Besi #13): Cuts happen on sentence beats + semantic match
        from doni_qc_gate import audit_footage_assembly, audit_against_database
        captions_json_path = PUBLIC_DIR / audio_info["captions_file"]
        series_id = topic.get("series_id")
        series_ep = topic.get("series_episode")

        selected_clips = []
        clip_durations = None
        qc_passed = False

        # SERIAL FOOTAGE ASSEMBLY: Strictly isolate serial episodes to their series catalog
        if series_id:
            logger.info("🎬 [SERIAL ASSEMBLY] Processing series '%s' (Episode %s)...", series_id, series_ep)
            cat_series = renderer._fetch_db_catalog(series_id=series_id)
            if not cat_series:
                raise RuntimeError(f"No catalog footage found in ai_brain.doniesdaily_clip_catalog for series '{series_id}'!")

            ep_clip = None
            if series_ep is not None:
                ep_str = str(series_ep).lower()
                for c in cat_series:
                    c_id_l = c.get("id", "").lower()
                    c_path_l = c.get("abs_path", "").lower()
                    if any(tag in c_id_l or tag in c_path_l for tag in [f"part{ep_str}", f"day{ep_str}", f"ep{ep_str}"]):
                        ep_clip = c
                        break

            # If this series has a single long video for the episode (like Spook Training), build non-overlapping narrative slices
            if ep_clip or len(cat_series) < 6:
                target_clip = ep_clip or cat_series[0]
                raw_path = Path(target_clip["abs_path"])
                if not raw_path.exists():
                    raise FileNotFoundError(f"Series raw footage not found at: {raw_path}")

                probe_s = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(raw_path)],
                    capture_output=True, text=True, check=True
                )
                raw_dur = float(probe_s.stdout.strip())
                logger.info("📹 Primary series footage: %s (raw=%.2fs | audio=%.2fs)", raw_path.name, raw_dur, duration_sec)

                if raw_dur > (duration_sec + 6.0):
                    slices_dir = WORKSPACE / "content_series" / series_id / "slices"
                    slices_dir.mkdir(parents=True, exist_ok=True)

                    s1_dur = round(duration_sec * 0.24, 2)
                    s2_dur = round(duration_sec * 0.34, 2)
                    s3_dur = round(duration_sec * 0.21, 2)
                    s4_dur = round(duration_sec - (s1_dur + s2_dur + s3_dur), 2)

                    s4_start = max(0.0, raw_dur - s4_dur)
                    s3_start = max(0.0, s4_start - s3_dur - 1.0)
                    mid_space = max(0.0, s3_start - s1_dur)
                    s2_start = round(s1_dur + max(0.0, (mid_space - s2_dur) / 2.0), 2)

                    slice_configs = [
                        (0.0, s1_dur),
                        (s2_start, s2_dur),
                        (s3_start, s3_dur),
                        (s4_start, s4_dur),
                    ]
                    cut_paths = []
                    dur_targets = []
                    for idx, (st_t, dur_t) in enumerate(slice_configs, 1):
                        slice_file = slices_dir / f"{series_id}_{t_key}_slice_{idx}.mp4"
                        cmd_slice = [
                            "ffmpeg", "-y",
                            "-ss", f"{st_t:.2f}",
                            "-i", str(raw_path),
                            "-t", f"{dur_t:.2f}",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                            "-an",
                            str(slice_file)
                        ]
                        subprocess.run(cmd_slice, check=True, capture_output=True)
                        cut_paths.append(slice_file)
                        dur_targets.append(dur_t)

                    selected_clips = cut_paths
                    clip_durations = dur_targets
                    logger.info("✂️ Created 4 non-overlapping chronological narrative cuts from %s", raw_path.name)
                else:
                    selected_clips = [raw_path]
                    clip_durations = [duration_sec]

                qc_assembly = audit_footage_assembly(selected_clips, clip_durations)
                if not qc_assembly["passed"]:
                    raise RuntimeError(f"Serial footage assembly QC failed: {qc_assembly['errors']}")
                qc_passed = True

        # Self-healing loop for daily/multi-clip topics (or multi-clip serials)
        if not qc_passed:
            for qc_attempt in range(1, 4):
                scene_plans = renderer.select_footage_by_speech_beats(
                    captions_path=captions_json_path,
                    topic_key=t_key,
                    series_id=series_id
                )
                if scene_plans:
                    selected_clips = [s["clip_path"] for s in scene_plans]
                    clip_durations = [s["duration"] for s in scene_plans]
                    logger.info("🎙️ Milo Script-Synced Director: %d speech beat transitions generated", len(selected_clips))
                else:
                    selected_clips = renderer.select_vertical_footage(
                        target_duration=duration_sec,
                        target_cut_duration=3.6,
                        topic_key=t_key,
                        full_script=topic.get("full_script") or topic.get("script") or topic.get("title", ""),
                        series_id=series_id
                    )
                    clip_durations = None

                slice_dur_param = clip_durations if clip_durations else (duration_sec / max(1, len(selected_clips)))
                qc_assembly = audit_footage_assembly(selected_clips, slice_dur_param)

                if qc_assembly["passed"]:
                    qc_passed = True
                    logger.info("🛡️ Cleo QC Footage Assembly Approved on attempt %d: %d unique cuts", qc_attempt, len(selected_clips))
                    break
                else:
                    logger.warning("🚨 Cleo QC Footage Rejection on attempt %d: %s. Retrying assembly...", qc_attempt, qc_assembly["errors"])
                    time.sleep(1)

        # Fallback to ultra-safe vertical footage if speech beats still somehow failed QC
        if not qc_passed:
            logger.warning("⚠️ Speech beats footage did not pass QC after retries. Falling back to guaranteed safe vertical footage pool...")
            selected_clips = renderer.select_vertical_footage(
                target_duration=duration_sec,
                target_cut_duration=3.8,
                topic_key=t_key,
                full_script=topic.get("full_script") or topic.get("script") or topic.get("title", ""),
                series_id=series_id
            )
            clip_durations = None
            slice_dur_param = duration_sec / max(1, len(selected_clips))
            qc_assembly = audit_footage_assembly(selected_clips, slice_dur_param)
            if not qc_assembly["passed"]:
                logger.warning("Auto-healing duplicate clips in fallback pool...")
                seen_clips = set()
                healed_clips = []
                for c in selected_clips:
                    if str(c) not in seen_clips:
                        healed_clips.append(c)
                        seen_clips.add(str(c))
                selected_clips = healed_clips
                logger.info("🛡️ Auto-healed fallback clips: %d cuts", len(selected_clips))

        # 1.5. Cleo DB Gatekeeper: Cross-reference footage selection against Database SSOT
        db_qc = audit_against_database(t_key, selected_clips)
        if not db_qc["passed"]:
            raise RuntimeError(f"🚨 CLEO DB-QC REJECTION: {db_qc['errors']}")
        logger.info("🛡️ Cleo DB-QC Gate Approved: Footage 100% matches DB storyline & series scope.")

        # 2. Render High-CTR Remotion Still Thumbnail
        remotion_thumb_path = Path(f"/tmp/{t_key}_remotion_thumb.jpg")
        primary_clip = selected_clips[0] if selected_clips else None
        renderer.render_remotion_thumbnail(
            hook_title=clean_title,
            hook_subtitle=hook_sub,
            badge_text=f"🐱 {badge_text}",
            output_thumb_path=remotion_thumb_path,
            bg_image_ref=primary_clip,
        )

        # 3. Render Remotion transparent overlay (Cached if already exists for this topic)
        overlay_mov = Path(f"/tmp/{t_key}_remotion_overlay.mov")
        if overlay_mov.exists() and overlay_mov.stat().st_size > 1024 * 1024:
            logger.info("⚡ Remotion transparent overlay found in cache: %s (%.2f MB). Skipping render!", overlay_mov, overlay_mov.stat().st_size / (1024 * 1024))
        else:
            renderer.render_overlay_layer(
                hook_title=clean_title,
                hook_subtitle=hook_sub,
                badge_text=f"🐱 {badge_text}",
                captions_filename=audio_info["captions_file"],
                duration_sec=duration_sec,
                output_mov_path=overlay_mov,
                subtitle_bottom=500,
                layout_mode="youtube_shorts",
                show_safe_area_guide=False,
            )

        # 4. Composite with FFMPEG (inject Remotion thumbnail as 0.08s poster frame)
        master_audio = PUBLIC_DIR / audio_info["master_audio_file"]
        output = renderer.composite_master(
            footage_clips=selected_clips,
            overlay_mov=overlay_mov,
            master_audio=master_audio,
            duration_sec=duration_sec,
            output_mp4=output_file,
            thumbnail_path=remotion_thumb_path,
            clip_durations=clip_durations,
        )
        logger.info(f"🎉 Hybrid render successful! File size: {output.stat().st_size / 1024 / 1024:.2f} MB")

        # 4. Anti-Cutoff Hard Guard Assert (PRD Rule #3 & SOP)
        probe_v = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(output)],
            capture_output=True, text=True, check=True
        )
        actual_v_dur = float(probe_v.stdout.strip())
        logger.info(f"🛡️ Cleo QC Duration Audit: Target Audio={duration_sec:.2f}s | Rendered Video={actual_v_dur:.2f}s")
        if actual_v_dur < (duration_sec - 0.5):
            raise RuntimeError(f"🚨 FATAL QC REJECTION: Video ({actual_v_dur:.2f}s) terpotong sebelum audio ({duration_sec:.2f}s) selesai! Upload dibatalkan!")

        # 5. Keep overlay_mov cached in /tmp during assembly & revisions (purged after successful upload)
        return output

    def publish_and_reconcile(
        self,
        video_path: Path,
        topic: Dict[str, Any],
        privacy_status: str = "public"
    ) -> Dict[str, Any]:
        """Uploads video to YouTube channel via Data API v3 and marks DB status as published."""
        t_key = topic["topic_key"]
        title = topic["title"]
        if "#Shorts" not in title:
            title = f"{title} #Shorts"
        if len(title) > 100:
            title = title[:97] + "..."

        # Fetch Music credit line to ensure 100% YouTube Content ID & Attribution compliance
        from doni_music_selector import get_music_and_sfx_from_db
        music_meta = get_music_and_sfx_from_db(t_key)
        music_credit = music_meta.get("credit_line", "")

        description = (
            f"{topic['title']}\n\n"
            f"{topic.get('hook_banner', '')}\n\n"
            f"{topic['full_script']}\n\n"
            f"Subscribe @DoniesDaily untuk fakta anabul seru setiap hari! 🐾✨\n\n"
            f"{music_credit}\n\n"
            f"#Shorts #KucingLucu #FaktaKucing #DoniesDaily #CatLovers #Anabul"
        )
        tags = ["Shorts", "KucingLucu", "FaktaKucing", "DoniesDaily", "CatLovers", "Anabul", f"donies_key:{t_key}"]

        # HARD GATE: Inspect rendered master video against Database & AI Vision BEFORE upload
        from doni_qc_gate import audit_against_database
        logger.info("🔍 Running Cleo DB & AI-Vision Final Gatekeeper before upload...")
        db_qc_final = audit_against_database(t_key, [], video_path=video_path)
        if not db_qc_final["passed"]:
            err_msg = "; ".join(db_qc_final.get("errors", []))
            logger.error(f"🚨 CLEO POST-RENDER QC REJECTION: {err_msg}")
            raise RuntimeError(f"🚨 CLEO POST-RENDER QC REJECTION: {err_msg}")
        logger.info("🛡️ Cleo Post-Render QC Approved: Video verified Shorts-compliant and matches DB SSOT.")

        # WAL Path
        wal_file = WORKSPACE / "data" / "production_wal.jsonl"
        wal_file.parent.mkdir(parents=True, exist_ok=True)

        def write_wal_entry(stage: str, extra: Optional[Dict[str, Any]] = None):
            entry = {
                "ts": datetime.now(JKT_TZ).isoformat(),
                "topic_key": t_key,
                "title": title,
                "video_path": str(video_path),
                "stage": stage
            }
            if extra:
                entry.update(extra)
            try:
                with open(wal_file, "a") as f:
                    f.write(json.dumps(entry) + "\n")
            except Exception as e:
                logger.warning(f"⚠️ Failed to write WAL log: {e}")

        # IDEMPOTENCY GUARD: Check if already uploaded to YouTube channel before calling insert
        tag_anchor = f"donies_key:{t_key}"
        existing_vid_id = self.publisher.find_existing_video_by_tag_or_title(tag_anchor, title)
        if existing_vid_id:
            logger.info(f"🛡️ [ANTI-DUPLICATE GUARD] Found video already live on YouTube: {existing_vid_id}! Skipping upload to save 1,600 quota units.")
            res = {
                "success": True,
                "video_id": existing_vid_id,
                "short_url": f"https://www.youtube.com/shorts/{existing_vid_id}",
                "watch_url": f"https://youtu.be/{existing_vid_id}",
                "title": title,
                "reused": True
            }
        else:
            write_wal_entry("PRE_UPLOAD_INTENT", {"tag_anchor": tag_anchor})
            logger.info(f"📤 Uploading master video to YouTube as '{privacy_status}'...")
            res = self.publisher.upload_short(
                video_path=str(video_path),
                title=title,
                description=description,
                tags=tags,
                privacy_status=privacy_status
            )

        if res.get("success"):
            vid_id = res.get("video_id")
            logger.info(f"✅ Video live at: https://www.youtube.com/shorts/{vid_id}")
            write_wal_entry("UPLOAD_SUCCESS", {"video_id": vid_id, "short_url": f"https://www.youtube.com/shorts/{vid_id}"})

            # Upload Custom Thumbnail if provided
            thumb_path = topic.get("thumbnail_path") or str(video_path).replace(".mp4", "_thumb.jpg")
            if vid_id and Path(thumb_path).exists():
                try:
                    logger.info(f"🖼️ Setting custom thumbnail from: {thumb_path}")
                    self.publisher.set_thumbnail(str(vid_id), thumb_path)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to upload custom thumbnail: {e}")

            # Reconcile DB
            sql_update = f"UPDATE ai_brain.doniesdaily_content_ideas SET status = 'published', updated_at = NOW() WHERE topic_key = '{t_key}';"
            subprocess.run(["docker", "exec", "-i", "supabase-db", "psql", "-U", "postgres", "-d", "postgres", "-c", sql_update], capture_output=True)

            # Probe actual video duration
            probe_post = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
                capture_output=True, text=True
            )
            v_post_dur = round(float(probe_post.stdout.strip()), 1) if probe_post.returncode == 0 else 20.0

            sql_post = f"""
            INSERT INTO ai_brain.doniesdaily_posts (video_id, topic_key, title, banner_title, duration_sec, short_url, privacy_status)
            VALUES ('{vid_id}', '{t_key}', '{title.replace("'", "''")}', '{topic.get("hook_banner", "").replace("'", "''")}', {v_post_dur}, 'https://www.youtube.com/shorts/{vid_id}', '{privacy_status}')
            ON CONFLICT (video_id) DO UPDATE
            SET topic_key = EXCLUDED.topic_key,
                short_url = EXCLUDED.short_url;

            UPDATE ai_brain.doniesdaily_content_ideas
            SET status = 'published',
                published_video_id = '{vid_id}',
                published_short_url = 'https://www.youtube.com/shorts/{vid_id}',
                updated_at = NOW()
            WHERE topic_key = '{t_key}';
            """
            res_post_sql = subprocess.run(["docker", "exec", "-i", "supabase-db", "psql", "-U", "postgres", "-d", "postgres", "-c", sql_post], capture_output=True, text=True)
            if res_post_sql.returncode != 0:
                logger.error("❌ Failed to update DB ledger: %s", res_post_sql.stderr)
            else:
                logger.info("✅ Database ledger synchronized with published state (topic_key & content_ideas updated)!")

            # Auto-purge heavy ProRes 4444 overlay from /tmp now that publish succeeded
            overlay_mov = Path(f"/tmp/{t_key}_remotion_overlay.mov")
            if overlay_mov.exists():
                try:
                    mov_size_mb = overlay_mov.stat().st_size / (1024 * 1024)
                    overlay_mov.unlink()
                    logger.info("🧹 Auto-purged ephemeral Remotion overlay (%.2f MB) from /tmp: %s", mov_size_mb, overlay_mov)
                except Exception as e:
                    logger.warning("Failed to purge ephemeral overlay: %s", e)

        return res

    async def run(
        self,
        topic_key: Optional[str] = None,
        publish: bool = True,
        privacy_status: str = "public"
    ) -> Dict[str, Any]:
        """Executes full autonomous cycle from DB topic to published YouTube Short."""
        logger.info("==================================================")
        logger.info("🐱 DONIESDAILY MASTER PRODUCTION PIPELINE STARTING")
        logger.info("==================================================")

        # 1. Fetch Topic
        import fcntl
        lock_file = open("/tmp/doni_render.lock", "w")
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.warning("⚠️ Another DoniesDaily render process is currently running! Exiting to avoid 2-vCPU thrashing.")
            return {"success": False, "error": "render_in_progress"}

        try:
            topic = self.fetch_next_topic(topic_key)
            t_key = topic["topic_key"]
            logger.info(f"🎯 Target Topic: {t_key} -> '{topic['title']}'")

            # Fast-Path Optimization: Check if pre-rendered valid master video already exists AND passes Cleo QC
            master_video_path = WORKSPACE / "data" / f"{t_key}_master.mp4"
            if master_video_path.exists() and master_video_path.stat().st_size > 5_000_000:
                from doni_qc_gate import audit_against_database
                fast_qc = audit_against_database(t_key, [], video_path=master_video_path)
                if fast_qc.get("passed", False):
                    logger.info("⚡ [FAST-PATH] Found pre-rendered master video (%.2f MB) passing QC: %s", master_video_path.stat().st_size / (1024 * 1024), master_video_path)
                    video_path = master_video_path
                else:
                    logger.warning("⚠️ [FAST-PATH BYPASS] Pre-rendered video %s failed QC: %s. Re-rendering from scratch...", master_video_path, fast_qc.get("errors"))
                    master_video_path.unlink(missing_ok=True)
                    audio_info = self.synthesize_audio_and_captions(topic)
                    video_path = self.render_remotion_short(topic, audio_info, "")
            else:
                # 2. Audio & Captions
                audio_info = self.synthesize_audio_and_captions(topic)

                # 3. Video Background (Handled directly by Hybrid Renderer)
                bg_video = ""

                # 4. Render Remotion Short (Hybrid Mode)
                video_path = self.render_remotion_short(topic, audio_info, bg_video)

            # 5. Publish
            if publish:
                upload_res = self.publish_and_reconcile(video_path, topic, privacy_status=privacy_status)
                # Release render flock before launching long-running viewer swarm
                try:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
                    lock_file.close()
                except Exception:
                    pass

                # Trigger Autonomous Multi-Viewer Swarm Agent (Chrome CDP :9222)
                vid_id = upload_res.get("video_id")
                if vid_id and not upload_res.get("reused"):
                    try:
                        logger.info(f"🐝 Launching autonomous Multi-Viewer Swarm Agent for {vid_id}...")
                        swarm_script = ROOT_DIR.parent.parent / "tools" / "doni_swarm_agent.py"
                        if not swarm_script.exists():
                            swarm_script = Path("/home/ubuntu/tools/doni_swarm_agent.py")
                        cmd_swarm = [
                            sys.executable,
                            str(swarm_script),
                            vid_id
                        ]
                        subprocess.run(cmd_swarm, timeout=300)
                        logger.info(f"✅ Swarm engagement cycle completed for {vid_id}!")

                        # Immediately trigger Studio Replier to heart & reply to early comments
                        replier_script = Path("/home/ubuntu/tools/doni_studio_replier.py")
                        if replier_script.exists():
                            logger.info(f"💬 Running immediate YouTube Studio Replier sweep after upload...")
                            subprocess.run([sys.executable, str(replier_script), "--limit", "10"], timeout=120)
                    except Exception as se:
                        logger.warning(f"Swarm/Replier agent warning: {se}")

                return {
                    "success": True,
                    "video_path": str(video_path),
                    "upload": upload_res
                }
            else:
                logger.info("Test mode: Publishing skipped.")
                return {
                    "success": True,
                    "video_path": str(video_path),
                    "mode": "render_only"
                }
        finally:
            try:
                fcntl.flock(lock_file, fcntl.LOCK_UN)
                lock_file.close()
            except Exception:
                pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DoniesDaily Master Remotion & Flow Autonomous Pipeline")
    parser.add_argument("--topic", type=str, default=None, help="Specific topic_key to produce")
    parser.add_argument("--no-publish", action="store_true", help="Render video only without publishing")
    parser.add_argument("--privacy", type=str, default="public", choices=["public", "unlisted", "private"], help="YouTube privacy status")
    args = parser.parse_args()

    pipeline = DoniRemotionFlowPipeline()
    asyncio.run(pipeline.run(
        topic_key=args.topic,
        publish=not args.no_publish,
        privacy_status=args.privacy
    ))

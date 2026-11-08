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
        """Pulls next 'ready' topic from Supabase PostgreSQL DB to guarantee zero duplicate content."""
        if topic_key:
            sql = f"SELECT json_agg(t) FROM (SELECT topic_key, title, hook_banner, hook_subtitle, hook_vocal, full_script, flow_prompts, scene_breakdown, status FROM ai_brain.doniesdaily_content_ideas WHERE topic_key = '{topic_key}') t;"
        else:
            sql = "SELECT json_agg(t) FROM (SELECT topic_key, title, hook_banner, hook_subtitle, hook_vocal, full_script, flow_prompts, scene_breakdown, status FROM ai_brain.doniesdaily_content_ideas WHERE status = 'ready' ORDER BY created_at ASC LIMIT 1) t;"

        res = subprocess.run([
            "docker", "exec", "-i", "supabase-db",
            "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c", sql
        ], capture_output=True, text=True, check=True)

        raw = res.stdout.strip()
        if not raw or raw == "null":
            raise RuntimeError("No topics with status 'ready' found in ai_brain.doniesdaily_content_ideas!")

        ideas = json.loads(raw)
        return ideas[0]

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

        # Mix with soft playful BGM + Dynamic Sound Effects (SFX)
        logger.info("🎵 Mixing voiceover with acoustic cat BGM + auto-ducking & dynamic SFX...")
        
        # Detect exact timing for SFX from captions
        sfx_inputs = []
        sfx_filters = []
        next_input_idx = 2
        
        # 1. Opening Hook impact SFX (Taco Bell Bong at 0.1s)
        taco_bell_path = ASSETS_DIR / "audio/sfx/sfx_taco_bell_bong.mp3"
        if taco_bell_path.exists():
            sfx_inputs.extend(["-i", str(taco_bell_path)])
            sfx_filters.append(f"[{next_input_idx}:a]volume=0.35,adelay=100|100[sfx_hook];")
            next_input_idx += 1

        # 2. Interactive Double-Tap Pop SFX (Undertale chime / toy squeak right when "pencet" is spoken)
        double_tap_delay_ms = 4000
        try:
            if captions_path.exists():
                with open(captions_path, "r", encoding="utf-8") as f:
                    words_data = json.load(f)
                for w in words_data:
                    clean_w = re.sub(r'[^\w]', '', w.get("text", "")).lower()
                    if clean_w in ["pencet", "tap", "ketuk"]:
                        double_tap_delay_ms = int(w.get("startMs", 4000))
                        break
        except Exception:
            pass

        chime_path = ASSETS_DIR / "audio/sfx/sfx_yellow_undertale_chime.mp3"
        if chime_path.exists():
            sfx_inputs.extend(["-i", str(chime_path)])
            sfx_filters.append(f"[{next_input_idx}:a]volume=0.45,adelay={double_tap_delay_ms}|{double_tap_delay_ms}[sfx_tap];")
            next_input_idx += 1

        total_audio_inputs = next_input_idx
        mix_sources = ["[voice]", "[bgm]"]
        if taco_bell_path.exists():
            mix_sources.append("[sfx_hook]")
        if chime_path.exists():
            mix_sources.append("[sfx_tap]")

        filter_complex = (
            "[0:a]volume=1.35,highpass=f=80,dynaudnorm[voice];"
            "[1:a]volume=0.08[bgm];"
            + "".join(sfx_filters)
            + "".join(mix_sources)
            + f"amix=inputs={len(mix_sources)}:duration=first:dropout_transition=2[aout]"
        )

        cmd_audio = [
            "ffmpeg", "-y",
            "-i", str(raw_voice),
            "-stream_loop", "-1", "-i", str(BGM_PATH),
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

        # Fallback to local verified clips if flow clips were not obtained
        if not downloaded_clips:
            logger.info("Using curated cat action footage pool...")
            stock_names = ["clip8_stock.mp4", "clip6_stock.mp4", "clip1_fight.mp4", "clip2_ball.mp4", "clip14_yawning.mp4"]
            for name in stock_names:
                p = CAT_VIDEOS_DIR / name
                if p.exists():
                    downloaded_clips.append(p)

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

        badge_text = re.sub(r'[^\w\s!]', '', topic.get("hook_banner") or "FAKTA ANABUL").strip()[:18]
        clean_title = re.sub(r'[^\w\s?]', '', re.sub(r'#\w+', '', topic['title'])).strip().upper()[:42]
        hook_sub = re.sub(r'[^\w\s!]', '', topic.get("hook_subtitle") or "Bukan Karena Marah Lho!").strip()[:35]
        duration_sec = float(audio_info["duration"])

        # 1. Select clean vertical 9:16 clips synchronized with voice script speech beats
        # Voice-Synced Scene Transitions (Hukum Besi #13): Cuts happen on sentence beats + semantic match
        from doni_qc_gate import audit_footage_assembly
        captions_json_path = PUBLIC_DIR / audio_info["captions_file"]

        selected_clips = []
        clip_durations = None
        qc_passed = False

        # Self-healing loop: try speech beats up to 3 times, fallback to safe vertical footage if needed
        for qc_attempt in range(1, 4):
            scene_plans = renderer.select_footage_by_speech_beats(
                captions_path=captions_json_path,
                topic_key=t_key
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
                    full_script=topic.get("full_script") or topic.get("script") or topic.get("title", "")
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
                full_script=topic.get("full_script") or topic.get("script") or topic.get("title", "")
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

        description = (
            f"{topic['title']}\n\n"
            f"{topic.get('hook_banner', '')}\n\n"
            f"{topic['full_script']}\n\n"
            f"Subscribe @DoniesDaily untuk fakta anabul seru setiap hari! 🐾✨\n\n"
            f"#Shorts #KucingLucu #FaktaKucing #DoniesDaily #CatLovers #Anabul"
        )
        tags = ["Shorts", "KucingLucu", "FaktaKucing", "DoniesDaily", "CatLovers", "Anabul"]

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
            INSERT INTO ai_brain.doniesdaily_posts (video_id, title, banner_title, duration_sec, short_url, privacy_status)
            VALUES ('{vid_id}', '{title.replace("'", "''")}', '{topic.get("hook_banner", "").replace("'", "''")}', {v_post_dur}, 'https://www.youtube.com/shorts/{vid_id}', '{privacy_status}')
            ON CONFLICT (video_id) DO NOTHING;
            """
            subprocess.run(["docker", "exec", "-i", "supabase-db", "psql", "-U", "postgres", "-d", "postgres", "-c", sql_post], capture_output=True)
            logger.info("✅ Database ledger synchronized with published state!")

            # Auto-purge heavy ProRes 4444 overlay from /tmp now that publish succeeded
            overlay_mov = Path(f"/tmp/{t_key}_remotion_overlay.mov")
            if overlay_mov.exists():
                try:
                    mov_size_mb = overlay_mov.stat().st_size / (1024 * 1024)
                    overlay_mov.unlink()
                    logger.info("🧹 Auto-purged ephemeral Remotion overlay (%.2f MB) from /tmp: %s", mov_size_mb, overlay_mov)
                except Exception as e:
                    logger.warning("Failed to purge ephemeral overlay: %s", e)

            # Trigger Autonomous Multi-Viewer Swarm Agent (Chrome CDP :9222)
            try:
                logger.info(f"🐝 Launching autonomous Multi-Viewer Swarm Agent for {vid_id}...")
                swarm_script = Path("/home/ubuntu/tools/doni_swarm_agent.py")
                cmd_swarm = [
                    sys.executable,
                    str(swarm_script),
                    vid_id
                ]
                subprocess.run(cmd_swarm, timeout=300)
                logger.info(f"✅ Swarm engagement cycle completed for {vid_id}!")
            except Exception as se:
                logger.warning(f"Swarm agent warning: {se}")

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
        topic = self.fetch_next_topic(topic_key)
        t_key = topic["topic_key"]
        logger.info(f"🎯 Target Topic: {t_key} -> '{topic['title']}'")

        # Fast-Path Optimization: Check if pre-rendered valid master video already exists
        master_video_path = self.data_dir / f"{t_key}_master.mp4"
        if master_video_path.exists() and master_video_path.stat().st_size > 5_000_000:
            logger.info("⚡ [FAST-PATH] Found pre-rendered master video (%.2f MB): %s", master_video_path.stat().st_size / (1024 * 1024), master_video_path)
            video_path = master_video_path
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

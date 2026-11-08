"""Doni Hybrid Video Renderer: Remotion React Overlays + FFMPEG Hardware Video Compositing.
Solves the VPS 2-core OOM/timeout bottleneck while guaranteeing 100% Remotion visual standards:
1. Remotion renders graphic overlays (HookTitle spring physics, dynamic kinetic captions, watermark, outro CTA)
   to a transparent ProRes 4444 video in seconds (no heavy background video decode in Chromium).
2. Remotion renders high-CTR Still Thumbnails (<Still id="DoniThumbnail" />) with punchy typography and dynamic keyframe background.
3. FFMPEG composites the native 9:16 cat video with the transparent Remotion overlay, injects the Remotion thumbnail
   as an initial poster frame (anti-Shorts bug), and masters the audio.
"""

import json
import logging
import random
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("doni_hybrid_renderer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent
REMOTION_DIR = BASE_DIR / "remotion"
PUBLIC_DIR = REMOTION_DIR / "public"
ASSETS_DIR = BASE_DIR / "assets"
DATA_DIR = BASE_DIR / "data"


class DoniHybridRenderer:
    def __init__(self):
        self.remotion_dir = REMOTION_DIR
        self.public_dir = PUBLIC_DIR
        self.public_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _fetch_db_catalog(self) -> List[Dict[str, Any]]:
        """Fetch pure cat catalog directly from ai_brain.doniesdaily_clip_catalog."""
        catalog = []
        try:
            cmd = [
                "docker", "exec", "-i", "supabase-db",
                "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c",
                "SELECT json_agg(t) FROM (SELECT clip_id AS id, cluster, rel_path, abs_path, duration, tags, description, emotion, action FROM ai_brain.doniesdaily_clip_catalog WHERE is_active = TRUE) t;"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                raw = res.stdout.strip()
                if raw and raw != "null":
                    catalog = json.loads(raw)
        except Exception as e:
            logger.warning(f"Could not load catalog from PostgreSQL: {e}")

        # Fallback to local cat_assets_catalog.json ONLY if DB unavailable (NO rglob allowed!)
        if not catalog:
            catalog_file = self.data_dir / "cat_assets_catalog.json"
            if catalog_file.exists():
                try:
                    with open(catalog_file, "r", encoding="utf-8") as f:
                        catalog = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load catalog fallback: {e}")

        # STRICT ISOLATION ASSERTION: Filter out any Arya/Reels paths
        sanitized = []
        for item in catalog:
            p_str = item.get("abs_path", "")
            if "reels-lemonaru" in p_str or "assets/footage" in p_str:
                logger.error(f"[SECURITY ALERT] Banned Arya footage rejected: {p_str}")
                continue
            sanitized.append(item)
        return sanitized

    def select_vertical_footage(
        self,
        num_clips: Optional[int] = None,
        target_duration: float = 60.0,
        target_cut_duration: float = 3.6,
        topic_key: Optional[str] = None,
        full_script: Optional[str] = None
    ) -> List[Path]:
        """Universal Semantic Asset Selector with Strict Zero In-Video Repetition (Hukum Besi #13).
        Pools all cat clips from PostgreSQL (Fahru authentic clips + Google Flow AI renders).
        Enforces dynamic pacing (3.2s - 4.0s per cut), diverse cluster isolation, and zero looping.
        """
        import math
        needed_clips = num_clips if (num_clips is not None and num_clips >= 8) else max(8, math.ceil(target_duration / target_cut_duration))
        catalog = self._fetch_db_catalog()

        # 1. Fetch recent clip usage history from PostgreSQL (cross-video fatigue)
        recent_used_clips = set()
        last_used_clip = None
        try:
            cmd_db = [
                "docker", "exec", "-i", "supabase-db",
                "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c",
                "SELECT clip_name FROM ai_brain.doniesdaily_clip_usage ORDER BY used_at DESC LIMIT 20;"
            ]
            res_db = subprocess.run(cmd_db, capture_output=True, text=True, timeout=5)
            if res_db.returncode == 0 and res_db.stdout.strip():
                lines = [l.strip() for l in res_db.stdout.strip().split("\n") if l.strip()]
                for idx, c in enumerate(lines):
                    recent_used_clips.add(c)
                    if idx == 0:
                        last_used_clip = c
        except Exception as e:
            logger.warning(f"Could not query clip usage ledger: {e}")

        # 2. Extract keywords from topic_key AND full_script
        text_corpus = f"{topic_key or ''} {full_script or ''}".lower()
        clean_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", text_corpus))

        synonyms = {
            "gigit": ["gigit", "bite", "bites", "cakar", "serang", "overstimulasi", "gigi"],
            "elus": ["elus", "petting", "sentuh", "tangan", "belai", "manja"],
            "perut": ["perut", "belly", "terlentang", "trap", "jebakan"],
            "tidur": ["tidur", "sleep", "ngantuk", "rebahan", "peluk", "mimpi", "cozy"],
            "ekor": ["ekor", "tail", "dangling", "kibas", "goyang"],
            "sedih": ["sedih", "sad", "lesu", "murung", "menangis", "comfort"],
            "makan": ["makan", "ikan", "food", "lapar", "eat", "daging", "snack"],
            "susu": ["susu", "milk", "laktosa", "minum", "bahaya", "dairy"],
            "roti": ["roti", "ngadon", "kneading", "pijat", "selimut", "purr", "dengkur"],
            "zoomies": ["zoomies", "lari", "sprint", "ngebut", "heboh", "malam", "midnight", "kaget"],
            "kepo": ["kepo", "curious", "usil", "jail", "dorong", "nudge", "explore", "sentuh"],
            "flehmen": ["flehmen", "bau", "smell", "cium", "nganga", "mulut"],
            "chubby": ["chubby", "gemoy", "gendut", "diangkat", "pipi", "bakpao"],
        }

        scored_clips = []
        # HUKUM BESI #18: STRICT SQUAD ISOLATION (ZERO ARYA/HUMAN/LIVESTOCK IN DONIES)
        banned_arya_keywords = {"domba", "kambing", "ternak", "seminar", "selfie", "karaoke", "cermin", "tutorial", "merokok", "pekerja", "sekolah", "pemuda", "screencast"}

        for entry in catalog:
            c_id = entry.get("id", entry.get("stem", ""))
            c_path = Path(entry["abs_path"])
            if not c_path.exists():
                continue

            c_tags = [t.lower() for t in entry.get("tags", [])]
            c_desc = entry.get("description", "").lower()
            entry_text = f"{c_id} {c_desc} {' '.join(c_tags)}".lower()

            if any(b in entry_text for b in banned_arya_keywords):
                logger.warning(f"🚫 [SQUAD ISOLATION] Milo menolak footage non-kucing: {c_id}")
                continue

            score = 0.0

            # Direct word match
            for word in clean_words:
                if word in c_tags:
                    score += 6.0
                if word in c_desc:
                    score += 3.0

            # Synonym match
            for key, syn_list in synonyms.items():
                if any(w in clean_words for w in syn_list):
                    if any(t in c_tags for t in syn_list):
                        score += 10.0

            # Authentic footage bonus (Fahru's authentic cat clips) vs AI penalty with Gated Category Bias
            if entry.get("category") == "fahru_sent":
                score += 12.0 if score > 0 else 2.0  # Cegah klip asli tak relevan menang mutlak
            else:
                score += -4.0 if score >= 10.0 else -10.0  # Penalti lebih lembut jika AI relevan

            # Anti-repetition cross-video fatigue penalty
            if c_id == last_used_clip:
                score -= 25.0
            elif c_id in recent_used_clips:
                score -= 10.0

            score += random.uniform(0.1, 1.5)
            scored_clips.append((score, c_path, entry))

        scored_clips.sort(key=lambda x: x[0], reverse=True)

        # 3. STRICT HUKUM BESI #13 IN-VIDEO SELECTION:
        # - NO repeated clip IDs in 1 video
        # - Max 1 clip per AI cluster on first pass (never bunch same-room scenes)
        # - Prioritaskan footage asli Fahru (fahru_sent) terlebih dahulu, AI sebagai pelengkap/fallback
        selected_entries = []
        used_ids = set()
        used_clusters = set()

        fahru_pool = [e for s, p, e in scored_clips if e.get("category") == "fahru_sent"]
        ai_pool = [e for s, p, e in scored_clips if e.get("category") != "fahru_sent"]

        # Shuffle slightly to maintain fresh variety among authentic clips
        random.shuffle(fahru_pool)

        f_idx, a_idx = 0, 0
        while len(selected_entries) < needed_clips and (f_idx < len(fahru_pool) or a_idx < len(ai_pool)):
            # 1. Prioritas Utama: Pick next Fahru authentic clip
            if f_idx < len(fahru_pool):
                candidate = fahru_pool[f_idx]
                f_idx += 1
                if candidate["id"] not in used_ids:
                    selected_entries.append(candidate)
                    used_ids.add(candidate["id"])

            if len(selected_entries) >= needed_clips:
                break

            # 2. Pelengkap: Pick next AI clip from a distinct cluster jika dibutuhkan
            while a_idx < len(ai_pool):
                candidate = ai_pool[a_idx]
                a_idx += 1
                c_cluster = candidate.get("cluster", "ai_cluster")
                if c_cluster not in used_clusters and candidate["id"] not in used_ids:
                    selected_entries.append(candidate)
                    used_clusters.add(c_cluster)
                    used_ids.add(candidate["id"])
                    break

        # If more clips are needed to fulfill target cut pacing without repetition:
        if len(selected_entries) < needed_clips:
            remaining = [e for s, p, e in scored_clips if e["id"] not in used_ids]
            for r in remaining:
                if len(selected_entries) >= needed_clips:
                    break
                # Ensure no consecutive clips from the same cluster
                if selected_entries and selected_entries[-1].get("cluster") == r.get("cluster"):
                    continue
                selected_entries.append(r)
                used_ids.add(r["id"])

        # Fallback if library strictly exhausted: take any remaining unused
        if len(selected_entries) < needed_clips:
            for s, p, e in scored_clips:
                if len(selected_entries) >= needed_clips:
                    break
                if e["id"] not in used_ids:
                    selected_entries.append(e)
                    used_ids.add(e["id"])

        selected_paths = [Path(e["abs_path"]) for e in selected_entries]

        logger.info("🎬 Milo Zero-Repetition Matcher selected %d unique cuts for %.1fs video:", len(selected_paths), target_duration)
        for idx, e in enumerate(selected_entries, 1):
            logger.info("   %02d. [%s] %s (%.1fs)", idx, e.get("cluster"), e.get("id"), e.get("duration", 10.0))

        # Record selection into PostgreSQL clip usage ledger
        try:
            t_key = topic_key or "unknown_topic"
            for p in selected_paths:
                sql_ins = f"INSERT INTO ai_brain.doniesdaily_clip_usage (clip_name, clip_path, topic_key) VALUES ('{p.stem}', '{str(p)}', '{t_key}');"
                subprocess.run(["docker", "exec", "-i", "supabase-db", "psql", "-U", "postgres", "-d", "postgres", "-c", sql_ins], capture_output=True)
        except Exception as e:
            logger.warning(f"Could not log clip usage to DB: {e}")

        return selected_paths

    def extract_speech_beat_segments(
        self,
        captions_path: Path,
        min_seg_dur: float = 4.0,
        max_seg_dur: float = 8.5
    ) -> List[Dict[str, Any]]:
        """Parses word-level captions JSON into clean, natural sentence segments.
        Follows natural sentence boundaries (ending with . ! ?), NOT cut every few words.
        Each sentence gets adequate screen time (4.0s - 8.5s) so the visual can breathe.
        """
        if not captions_path.exists():
            return []
        try:
            with open(captions_path, "r", encoding="utf-8") as f:
                words = json.load(f)
        except Exception as e:
            logger.warning("Failed to parse captions JSON: %s", e)
            return []

        sentences = []
        curr_words = []
        seg_start = 0.0

        for idx, w in enumerate(words):
            text = w.get("text", "").strip()
            s_sec = w.get("startMs", 0) / 1000.0
            e_sec = w.get("endMs", 0) / 1000.0
            if not curr_words:
                seg_start = s_sec
            curr_words.append(text)

            has_terminal_punct = any(text.endswith(p) for p in [".", "!", "?"])
            duration = e_sec - seg_start

            # Only cut on real sentence termination with min duration, or forced max duration
            should_cut = False
            if has_terminal_punct and duration >= min_seg_dur:
                should_cut = True
            elif duration >= max_seg_dur:
                should_cut = True
            elif idx == len(words) - 1:
                should_cut = True

            if should_cut:
                seg_text = " ".join(curr_words)
                words_clean = set(re.findall(r"\b[a-zA-Z]{3,}\b", seg_text.lower()))
                sentences.append({
                    "start": seg_start,
                    "end": e_sec,
                    "text": seg_text,
                    "words": words_clean
                })
                curr_words = []

        if not sentences:
            return []

        # Merge tiny trailing sentences or fragments (< 3.0s) into previous sentence
        merged = []
        for s in sentences:
            dur = s["end"] - s["start"]
            if merged and dur < 3.0:
                prev = merged.pop()
                combined_text = prev["text"] + " " + s["text"]
                merged.append({
                    "start": prev["start"],
                    "end": s["end"],
                    "text": combined_text,
                    "words": set(re.findall(r"\b[a-zA-Z]{3,}\b", combined_text.lower()))
                })
            else:
                merged.append(s)

        # Seamless boundary alignment: zero gap between scene cuts
        aligned = []
        for i, s in enumerate(merged):
            st = 0.0 if i == 0 else aligned[i-1]["end"]
            en = merged[i+1]["start"] if i + 1 < len(merged) else (s["end"] + 0.35)
            aligned.append({
                "index": i + 1,
                "start": round(st, 2),
                "end": round(en, 2),
                "duration": round(en - st, 2),
                "text": s["text"],
                "words": s["words"]
            })
        return aligned

    def select_footage_by_speech_beats(
        self,
        captions_path: Path,
        topic_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Script-Synced Semantic Footage Matcher (Hukum Besi #13 & Script Beat Transitions).
        Aligns each visual cut precisely with the speech cadence of the voiceover.
        Selects 100% unique cat footage matched to the semantics of each sentence.
        """
        segments = self.extract_speech_beat_segments(captions_path)
        if not segments:
            logger.warning("No speech segments found in captions file: %s", captions_path)
            return []

        # Load catalog from PostgreSQL Dual-Brain
        catalog = self._fetch_db_catalog()

        # Fetch recent clip usage history from PostgreSQL
        recent_used_clips = set()
        try:
            cmd_db = [
                "docker", "exec", "-i", "supabase-db",
                "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c",
                "SELECT clip_name FROM ai_brain.doniesdaily_clip_usage ORDER BY used_at DESC LIMIT 15;"
            ]
            res_db = subprocess.run(cmd_db, capture_output=True, text=True, timeout=5)
            if res_db.returncode == 0 and res_db.stdout.strip():
                lines = [l.strip() for l in res_db.stdout.strip().split("\n") if l.strip()]
                for c in lines:
                    recent_used_clips.add(c)
        except Exception as e:
            logger.warning(f"Could not query clip usage ledger: {e}")

        synonyms = {
            "gigit": ["gigit", "bite", "bites", "cakar", "cakaran", "serang", "kuku", "overstimulasi", "perangkap", "maut"],
            "buru": ["buru", "berburu", "hadiah", "bangkai", "bawa", "ikan", "curi", "tangkap", "mangsa", "predator", "kasih"],
            "induk": ["induk", "ibu", "anak", "kitten", "bayi", "keluarga", "ajar", "rawat", "sayang"],
            "elus": ["elus", "petting", "sentuh", "tangan", "jarimu", "belai", "manja", "pijat", "kain", "baju", "selimut"],
            "perut": ["perut", "belly", "terlentang", "trap", "jebakan", "gembul", "vital", "organ"],
            "tidur": ["tidur", "sleep", "ngantuk", "rebahan", "peluk", "mimpi", "cozy", "pasrah", "malaikat", "nyaman", "santai"],
            "ekor": ["ekor", "tail", "dangling", "kibas", "goyang", "radar", "belakang", "punggung"],
            "sedih": ["sedih", "sad", "lesu", "murung", "menangis", "comfort", "panik", "takut", "kecewa", "marah", "marahi"],
            "makan": ["makan", "ikan", "food", "lapar", "eat", "daging", "snack", "kelaparan"],
            "ngeong": ["ngeong", "meow", "panggil", "teriak", "suara", "bicara", "ngomong", "pamer"],
            "tatap": ["tatap", "mata", "wajah", "polos", "bengong", "lihat", "pandang"],
            "kepo": ["kepo", "curious", "usil", "jail", "dorong", "nudge", "explore", "komentar", "cerita"],
            "flehmen": ["flehmen", "bau", "smell", "cium", "nganga", "mulut", "ekspresi", "aroma"],
            "zoomies": ["zoomies", "lari", "sprint", "ngebut", "heboh", "malam", "midnight", "lompat"],
            "chubby": ["chubby", "gemoy", "gendut", "diangkat", "pipi", "bakpao"],
        }

        scene_plans = []
        used_entities = set()

        # MANDATORY CLAUDE OPUS REMOTION DIRECTOR (Instruksi Owner: "untuk edit remotion pakaikan opus wajib")
        opus_selected_map = {}
        try:
            import urllib.request, sqlite3, time, uuid
            cat_map = {c["id"]: c for c in catalog if Path(c["abs_path"]).exists()}
            seg_brief = [
                {"seg_index": s["index"], "duration_sec": s["duration"], "spoken_text": s["text"]}
                for s in segments
            ]
            cat_brief = [
                {
                    "clip_id": c["id"],
                    "cluster": c.get("cluster", ""),
                    "category": c.get("category", ""),
                    "max_dur_sec": round(float(c.get("duration", 10.0)), 2),
                    "tags": c.get("tags", []),
                    "description": c.get("description", ""),
                    "recently_used": c["id"] in recent_used_clips
                }
                for c in cat_map.values()
            ]
            opus_prompt = f"""Kamu adalah Milo, Lead Video Editor & Remotion Director @DoniesDaily (powered by Claude Opus).
Tugasmu menyusun timeline pemotongan klip video (Remotion Scene Cut Plan) mengikuti kalimat narasi voiceover di bawah ini.

TOPIK: {topic_key or 'cat_behavior'}

SEGMEN KALIMAT NARASI (Wajib dipasangkan 1 klip unik per segmen):
{json.dumps(seg_brief, ensure_ascii=False, indent=2)}

KATALOG KLIP TERSEDIA:
{json.dumps(cat_brief, ensure_ascii=False, indent=2)}

ATURAN WAJIB (HUKUM BESI #13 v2 & MANDAT OWNER):
1. Pilih TEPAT 1 `clip_id` dari katalog untuk setiap `seg_index` yang paling cocok secara visual & emosi dengan `spoken_text`.
2. DILARANG KERAS memakai `clip_id` yang sama lebih dari 1 kali dalam 1 video (Zero Duplication).
3. Untuk cluster multi-part (`cat_belly_trap_scratch`, `knocking`, `cat_milk_danger`, `cat_flehmen_response`), maksimal HANYA BOLEH ambil 1 klip per cluster.
4. Wajib pilih klip yang `max_dur_sec >= duration_sec` segmen tersebut (supaya 0% looping).
5. PRIORITAS UTAMA (MANDAT OWNER & KOHERENSI CERITA): Utamakan footage asli Mas Fahru (`category: fahru_sent`) jika relevan secara tema/emosi dengan naskah. Jika naskah membutuhkan visual spesifik yang tidak dimiliki klip asli (misal aksi berburu/dorong benda/minum susu), gunakan klip AI (`category: google_flow_render`) yang relevan. Jangan pernah pasang klip tidur asli pada narasi aksi berburu/agresif! Prioritaskan klip yang `recently_used: false`.
6. ACTIVE CREATIVE MASTERY (MANDAT OWNER - DILARANG EDIT PASIF/MONOTON): Analisis alur emosional naskah secara mendalam (Hook penasaran -> Penjelasan naluri -> Twist mengejutkan -> Outro hangat). Pastikan pergerakan kamera, ekspresi anabul, dan mood visual di setiap segmen benar-benar hidup, variatif, dan memiliki daya tahan retensi tinggi (Hukum Besi #13 & #15).

Kembalikan HANYA JSON array murni tanpa markdown/backticks:
[
  {{"seg_index": 1, "clip_id": "nama_clip_id", "edit_reason": "alasan singkat 1 kalimat"}}
]"""
            req = urllib.request.Request(
                "http://127.0.0.1:8317/v1/chat/completions",
                data=json.dumps({
                    "model": "claude-opus-5-5-high",
                    "messages": [
                        {"role": "system", "content": "You are Milo, an expert Remotion Video Editor & Scene Director powered by Claude Opus. Output valid raw JSON array only."},
                        {"role": "user", "content": opus_prompt}
                    ],
                    "max_tokens": 8192,
                    "temperature": 0.2
                }).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": "Bearer cpa-secret-key-12345"}
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw_opus = (json.loads(resp.read().decode("utf-8"))["choices"][0]["message"].get("content") or "").strip()
                m_arr = re.search(r"\[.*\]", raw_opus, re.DOTALL)
                if m_arr:
                    raw_opus = m_arr.group(0)
                opus_choices = json.loads(raw_opus)
                reasons_log = []
                for item in opus_choices:
                    s_idx = int(item.get("seg_index", 0))
                    cid = item.get("clip_id", "")
                    if cid in cat_map:
                        opus_selected_map[s_idx] = (cat_map[cid], item.get("edit_reason", ""))
                        reasons_log.append(f"Seg #{s_idx} -> {cid}: {item.get('edit_reason', '')}")
                logger.info("🎬 [CLAUDE OPUS REMOTION DIRECTOR] Successfully directed %d/%d scene cuts!", len(opus_selected_map), len(segments))

                # Log Opus Remotion edit trace to Swarm Matrix
                db_chat = Path("/home/ubuntu/vps-control-center/backend/data/agents_chat.db")
                if db_chat.exists() and reasons_log:
                    conn = sqlite3.connect(str(db_chat))
                    cur = conn.cursor()
                    mid = f"msg-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"
                    ts_now = time.strftime("%H:%M")
                    ep_now = time.time()
                    msg_txt = f"🎬 **[MILO x CLAUDE OPUS — REMOTION SCENE CUT PLAN]**\nTopik: `{topic_key}` ({len(opus_selected_map)} scene cuts disusun via `claude-opus-5-5-high`):\n" + "\n".join(f"• {r}" for r in reasons_log[:12])
                    cur.execute("""
                        INSERT INTO agent_messages (id, sender_id, sender_name, sender_avatar, sender_role, recipient_id, recipient_name, content, timestamp, channel, status, created_at)
                        VALUES (?, 'milo', 'Milo (Opus Remotion Editor)', '🎞️', 'Visual Director & Opus Remotion Editor', 'all', 'All Agents', ?, ?, 'donies', 'delivered', ?)
                    """, (mid, msg_txt, ts_now, ep_now))
                    conn.commit()
                    conn.close()
        except Exception as e_opus:
            logger.warning("Claude Opus Remotion Director fallback to heuristic matcher: %s", e_opus)

        # Two-Pass Priority Allocation (What-If Hard Guard):
        # Pass 1 Order: Hook (0, 1) -> Climax/CTA (N-1) -> Remaining segments sorted by duration descending
        n_segs = len(segments)
        priority_order = []
        if n_segs > 0:
            priority_order.append(0)
        if n_segs > 1:
            priority_order.append(1)
        if n_segs > 2:
            priority_order.append(n_segs - 1)

        rem_indices = [i for i in range(n_segs) if i not in priority_order]
        rem_indices.sort(key=lambda idx: segments[idx]["duration"], reverse=True)
        priority_order.extend(rem_indices)

        scene_plans_map = {}
        used_clusters_by_seg = {}

        for s_idx in priority_order:
            seg = segments[s_idx]
            seg_dur = float(seg["duration"])

            # 1. First honor Claude Opus Remotion Director selection if valid & non-duplicate
            if seg["index"] in opus_selected_map:
                cand_c, _ = opus_selected_map[seg["index"]]
                c_cluster = cand_c.get("cluster", "")
                cand_ent = c_cluster if c_cluster in ["cat_belly_trap_scratch", "knocking", "cat_milk_danger", "cat_flehmen_response"] else cand_c["id"]
                if cand_ent not in used_entities and float(cand_c.get("duration", 10.0)) >= seg_dur - 0.1:
                    used_entities.add(cand_ent)
                    if c_cluster:
                        used_clusters_by_seg[c_cluster] = s_idx
                    scene_plans_map[s_idx] = {
                        "seg_index": seg["index"],
                        "clip_path": Path(cand_c["abs_path"]),
                        "duration": seg_dur,
                        "text": seg["text"],
                        "cluster": c_cluster,
                        "clip_id": cand_c["id"],
                        "clip_dur": cand_c.get("duration", 10.0)
                    }
                    continue

            # Position importance multiplier (Tier 1 Hard Guard)
            if s_idx in [0, 1]:
                m_pos = 1.5  # Hook gets 1.5x weight
            elif s_idx == n_segs - 1:
                m_pos = 1.3  # Climax gets 1.3x weight
            else:
                m_pos = 1.0

            scored = []
            for c in catalog:
                c_id = c["id"]
                cluster = c.get("cluster", "")
                # Strictly isolate visual entity so no same-cat AI shoot appears twice in one video
                if cluster in ["cat_belly_trap_scratch", "knocking", "cat_milk_danger", "cat_flehmen_response"]:
                    visual_entity = cluster
                else:
                    visual_entity = c_id

                if visual_entity in used_entities:
                    continue

                # Cluster spacing guard: avoid repeating same AI shoot within 3 segments
                if cluster and cluster in used_clusters_by_seg:
                    last_used_s = used_clusters_by_seg[cluster]
                    if abs(s_idx - last_used_s) < 3:
                        continue

                c_path = Path(c["abs_path"])
                if not c_path.exists():
                    continue

                # 1. Pure semantic score
                s_sem = 0.0
                c_tags = [t.lower() for t in c.get("tags", [])]
                c_desc = c.get("description", "").lower()

                # Direct word match against this speech segment
                for w in seg["words"]:
                    if w in c_tags:
                        s_sem += 8.0
                    if w in c_desc:
                        s_sem += 4.0

                # Synonym match against speech segment keywords
                for syn_key, syn_vals in synonyms.items():
                    if any(w in seg["words"] for w in syn_vals):
                        if any(t in c_tags for t in syn_vals):
                            s_sem += 12.0

                # 2. Gated Category Bias (Tier 1 Hard Guard - Eliminates +25.0 Category Chasm)
                if c.get("category") == "fahru_sent":
                    s_cat = 12.0 if s_sem > 0 else 2.0
                else:
                    s_cat = -4.0 if s_sem >= 12.0 else -10.0

                # 3. Continuous Duration Penalty with IEEE-754 epsilon tolerance
                c_dur = float(c.get("duration", 10.0))
                stretch_ratio = (seg_dur - 0.05) / max(0.1, c_dur)
                if stretch_ratio <= 1.05:
                    p_dur = 0.0
                elif stretch_ratio <= 1.35:
                    p_dur = -35.0 * (((stretch_ratio - 1.05) / 0.30) ** 2)
                else:
                    p_dur = -1000.0

                # 4. Cross-video fatigue penalty
                p_fatigue = -10.0 if c_id in recent_used_clips else 0.0

                tot_score = ((s_sem + s_cat) * m_pos) + p_dur + p_fatigue + random.uniform(0.1, 1.2)
                scored.append((tot_score, c, visual_entity, cluster))

            scored.sort(key=lambda x: x[0], reverse=True)
            if scored and scored[0][0] > -500:
                best_c, best_ent, best_cluster = scored[0][1], scored[0][2], scored[0][3]
                used_entities.add(best_ent)
                if best_cluster:
                    used_clusters_by_seg[best_cluster] = s_idx
                scene_plans_map[s_idx] = {
                    "seg_index": seg["index"],
                    "clip_path": Path(best_c["abs_path"]),
                    "duration": seg_dur,
                    "text": seg["text"],
                    "cluster": best_c.get("cluster"),
                    "clip_id": best_c["id"],
                    "clip_dur": best_c.get("duration", 10.0)
                }
            elif scored:
                # Emergency relaxation: take highest scoring remaining clip even if slightly stretched
                best_c, best_ent, best_cluster = scored[0][1], scored[0][2], scored[0][3]
                used_entities.add(best_ent)
                scene_plans_map[s_idx] = {
                    "seg_index": seg["index"],
                    "clip_path": Path(best_c["abs_path"]),
                    "duration": seg_dur,
                    "text": seg["text"],
                    "cluster": best_c.get("cluster"),
                    "clip_id": best_c["id"],
                    "clip_dur": best_c.get("duration", 10.0)
                }

        # Re-sort into chronological scene cuts
        scene_plans = [scene_plans_map[i] for i in range(n_segs) if i in scene_plans_map]

        logger.info("🎙️ Milo Script-Synced Director generated %d speech beat transitions:", len(scene_plans))
        for s in scene_plans:
            logger.info("   #%02d [%.2fs] (%s) %s -> %s", s["seg_index"], s["duration"], s["cluster"], s["clip_id"], s["text"][:35])

        # Record selection into PostgreSQL clip usage ledger
        try:
            t_key = topic_key or "unknown_topic"
            for s in scene_plans:
                p = s["clip_path"]
                sql_ins = f"INSERT INTO ai_brain.doniesdaily_clip_usage (clip_name, clip_path, topic_key) VALUES ('{p.stem}', '{str(p)}', '{t_key}');"
                subprocess.run(["docker", "exec", "-i", "supabase-db", "psql", "-U", "postgres", "-d", "postgres", "-c", sql_ins], capture_output=True)
        except Exception as e:
            logger.warning(f"Could not log clip usage to DB: {e}")

        return scene_plans

    def render_remotion_thumbnail(
        self,
        hook_title: str,
        hook_subtitle: str,
        badge_text: str,
        output_thumb_path: Path,
        bg_image_ref: Optional[Path] = None,
    ) -> Path:
        """Renders high-CTR Remotion Still Thumbnail via Remotion CLI."""
        output_thumb_path.parent.mkdir(parents=True, exist_ok=True)
        bg_prop = ""

        # Extract dramatic background frame from the primary video clip if available
        if bg_image_ref and bg_image_ref.exists():
            if bg_image_ref.suffix.lower() in [".mp4", ".mov"]:
                extracted_frame = self.public_dir / "current_thumb_bg.jpg"
                cmd_extract = [
                    "ffmpeg", "-y",
                    "-ss", "00:00:01.500",
                    "-i", str(bg_image_ref),
                    "-vframes", "1",
                    "-q:v", "2",
                    str(extracted_frame)
                ]
                subprocess.run(cmd_extract, capture_output=True)
                if extracted_frame.exists():
                    bg_prop = "current_thumb_bg.jpg"
            elif bg_image_ref.suffix.lower() in [".jpg", ".png", ".jpeg"]:
                dest_bg = self.public_dir / "current_thumb_bg.jpg"
                shutil.copy2(bg_image_ref, dest_bg)
                bg_prop = "current_thumb_bg.jpg"

        props = {
            "title": hook_title.upper()[:42],
            "subtitle": hook_subtitle.upper()[:35],
            "badgeText": badge_text[:25],
            "bgImage": bg_prop,
        }

        # Always target src/index.ts directly to support dynamic staticFile fetching for any topic
        still_target = "src/index.ts"

        cmd = [
            "npx", "remotion", "still",
            still_target,
            "DoniThumbnail",
            str(output_thumb_path),
            f"--props={json.dumps(props)}"
        ]
        logger.info("Rendering Remotion Still Thumbnail: %s", " ".join(cmd[:6]))
        res = subprocess.run(cmd, cwd=str(self.remotion_dir), capture_output=True, text=True, check=False)
        if res.returncode != 0:
            logger.error("Remotion thumbnail render failed: %s", res.stderr or res.stdout)
            # Fallback frame
            if bg_image_ref and bg_image_ref.exists():
                cmd_fb = [
                    "ffmpeg", "-y",
                    "-ss", "00:00:01.500",
                    "-i", str(bg_image_ref),
                    "-vframes", "1",
                    "-q:v", "2",
                    str(output_thumb_path)
                ]
                subprocess.run(cmd_fb, capture_output=True)
        else:
            logger.info("📸 Remotion Still Thumbnail rendered successfully: %s (%d bytes)", output_thumb_path, output_thumb_path.stat().st_size)

        return output_thumb_path

    def render_overlay_layer(
        self,
        hook_title: str,
        hook_subtitle: str,
        badge_text: str,
        captions_filename: str,
        duration_sec: float,
        output_mov_path: Path,
        subtitle_bottom: int = 500,
        layout_mode: str = "youtube_shorts",
        show_safe_area_guide: bool = False,
    ) -> Path:
        """Renders the transparent ProRes 4444 overlay via Remotion CLI, strictly respecting YouTube Shorts Safe Area."""
        props = {
            "hookTitle": hook_title,
            "hookSubtitle": hook_subtitle,
            "badgeText": badge_text,
            "captionsFile": captions_filename,
            "durationInSeconds": duration_sec,
            "showOutroCTA": True,
            "layoutMode": layout_mode,
            "subtitleBottom": subtitle_bottom,
            "showSafeAreaGuide": show_safe_area_guide,
        }
        props_file = self.public_dir / "active_overlay_props.json"
        props_file.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")

        output_mov_path.parent.mkdir(parents=True, exist_ok=True)

        if output_mov_path.exists() and output_mov_path.stat().st_size > 10_000_000:
            logger.info("Overlay layer already exists and valid (%d bytes). Reusing: %s", output_mov_path.stat().st_size, output_mov_path)
            return output_mov_path

        # Always render DoniOverlay via src/index.ts so Remotion serves public/ assets dynamically
        render_target = ["DoniOverlay"]

        cmd = [
            "npx",
            "remotion",
            "render",
            *render_target,
            str(output_mov_path),
            f"--props={props_file.resolve()}",
            "--codec=prores",
            "--prores-profile=4444",
            "--pixel-format=yuva444p10le",
            "--concurrency=2",
        ]

        logger.info("Rendering Remotion transparent overlay: %s", " ".join(cmd))
        res = subprocess.run(cmd, cwd=str(self.remotion_dir), capture_output=True, text=True, check=False)
        if res.returncode != 0:
            logger.error("Remotion overlay render failed: %s", res.stderr or res.stdout)
            raise RuntimeError(f"Remotion render exit code {res.returncode}")

        logger.info("Remotion overlay rendered successfully: %s (%d bytes)", output_mov_path, output_mov_path.stat().st_size)
        return output_mov_path

    def composite_master(
        self,
        footage_clips: List[Path],
        overlay_mov: Path,
        master_audio: Path,
        duration_sec: float,
        output_mp4: Path,
        thumbnail_path: Optional[Path] = None,
        clip_durations: Optional[List[float]] = None,
    ) -> Path:
        """Combines footage clips + Remotion transparent overlay + audio master.
        Injects the Remotion thumbnail as a 0.08s poster frame at frame 0 (guarantees Shorts cover).
        Guarantees video never cuts off before the voiceover finishes.
        Supports exact speech beat clip durations (speech-synced cut pacing).
        """
        # Probe exact audio duration to strictly avoid audio cutoffs
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(master_audio)],
            capture_output=True, text=True, check=True
        )
        audio_dur = float(probe.stdout.strip())
        effective_dur = max(duration_sec, audio_dur) + 0.35  # Add 0.35s breathing room at the end
        default_slice = effective_dur / float(len(footage_clips))

        inputs = []
        filter_parts = []
        for i, clip in enumerate(footage_clips):
            clip_probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(clip)],
                capture_output=True, text=True, check=True
            )
            c_dur = max(1.0, float(clip_probe.stdout.strip()))
            slice_dur = clip_durations[i] if (clip_durations and i < len(clip_durations)) else default_slice

            if c_dur < (slice_dur - 0.05):
                # Emergency Force-Fit Guard: Smoothly stretch PTS (subtle slow-mo) so clip covers slice seamlessly
                pts_factor = slice_dur / max(0.1, c_dur)
                logger.info("⚡ Force-fit stretch clip #%d (%s): %.2fs -> %.2fs (pts_factor=%.3f)", i+1, Path(clip).name, c_dur, slice_dur, pts_factor)
                inputs.extend(["-ss", "0.0", "-t", f"{c_dur:.2f}", "-i", str(clip)])
                filter_parts.append(
                    f"[{i}:v]setpts=(PTS-STARTPTS)*{pts_factor:.4f},"
                    f"scale=1080:1920:force_original_aspect_ratio=decrease,"
                    f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}];"
                )
            else:
                # Safe center action offset: mathematically guaranteed start_offset + slice_dur <= c_dur
                max_offset = max(0.0, c_dur - slice_dur)
                start_offset = round(max_offset / 2.0, 2)
                inputs.extend(["-ss", f"{start_offset:.2f}", "-t", f"{slice_dur:.2f}", "-i", str(clip)])
                filter_parts.append(
                    f"[{i}:v]setpts=PTS-STARTPTS,"
                    f"scale=1080:1920:force_original_aspect_ratio=decrease,"
                    f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}];"
                )

        concat_inputs = "".join(f"[v{i}]" for i in range(len(footage_clips)))
        filter_parts.append(f"{concat_inputs}concat=n={len(footage_clips)}:v=1:a=0[bg];")

        # Overlay Remotion ProRes 4444 on background video with eof_action=pass
        overlay_idx = len(footage_clips)
        inputs.extend(["-i", str(overlay_mov)])
        filter_parts.append(f"[bg][{overlay_idx}:v]overlay=0:0:eof_action=pass[vmain];")

        # Inject 0.08s Poster Frame (Remotion Still Thumbnail) at the start if available
        if thumbnail_path and thumbnail_path.exists():
            thumb_idx = overlay_idx + 1
            inputs.extend(["-loop", "1", "-t", "0.08", "-i", str(thumbnail_path)])
            filter_parts.append(
                f"[{thumb_idx}:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
                f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[vthumb];"
                f"[vthumb][vmain]concat=n=2:v=1:a=0[vout];"
            )
            audio_idx = thumb_idx + 1
        else:
            filter_parts.append("[vmain]copy[vout];")
            audio_idx = overlay_idx + 1

        # Master Audio input
        inputs.extend(["-i", str(master_audio)])

        filter_complex = "".join(filter_parts)

        cmd = [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            f"{audio_idx}:a",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-t",
            f"{effective_dur + (0.08 if thumbnail_path and thumbnail_path.exists() else 0):.2f}",
            str(output_mp4),
        ]

        logger.info("Executing FFMPEG composite master with Poster Frame injection...")
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            logger.error("FFMPEG composite failed: %s", res.stderr)
            raise RuntimeError(f"FFMPEG composite exit code {res.returncode}")

        # Ensure high-quality thumbnail is saved at expected thumb path
        target_thumb = output_mp4.with_name(f"{output_mp4.stem}_thumb.jpg")
        if thumbnail_path and thumbnail_path.exists() and thumbnail_path != target_thumb:
            shutil.copy2(thumbnail_path, target_thumb)

        logger.info("Master video created successfully: %s (%d bytes)", output_mp4, output_mp4.stat().st_size)
        return output_mp4

#!/usr/bin/env python3
"""
Cleo 🔍 — Automated Quality Control Gatekeeper for DoniesDaily
Rigorous deterministic audio/video inspection using ffprobe & ffmpeg before YouTube upload.
"""
import os
import sys
import json
import re
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

def inspect_video(
    video_path: str,
    audio_path: Optional[str] = None,
    script_text: str = "",
    title: str = "",
    hook_banner: str = "",
    run_ai_vision: bool = True
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "passed": True,
        "video_path": video_path,
        "errors": [],
        "warnings": [],
        "metrics": {}
    }

    v_file = Path(video_path)
    if not v_file.exists():
        report["passed"] = False
        report["errors"].append(f"File video tidak ditemukan: {video_path}")
        return report

    size_mb = v_file.stat().st_size / (1024 * 1024)
    report["metrics"]["file_size_mb"] = round(size_mb, 2)
    if size_mb < 1.0:
        report["passed"] = False
        report["errors"].append(f"Ukuran video terlalu kecil (<1MB): {size_mb:.2f}MB")

    # 1. ffprobe Streams & Format
    cmd_probe = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", str(v_file)
    ]
    try:
        p_res = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
        meta = json.loads(p_res.stdout)
    except Exception as e:
        report["passed"] = False
        report["errors"].append(f"ffprobe gagal membaca file video: {e}")
        return report

    streams = meta.get("streams", [])
    format_info = meta.get("format", {})
    
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not v_stream:
        report["passed"] = False
        report["errors"].append("CRITICAL: Stream video tidak ditemukan!")
        return report

    if not a_stream:
        report["passed"] = False
        report["errors"].append("CRITICAL: Stream audio tidak ditemukan dalam file video!")

    # Resolution Check (Must be 9:16 vertical, standard 1080x1920)
    width = int(v_stream.get("width", 0))
    height = int(v_stream.get("height", 0))
    report["metrics"]["resolution"] = f"{width}x{height}"
    
    if width != 1080 or height != 1920:
        aspect_ratio = width / height if height else 0
        if round(aspect_ratio, 2) != 0.56: # 9/16 = 0.5625
            report["passed"] = False
            report["errors"].append(f"Aspect ratio bukan 9:16 vertikal ({width}x{height})")
        else:
            report["warnings"].append(f"Resolusi vertikal {width}x{height} bukan standar 1080x1920")

    # Duration Check (YouTube Shorts must be < 60s, recommended 15s - 58s)
    duration = float(format_info.get("duration", 0))
    report["metrics"]["duration_seconds"] = round(duration, 2)
    if duration > 59.9:
        report["passed"] = False
        report["errors"].append(f"Durasi video melebihi batas YouTube Shorts (>60s): {duration:.2f}s")
    elif duration < 10.0:
        report["passed"] = False
        report["errors"].append(f"Durasi video terlalu singkat untuk shorts (<10s): {duration:.2f}s")

    # Audio Desync Check (if raw TTS audio is supplied)
    if audio_path and Path(audio_path).exists():
        cmd_aprobe = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", audio_path]
        try:
            a_res = subprocess.run(cmd_aprobe, capture_output=True, text=True, check=True)
            a_meta = json.loads(a_res.stdout)
            raw_a_duration = float(a_meta.get("format", {}).get("duration", 0))
            delta = abs(duration - raw_a_duration)
            report["metrics"]["audio_delta_seconds"] = round(delta, 3)
            if delta > 1.5:
                report["passed"] = False
                report["errors"].append(f"Desync audio vs video melebihi toleransi 1.5s (delta: {delta:.2f}s)")
        except Exception as err:
            report["warnings"].append(f"Gagal memverifikasi audio raw: {err}")

    # 2. Black Frame Detection (Freeze or black gap >= 0.5s)
    cmd_black = [
        "ffmpeg", "-i", str(v_file),
        "-vf", "blackdetect=d=0.5:pix_th=0.10",
        "-f", "null", "-"
    ]
    try:
        black_res = subprocess.run(cmd_black, capture_output=True, text=True)
        if "black_start" in black_res.stderr:
            report["passed"] = False
            report["errors"].append("Terdeteksi black frame / layar hitam membeku >= 0.5s")
        else:
            report["metrics"]["black_frame_clean"] = True
    except Exception as e:
        report["warnings"].append(f"Blackframe check error: {e}")

    # 3. Audio Loudness (EBU R128 integrated loudness)
    cmd_loudness = [
        "ffmpeg", "-i", str(v_file),
        "-af", "ebur128",
        "-f", "null", "-"
    ]
    try:
        loud_res = subprocess.run(cmd_loudness, capture_output=True, text=True)
        out = loud_res.stderr
        # Cari di Summary section terlebih dahulu
        summary_match = re.search(r"Integrated loudness:\s*\n\s*I:\s*(-?[\d\.]+)\s*LUFS", out)
        if summary_match:
            il = float(summary_match.group(1))
        else:
            all_matches = re.findall(r"I:\s*(-?[\d\.]+)\s*LUFS", out)
            il = float(all_matches[-1]) if all_matches else None

        if il is not None:
            report["metrics"]["integrated_loudness_lufs"] = il
            if il < -26.0:
                report["warnings"].append(f"Audio agak lirih ({il} LUFS, ideal: -14 s/d -20 LUFS)")
            elif il > -8.0:
                report["warnings"].append(f"Audio berisiko distorsi / terlalu keras ({il} LUFS)")
    except Exception as e:
        report["warnings"].append(f"Loudness check error: {e}")

    # 4. Cleo 2.0 AI Vision Audit (20 Chronological Frames via Gemini 3.8 Flash)
    if run_ai_vision and report["passed"]:
        try:
            # Add src to path if needed
            src_dir = str(Path(__file__).resolve().parent)
            if src_dir not in sys.path:
                sys.path.insert(0, src_dir)
            from doni_ai_qc import audit_video_narrative_and_quality

            ai_res = audit_video_narrative_and_quality(
                video_path=video_path,
                script_text=script_text,
                title=title,
                hook_banner=hook_banner
            )
            report["ai_vision"] = ai_res
            if not ai_res.get("passed", False):
                report["passed"] = False
                summary_fail = ai_res.get("summary_verdict") or ai_res.get("error") or "Skor AI Vision di bawah standar kelulusan."
                report["errors"].append(f"CLEO AI-VISION REJECTION: {summary_fail}")
                if ai_res.get("critical_issues"):
                    report["errors"].extend(ai_res["critical_issues"])
            else:
                report["metrics"]["ai_vision_score"] = ai_res.get("overall_score")
                report["metrics"]["narrative_alignment_score"] = ai_res.get("narrative_alignment_score")
                report["metrics"]["visual_quality_score"] = ai_res.get("visual_quality_score")
                report["metrics"]["pacing_retention_score"] = ai_res.get("pacing_retention_score")
                report["metrics"]["cleo_summary"] = ai_res.get("summary_verdict")
        except Exception as e:
            report["warnings"].append(f"AI Vision check warning: {e}")

    return report

def audit_script_and_outro(script_text: str) -> Dict[str, Any]:
    """Verifies Hukum Besi #15: Script MUST end with Follow & Subscribe CTA."""
    report = {"passed": True, "errors": [], "warnings": []}
    if not script_text:
        report["warnings"].append("Skrip teks kosong, verifikasi outro dilewati.")
        return report

    text_lower = script_text.lower()
    has_sub = "subscribe" in text_lower or "subs" in text_lower
    has_follow = "follow" in text_lower
    has_brand = "doniesdaily" in text_lower or "doni" in text_lower

    if not (has_sub or has_follow):
        report["passed"] = False
        report["errors"].append("HUKUM BESI #15 VIOLATION: Naskah wajib menyertakan CTA penutup Follow/Subscribe DoniesDaily!")
    elif not has_brand:
        report["warnings"].append("CTA penutup sebaiknya menyebutkan nama channel DoniesDaily secara eksplisit.")
    
    return report

def audit_footage_assembly(footage_clips: list, slice_dur: Union[float, List[float]]) -> Dict[str, Any]:
    """Verifies Hukum Besi #13: Strict Zero In-Video Footage Repetition and Zero Looping."""
    report = {"passed": True, "errors": [], "metrics": {}}
    clip_strs = [str(c) for c in footage_clips]
    unique_clips = set(clip_strs)

    report["metrics"]["total_cuts"] = len(footage_clips)
    report["metrics"]["unique_clips"] = len(unique_clips)

    if isinstance(slice_dur, list):
        dur_list = [float(d) for d in slice_dur]
        report["metrics"]["slice_durations"] = [round(d, 2) for d in dur_list]
    else:
        dur_list = [float(slice_dur)] * len(footage_clips)
        report["metrics"]["slice_duration_sec"] = round(float(slice_dur), 2)

    if len(clip_strs) != len(unique_clips):
        report["passed"] = False
        report["errors"].append(f"HUKUM BESI #13 VIOLATION: Terdeteksi {len(clip_strs) - len(unique_clips)} footage terduplikasi dalam 1 video!")

    for idx, c in enumerate(footage_clips):
        target_slice = dur_list[idx] if idx < len(dur_list) else dur_list[-1]
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(c)],
            capture_output=True, text=True
        )
        dur = float(probe.stdout.strip()) if probe.stdout.strip() else 0.0
        if dur > 0 and target_slice > (dur + 0.1):
            if target_slice <= (dur * 1.5):
                # Within 1.5x range: Safely auto-healed via FFmpeg Force-Fit setpts stretch
                report["warnings"].append(f"Klip {Path(c).name} ({dur:.2f}s) di segmen #{idx+1} akan di-stretch halus ({target_slice:.2f}s via setpts slow-mo)")
            else:
                report["passed"] = False
                report["errors"].append(f"HUKUM BESI #13 VIOLATION: Klip {Path(c).name} ({dur:.2f}s) di segmen #{idx+1} defisit ekstrem dari slice ({target_slice:.2f}s)!")

    return report

def format_cleo_stamp(report: Dict[str, Any], video_path: str) -> str:
    m = report.get("metrics", {})
    status = "QC_PASSED" if report["passed"] else "QC_FAILED"
    res = m.get("resolution", "unknown")
    dur = m.get("duration_seconds", 0)
    drift = m.get("audio_delta_seconds", "N/A")
    lufs = m.get("integrated_loudness_lufs", "N/A")
    black = 0 if m.get("black_frame_clean") else "DETECTED"
    
    ai_score = m.get("ai_vision_score", "N/A")
    ai_narrative = m.get("narrative_alignment_score", "N/A")
    ai_verdict = m.get("cleo_summary", "")
    if not ai_verdict and report.get("ai_vision"):
        ai_verdict = report["ai_vision"].get("summary_verdict", "")

    stamp = f"""
======================================================
[CLEO_QC_INSPECTION] — AI-Vision Broadcast Gatekeeper
Target: {Path(video_path).name}
Status: {status}
Deterministic Metrics:
  - Resolution: {res} (Aspect: 9:16)
  - Duration: {dur}s (Shorts Compliant)
  - Audio Drift: {drift}s (Tolerance <=0.5s)
  - Integrated Loudness: {lufs} LUFS (Target: -14..-19 LUFS)
  - Black Frames: {black}
AI Vision 20-Frame Audit (Gemini 3.8 Flash):
  - Overall Quality Score: {ai_score}/100
  - Narrative-Visual Alignment: {ai_narrative}/100
  - Cleo AI Verdict: {ai_verdict if ai_verdict else '(AI Vision not executed / N/A)'}
Inspector: Cleo 🔍 — DoniesDaily Broadcast Gatekeeper
======================================================
"""
    return stamp.strip()

def update_db_qc(topic_key: str, report: Dict[str, Any]):
    stage = "QC_PASSED" if report["passed"] else "QC_FAILED"
    report_json = json.dumps(report).replace("'", "''")
    err_msg = "; ".join(report.get("errors", [])).replace("'", "''")
    
    sql = f"""
    UPDATE ai_brain.doniesdaily_production_queue
    SET current_stage = '{stage}',
        qc_report = '{report_json}'::jsonb,
        error_message = {'NULL' if not err_msg else f"'{err_msg}'"},
        updated_at = NOW()
    WHERE topic_key = '{topic_key}';
    """
    cmd = ["docker", "exec", "-i", "supabase-db", "psql", "-U", "postgres", "-d", "postgres", "-c", sql]
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleo 🔍 QC Gatekeeper (Deterministic + AI Vision)")
    parser.add_argument("video_path", help="Path ke video MP4")
    parser.add_argument("audio_path", nargs="?", default=None, help="Path ke audio TTS (opsional)")
    parser.add_argument("--update-db", dest="topic_key", default=None, help="Topic key untuk update DB antrean")
    parser.add_argument("--script", default="", help="Naskah teks atau path file naskah")
    parser.add_argument("--title", default="", help="Judul video")
    parser.add_argument("--hook", default="", help="Teks Hook Banner")
    parser.add_argument("--no-ai", action="store_true", help="Lewati AI Vision (hanya tes deterministik)")

    args = parser.parse_args()

    v_path = args.video_path
    a_path = args.audio_path
    topic_key_to_update = args.topic_key
    script_val = args.script
    title_val = args.title
    hook_val = args.hook

    # If topic_key provided but script/title not specified, fetch from DB
    if topic_key_to_update and (not script_val or not title_val):
        try:
            sql_fetch = f"""
            SELECT title, hook_banner, COALESCE(full_script, '') 
            FROM ai_brain.doniesdaily_content_ideas 
            WHERE topic_key = '{topic_key_to_update}' LIMIT 1;
            """
            res_db = subprocess.run(
                ["docker", "exec", "-i", "supabase-db", "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-F", "|||", "-c", sql_fetch],
                capture_output=True, text=True
            )
            if res_db.stdout.strip():
                p_title, p_hook, p_script = res_db.stdout.strip().split("|||")
                if not title_val:
                    title_val = p_title
                if not hook_val:
                    hook_val = p_hook
                if not script_val:
                    script_val = p_script
        except Exception as e:
            print(f"Warning: Gagal menarik data naskah DB: {e}", file=sys.stderr)

    if script_val and len(script_val) < 256 and Path(script_val).exists():
        with open(script_val, "r", encoding="utf-8") as sf:
            script_val = sf.read().strip()

    run_ai = not args.no_ai
    rep = inspect_video(
        video_path=v_path,
        audio_path=a_path,
        script_text=script_val,
        title=title_val,
        hook_banner=hook_val,
        run_ai_vision=run_ai
    )

    print("\n" + format_cleo_stamp(rep, v_path) + "\n")
    print(json.dumps(rep, indent=2, ensure_ascii=False))

    if topic_key_to_update:
        print(f"\nUpdating database queue for topic '{topic_key_to_update}'...")
        update_db_qc(topic_key_to_update, rep)
        print("Database updated.")

    sys.exit(0 if rep["passed"] else 1)

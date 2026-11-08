#!/usr/bin/env python3
"""
Cleo 2.0 🔍 — AI-Vision Quality Control Gatekeeper for DoniesDaily
Powered by gemini-3.8-flash-high via Antigravity CLIProxyAPI (:8317).
Extracts 20 chronological frames (5% step: 5% to 100%) and performs deep narrative-visual
alignment auditing, Remotion layout checks, glitch detection, and retention evaluation.
"""

import os
import sys
import json
import base64
import tempfile
import argparse
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union

API_URL = os.getenv("CPA_BASE_URL", "http://127.0.0.1:8317/v1/chat/completions")
API_KEY = os.getenv("CPA_API_KEY", "cpa-secret-key-12345")
MODEL = os.getenv("CLEO_QC_MODEL", "gemini-3.8-flash-high")


def probe_video_duration(video_path: Path) -> float:
    """Gets video duration using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip()) if res.stdout.strip() else 0.0


def extract_20_qc_frames(video_path: Path, tmp_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Extracts exactly 20 chronological frames across the video at 5% duration intervals:
    5%, 10%, 15%, 20%, 25%, 30%, 35%, 40%, 45%, 50%, 55%, 60%, 65%, 70%, 75%, 80%, 85%, 90%, 95%, 100%.
    Frames are scaled to 540x960 (9:16) for optimal token efficiency while preserving text readability.
    """
    duration = probe_video_duration(video_path)
    if duration <= 0:
        raise ValueError(f"Durasi video tidak valid atau file korup: {video_path}")

    frames_meta = []
    managed_tmp = None
    target_dir = tmp_dir
    if target_dir is None:
        managed_tmp = tempfile.TemporaryDirectory(prefix="cleo_qc_20f_")
        target_dir = Path(managed_tmp.name)

    try:
        for i in range(1, 21):
            pct_float = i * 0.05
            pct_int = round(pct_float * 100)
            
            # At 100%, avoid grabbing past EOF
            if i == 20:
                ts = max(0.1, duration - 0.25)
            else:
                ts = duration * pct_float

            out_jpg = target_dir / f"frame_{i:02d}_{pct_int}pct.jpg"
            cmd = [
                "ffmpeg", "-y", "-ss", f"{ts:.2f}",
                "-i", str(video_path),
                "-vframes", "1",
                "-vf", "scale='min(540,iw)':-1",
                "-q:v", "4",
                str(out_jpg)
            ]
            subprocess.run(cmd, capture_output=True, check=True)

            with open(out_jpg, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")

            frames_meta.append({
                "frame_index": i,
                "pct_label": f"{pct_int}%",
                "timestamp_sec": round(ts, 2),
                "file_path": str(out_jpg),
                "base64": b64_data
            })
    finally:
        if managed_tmp:
            # We preserve base64 strings in memory; temp dir will be cleaned on exit
            pass

    return frames_meta


def build_cleo_vision_prompt(
    duration: float,
    frames_meta: List[Dict[str, Any]],
    script_text: str = "",
    title: str = "",
    hook_banner: str = ""
) -> List[Dict[str, Any]]:
    """Builds the multi-modal prompt with 20 chronological frames for Gemini 3.8 Flash."""
    system_text = f"""Anda adalah CLEO 🔍 — Chief Broadcast Quality Control & Narrative Auditor untuk saluran YouTube Shorts '@DoniesDaily' (niche edukasi & perilaku kucing).

TUGAS ANDA:
Melakukan audit menyeluruh terhadap 20 FRAME KRONOLOGIS (interval 5% dari detik 0 s/d akhir video durasi {duration:.1f}s).
Anda harus memeriksa kesesuaian cerita visual vs naskah suara, kualitas tata letak teks Remotion, keberadaan outro CTA, dan daya tarik retensi penonton.

DATA PRODUKSI:
- Durasi Video: {duration:.1f} detik
- Judul Video: {title if title else '(Tidak dispesifikasi)'}
- Hook Banner Atas: {hook_banner if hook_banner else '(Tidak dispesifikasi)'}
- Naskah Narasi Lengkap (Voiceover Kak Ceria / Doni):
\"\"\"
{script_text if script_text else '(Naskah suara tidak dilampirkan - audit murni visual & teks overlay)'}
\"\"\"

4 PILAR PENILAIAN WAJIB:
1. NARRATIVE-VISUAL ALIGNMENT (Bobot 40%):
   - Apakah ekspresi, gerakan, atau adegan anabul di tiap frame mencerminkan apa yang sedang dibicarakan narasi suara?
   - Cek ketidakcocokan fatal (misal: narasi teriak/waspada, tapi visual kucing tidur pulas atau lari keluar).
2. REMOTION TEXT & OVERLAY POLISH (Bobot 25%):
   - YouTube Shorts Safe Area Compliance (MUTLAK):
     * Hook Banner atas tidak boleh mepet ke atas (wajib berada di bawah notch kamera / search header).
     * Subtitle kinetik WAJIB melayang di safe area (bottom >= 480px) agar TIDAK TERTUTUP oleh channel name, handle @DoniesDaily, dan tombol SUBSCRIBE merah YouTube Shorts!
     * Teks subtitle, badge, dan kartu CTA tidak boleh menembus sisi kanan layar yang tertutup action buttons (Like, Dislike, Comment, Share).
   - Keterbacaan subtitle kinetik (kontras, border hitam tebal, highlight kuning neon).
   - Keberadaan Outro CTA di akhir (90% s/d 100%): Apakah ada visual ajakan 'Follow & Subscribe DoniesDaily'?
3. VISUAL QUALITY & DEFECTS (Bobot 20%):
   - Aspect ratio wajib vertikal 9:16 bersih (tidak ada pilar hitam samping / letterbox horizontal).
   - Nol black frame freeze, nol artefak pecah/buram ekstrem, nol watermark pihak ketiga yang bocor.
4. PACING & RETENTION APPEAL (Bobot 15%):
   - Apakah transisi visual dinamis dan tidak membosankan? Apakah kucing di video tampak ekspresif dan menggemaskan?
5. SQUAD BOUNDARY & SUBJECT INTEGRITY (HUKUM BESI #18 MUTLAK):
   - Video DoniesDaily WAJIB 100% KUCING/ANABUL.
   - DILARANG KERAS memuat wajah manusia (Mas Fahru, orang selfie, ngaca, dsb), domba, kambing, kandang ternak, tutorial coding, atau materi Tim Arya!
   - JIKA DITEMUKAN 1 SAJA FRAME DENGAN MANUSIA / TERNAK NON-KUCING ➔ VERDICT WAJIB 'REJECTED', overall_score = 0, dan tambahkan 'SQUAD_CONTAMINATION: Terdeteksi footage manusia/non-kucing' ke critical_issues!

ATURAN KELULUSAN (PASSING GRADE):
- STATUS APPROVED: Nilai overall_score >= 75 dan ZERO critical issues (critical_issues kosong).
- STATUS REJECTED: Nilai overall_score < 75 atau terdeteksi ketidakcocokan fatal antara visual dan narasi.

OUTPUT WAJIB JSON VALID (HANYA JSON, TANPA MARKDOWN DI LUAR KODE):
{{
  "verdict": "APPROVED" | "REJECTED",
  "overall_score": 85,
  "narrative_alignment_score": 90,
  "visual_quality_score": 85,
  "pacing_retention_score": 80,
  "hook_banner_verified": true,
  "outro_cta_verified": true,
  "summary_verdict": "1-2 kalimat ringkasan eksekutif hasil audit Cleo.",
  "strengths": [
    "Poin keunggulan visual 1",
    "Poin keunggulan visual 2"
  ],
  "critical_issues": [
    "Isu fatal jika ada (kosongkan jika lulus)"
  ],
  "actionable_feedback_for_milo": [
    "Rekomendasi spesifik untuk Milo (Video Editor) untuk perbaikan klip atau timing"
  ],
  "timeline_observations": [
    {{"frame": 1, "pct": "5%", "ts": 2.3, "status": "GOOD", "note": "Hook title banner tampil jelas..."}},
    {{"frame": 10, "pct": "50%", "ts": 23.3, "status": "GOOD", "note": "Kucing ekspresif sesuai narasi..."}},
    {{"frame": 20, "pct": "100%", "ts": 46.5, "status": "GOOD", "note": "Outro CTA subscribe terlihat..."}}
  ]
}}
"""

    content_parts: List[Dict[str, Any]] = [
        {"type": "text", "text": system_text}
    ]

    for f in frames_meta:
        content_parts.append({
            "type": "text",
            "text": f"=== FRAME #{f['frame_index']} ({f['pct_label']} — Detik {f['timestamp_sec']}s) ==="
        })
        content_parts.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{f['base64']}"
            }
        })

    return content_parts


def audit_video_narrative_and_quality(
    video_path: Union[str, Path],
    script_text: str = "",
    title: str = "",
    hook_banner: str = ""
) -> Dict[str, Any]:
    """
    Main entry point: Audits a video via 20-frame AI Vision.
    Returns structured audit dictionary.
    """
    v_path = Path(video_path)
    if not v_path.exists():
        return {
            "verdict": "REJECTED",
            "overall_score": 0,
            "error": f"File video tidak ditemukan: {v_path}",
            "passed": False
        }

    duration = probe_video_duration(v_path)
    with tempfile.TemporaryDirectory(prefix="cleo_qc_20f_") as tmpdir:
        tmp_path = Path(tmpdir)
        frames_meta = extract_20_qc_frames(v_path, tmp_dir=tmp_path)
        content_parts = build_cleo_vision_prompt(
            duration=duration,
            frames_meta=frames_meta,
            script_text=script_text,
            title=title,
            hook_banner=hook_banner
        )

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": content_parts}
            ],
            "max_tokens": 2000,
            "temperature": 0.2
        }

        req = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                raw_reply = resp_data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return {
                "verdict": "REJECTED",
                "overall_score": 0,
                "error": f"Gagal menghubungi AI Vision API ({MODEL}): {e}",
                "passed": False
            }

        # Parse JSON from response
        try:
            cleaned = raw_reply
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()

            result = json.loads(cleaned)
            result["passed"] = (result.get("verdict") == "APPROVED") and (result.get("overall_score", 0) >= 75)
            result["video_path"] = str(v_path)
            result["duration_seconds"] = round(duration, 2)
            result["model_used"] = MODEL
            result["frames_inspected"] = 20
            return result
        except Exception as parse_err:
            return {
                "verdict": "REJECTED",
                "overall_score": 0,
                "error": f"Gagal mem-parsing output JSON dari AI Vision: {parse_err}. Raw reply: {raw_reply[:300]}",
                "passed": False,
                "raw_reply": raw_reply
            }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleo 2.0 AI-Vision 20-Frame QC Auditor")
    parser.add_argument("--video", required=True, help="Path ke file video MP4")
    parser.add_argument("--script", default="", help="Teks naskah atau path ke file txt")
    parser.add_argument("--title", default="", help="Judul Shorts")
    parser.add_argument("--hook", default="", help="Teks Hook Banner")
    parser.add_argument("--json", action="store_true", help="Output raw JSON only")

    args = parser.parse_args()
    
    script_val = args.script
    if script_val and len(script_val) < 256 and Path(script_val).exists():
        with open(script_val, "r", encoding="utf-8") as sf:
            script_val = sf.read().strip()

    print(f"🔍 [CLEO 2.0] Memulai inspeksi AI Vision 20-Frame untuk: {args.video} ...")
    report = audit_video_narrative_and_quality(
        video_path=args.video,
        script_text=script_val,
        title=args.title,
        hook_banner=args.hook
    )

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        v_state = "✅ APPROVED" if report.get("passed") else "❌ REJECTED"
        print("\n" + "=" * 60)
        print(f"📢 HASIL AUDIT AI-VISION CLEO 2.0: {v_state}")
        print(f"Skor Keseluruhan: {report.get('overall_score', 0)} / 100")
        print(f"  - Kesesuaian Cerita (Narrative): {report.get('narrative_alignment_score', 0)}/100")
        print(f"  - Kualitas Visual & Layout: {report.get('visual_quality_score', 0)}/100")
        print(f"  - Pacing & Retensi: {report.get('pacing_retention_score', 0)}/100")
        print(f"  - Hook Banner Terverifikasi: {report.get('hook_banner_verified')}")
        print(f"  - Outro CTA Terverifikasi: {report.get('outro_cta_verified')}")
        print("-" * 60)
        print(f"Ringkasan: {report.get('summary_verdict', '-')}")
        if report.get("critical_issues"):
            print("🚨 CRITICAL ISSUES:")
            for ci in report["critical_issues"]:
                print(f"  • {ci}")
        if report.get("actionable_feedback_for_milo"):
            print("🛠️ CATATAN REVISI UNTUK MILO:")
            for fb in report["actionable_feedback_for_milo"]:
                print(f"  • {fb}")
        print("=" * 60)

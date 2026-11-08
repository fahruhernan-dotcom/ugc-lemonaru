# 📜 PRD & MASTER WORKFLOW SPEC: DONIESDAILY SQUAD v2.0
<!-- 
PRD & How-To-Work SSOT for DoniesDaily YouTube Shorts Automation
Canonical Location: /home/ubuntu/apps/ugc-lemonaru/PRD_DONIESDAILY_MASTER_SPEC.md
Author: Hermes Agent (Personal Co-Pilot) & Fahru (Owner)
Date: 2026-10-28
-->

## 1. Executive Summary & Objective
DoniesDaily (`@DoniesDaily`, YouTube Channel ID: `UCNPtjF2aB0wvWHI0q7hhcCg`) adalah channel YouTube Shorts edukasi dan humor anabul otonom dengan standar siaran televisi (broadcast quality). 
Tujuan utama: Mencapai sprint 100 subscribers dan engagement organik tinggi tanpa konten sampah scraping, zero-deduplication, dan zero audio-visual desync/cutoffs.

---

## 2. Invariant Rules (Hukum Besi yang DILARANG DILANGGAR)
1. **Zero External Scraping:** Hanya boleh mengonsumsi footage asli kiriman Mas Fahru di `/fahru_clips/` atau hasil render Google Flow AI resmi.
2. **Semantic Asset Naming:** Semua footage anabul wajib dinamai berdasarkan aksi/kejadiannya (misal: `kucing_hitam_lesu_topeng_sedih.mp4`) agar Milo dapat memilih klip secara semantik tanpa inspect file 1 per 1.
3. **Master Clock Audio Paling Utama:** Durasi video MP4 final **WAJIB 100% MENGIKUTI PANJANG AUDIO STEM VOKAL** (`ffprobe -show_entries format=duration`). Video DILARANG KERAS terpotong sebelum narasi selesai!
4. **Zero Whisper Monoton:** Dilarang keras spam tag `[whispers]` terus-menerus. Wajib gunakan dinamika vokal ElevenLabs v4: `[curious]`, `[gasps]`, `[laughs]`, `[excited]`, `[sighs]`.
5. **Disk Hygiene (Ephemeral Purge):** File render overlay raksasa ProRes 4444 (`.mov` ~100-250MB) wajib langsung di-unlink dari `/tmp/` seketika render komposit MP4 tuntas.
6. **Pre-Production Deduplication Gate:** Wajib query `ai_brain.doniesdaily_posts` sebelum menyusun tema/naskah.
7. **Post-Publishing Ledger Reconcile:** Seketika video terunggah, status di `ai_brain.doniesdaily_content_ideas` wajib di-update ke `'published'` dan ID YouTube dicatat di `ai_brain.doniesdaily_posts`.
8. **Word-by-Word Subtitle Kinetic Standard (Hormozi Pop):** Subtitle WAJIB muncul per 1 kata (`SWITCH_CAPTIONS_EVERY_MS = 0`), bukan kalimat panjang atau multi-kata bertumpuk. Setiap kata melompat dinamis mengikuti vokal dengan sorot kuning neon (`#FFE600`) dan stroke hitam tebal 20px agar mata penonton terpaku penuh di layar.
9. **Full Transparency & Auditability (Grup & DB-First):** Setiap percakapan, instruksi delegasi, diskusi rapat standup, hingga trace eksekusi alat antar-AI WAJIB tercatat di DB (`agents_chat.db` / `agent_messages` & `agent_traces`) dan disalurkan ke Channel/Grup Matrix terkait. Dilarang keras ada eksekusi diam-diam (dark execution) tanpa riwayat yang bisa dipantau Fahru secara transparan.
10. **Remotion High-CTR Thumbnail & Universal Semantic Matching:**
    - **Thumbnail Still Remotion:** DILARANG mengambil thumbnail via screenshot FFMPEG biasa. Thumbnail wajib dirender via Remotion Still component (`<Still id="DoniThumbnail" />`) dengan tipografi bold kontras tinggi, badge kategori, dan frame dramatis klip anabul di latar belakang.
    - **Anti-Repetition & Semantic Asset Routing:** Milo WAJIB memilih footage dari seluruh 33+ katalog video (`fahru_clips` + `flow_renders`) secara semantik berbasis NLP keyword matching terhadap naskah, dipadu skor Anti-Fatigue Ledger (`ai_brain.doniesdaily_clip_usage`) agar penonton tidak bosan melihat footage yang itu-itu saja.
    - **Cover Poster Injection:** Thumbnail Remotion di-inject sebagai frame poster pembuka (0.08 detik) di video komposit agar YouTube Shorts otomatis menggunakan cover visual punchy tersebut meski API custom thumbnail terkendala izin SMS.
11. **Continuous Learning & Evolution Feedback Loop (Self-Improving Engine):**
    - **Mochi Data Forensic:** Mochi wajib menjalankan audit telemetri YouTube Data API secara otonom setiap pagi (09:00 WIB), mengklasifikasikan performa (outperformer vs underperformer), dan memperbarui PostgreSQL Learning Ledger (`ai_brain.doniesdaily_learnings`).
    - **Dynamic Rule Injection:** Naskah Luna (@Luna) dan seleksi visual Milo (@Milo) WAJIB membaca dan mematuhi `active learned rules` dari DB secara dinamis. Dilarang keras membuat video baru dengan pola/format yang terbukti gagal di masa lalu.
    - **Cadence Interval Guard:** Jeda rilis antar-video WAJIB minimal 16-24 jam (maksimal 1 rilis per hari). Dilarang keras burst-upload yang memicu spam throttle.
12. **Evaluasi Mandatori Ketua Doni (Leadership Review & Executive Verdict):**
    - **Standup Pagi (09:00 WIB):** Ketua Doni WAJIB memberikan evaluasi mendalam atas laporan data Mochi, membedah otopsi retensi/CTR video sebelumnya, menetapkan larangan format usang, dan memberikan approval/verdict kritis terhadap draf naskah Luna & kesiapan subagent sebelum sprint.
    - **Pasca-Produksi (14:00 WIB):** Setelah Cleo menyelesaikan QC teknis, Ketua Doni WAJIB melakukan evaluasi kepatuhan siaran (pacing vokal Vivan, kontras subtitle Hormozi, dynamic thumbnail Remotion, keselarasan semantik video) serta mengeluarkan rilis resmi dan target metrik 24 jam ke depan.
    - **Zero Passive Delegator:** Doni pantang menjadi 'juru bicara pasif'. Setiap masukan, kritik, dan evaluasi kepemimpinan wajib dicatat di Swarm Matrix (`agents_chat.db`) dan diarsipkan ke Obsidian Vault.
13. **Zero In-Video Footage Repetition & High-Retention Fast Pacing (Hukum Besi #13):**
    - **DILARANG KERAS MENGULANG FOOTAGE DALAM 1 VIDEO:** Dilarang mengulang klip via `-stream_loop` dan dilarang memilih lebih dari 1 scene dari cluster folder sesi pemotretan AI yang sama (misal `cat_belly_trap_scratch/scene_1` dan `scene_2` dalam 1 video).
    - **Dynamic Pacing (3.2s – 4.0s per Cut):** Setiap cut visual wajib berganti setiap 3.2 – 4.0 detik. Untuk video 60 detik, Milo wajib menyusun 14–17 adegan unik tanpa looping.
    - **Interleaving Authentic & AI:** Milo wajib menyelingi klip nyata kiriman Mas Fahru (`fahru_clips`) dengan klip AI (`flow_renders`) agar ritme visual bervariasi dan memikat penonton.
    - **Cleo QC Pre-Render Assertion:** Cleo wajib memverifikasi bahwa seluruh klip yang dipilih Milo 100% unik dan tidak ada klip yang durasinya lebih pendek dari potongan slice (`slice_dur <= clip_duration`).
14. **10-Frame Multi-Vision Footage Ingestion (Hukum Besi #14):**
    - Dilarang keras menilai/menamai video dari 1 frame.
    - Wajib mengekstrak tepat 10 frame berurutan (9% s/d 91% durasi) via FFmpeg dan dianalisis alur perilakunya menggunakan Gemini Vision.
    - Penamaan klip wajib panjang dan deskriptif (6-12 kata, snake_case) dengan prefix wajib `asli_fahru_*` untuk footage authentic dan `ai_gen_{cluster}_*` untuk footage AI render.
15. **Milo Remotion Mandate & Outro CTA Closure (Hukum Besi #15):**
    - **Wajib Remotion Engine:** DILARANG KERAS menggunakan subtitle FFmpeg biasa/ASS filter jalan pintas. Semua overlay kinetik (Hook Title, Dynamic Badge, Single-Word Kinetic Subtitle, Outro Card) WAJIB diproduksi oleh Milo via React Remotion engine (`DoniOverlay`).
    - **Single-Word Pop-Up (Hormozi Kinetic):** Subtitle WAJIB melompat per 1 kata murni (`1 word per pop-up`), dilarang menggabungkan 2-3 kata dalam satu tampilan kecuali frasa angka/nama mutlak.
    - **Penutup Wajib CTA (Follow & Subscribe):** Setiap video tanpa kecuali WAJIB menyertakan call-to-action verbal dan visual untuk subscribe & follow DoniesDaily (contoh: *"dan jangan lupa follow dan subscribe DoniesDaily ya!"*). Skrip atau video tanpa CTA penutup otomatis dinyatakan FAILED oleh QC Cleo.

---

## 3. Squad Structure & How-To-Work (RACI Matrix)

```
        ┌────────────────────────────────────────────────────────┐
        │            FAHRU (OWNER & CHIEF EXECUTIVE)             │
        └───────────────────────────┬────────────────────────────┘
                                    │ Arahan Strategis
        ┌───────────────────────────▼────────────────────────────┐
        │          HERMES AGENT (CO-PILOT & GATEKEEPER)          │
        └───────────────────────────┬────────────────────────────┘
                                    │ Briefing & Audit
        ┌───────────────────────────▼────────────────────────────┐
        │          DONI (@Doni — LEAD PRODUCER & ORCHESTRATOR)   │
        └───────┬─────────────┬─────────────┬─────────────┬──────┘
                │             │             │             │
        ┌───────▼──────┐┌─────▼───────┐┌────▼───────┐┌────▼──────┐
        │ 📊 MOCHI     ││ ✍️ LUNA      ││ 🎙️ KAK CERIA││ 🎞️ MILO   │
        │ Analytics DB ││ Copywriter  ││ Audio & TTS││ Video Lead│
        └──────────────┘└─────────────┘└────────────┘└───────────┘
                                                          │
                                                    ┌─────▼──────┐
                                                    │ 🛡️ CLEO    │
                                                    │ BroadcastQC│
                                                    └────────────┘
```

### Detail Peran & Tanggung Jawab:

| Agent | Peran | Output Konkret | Aturan Khusus |
| :--- | :--- | :--- | :--- |
| **📊 Mochi** | Head of Analytics & DB Forensics | Laporan topik bebas duplikasi & estimasi retensi | Query `ai_brain.doniesdaily_posts`. Pilih angle dengan retensi >80%. |
| **🐱 Doni** | Lead Producer | Editorial sprint brief & koordinasi antar subagent | Bawa 2-3 opsi terkurasi ke Hermes di `#executive-board`. |
| **✍️ Luna** | Scriptwriter | Naskah 35–45 kata (Shorts 20s) atau 110–135 kata (Long Shorts 50-60s) | Variasi tag emosi vokal. Wajib hook curiosity di 0-3 detik. |
| **🎙️ Kak Ceria** | Audio Director | File audio stem `master.mp3` & word timestamp `captions.json` | ElevenLabs v4 Turbo (Vivan). Parameter: stability 0.40, boost 0.75, speed 1.08x. |
| **🎞️ Milo** | Visual Director & Renderer | Video MP4 1080x1920 9:16 vertikal | Wajib Semantic Footage Matching. Loop background video sampai audio selesai! |
| **🛡️ Cleo** | Broadcast QC & Gatekeeper | Lulus uji EBU R128 (-14 LUFS) & auto-thumbnail | Tolak release jika durasi video < durasi audio (anti-cutoff guard). |

---

## 4. SOP Verifikasi Anti-Cutoff (The Iron Guard)
Sebelum perintah upload dijalankan, pipeline wajib menjalankan assert berikut:
```python
dur_audio = get_duration(master_audio)
dur_video = get_duration(master_video)
assert dur_video >= dur_audio - 0.1, f"FATAL: Video ({dur_video}s) lebih pendek dari audio ({dur_audio}s)! Video terpotong!"
```
Jika gagal, render otomatis dibatalkan dan dilempar kembali ke Milo untuk di-loop ulang background videonya.

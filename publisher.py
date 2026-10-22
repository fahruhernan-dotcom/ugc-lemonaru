"""TikTok Studio Publisher CLI — Hermes & Velora AI.
Interactive operator for publishing video packages to TikTok Creator Studio.
Supports both Playwright and Selenium (undetected-chromedriver) architectures.
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Redirect temp to Drive D:
D_TEMP = Path(__file__).resolve().parent / "data" / "temp"
D_TEMP.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(D_TEMP.resolve())
os.environ["TMP"] = str(D_TEMP.resolve())
tempfile.tempdir = str(D_TEMP.resolve())

from src.tiktok_browser_operator import TikTokBrowserOperator, run_interactive_login as run_pw_login
from src.tiktok_selenium_operator import TikTokSeleniumOperator, run_interactive_login as run_uc_login


from src.flow_adapter import GoogleFlowAdapter, FlowAuthError
from src.flow_selenium_operator import GoogleFlowSeleniumOperator
from src.media_muxer import MediaMuxer


def verify_package_integrity(pkg_dir: Path) -> tuple:
    """Pre-flight Gatekeeper: Verifies video, audio, and metadata before upload."""
    issues = []
    video_file = pkg_dir / "video.mp4"
    audio_file = pkg_dir / "audio_voiceover.mp3"

    if not video_file.exists():
        return False, ["File video.mp4 tidak ditemukan di paket."]

    v_info = MediaMuxer.probe_file(video_file)
    if v_info.get("duration", 0) < 4.0:
        issues.append(f"Durasi video terlalu pendek ({v_info.get('duration')}s < 4.0s).")

    # Audio stream check & on-the-fly auto-muxing
    if not v_info.get("has_audio", False):
        if audio_file.exists():
            print("⚠️ Video terdeteksi belum memiliki audio stream, namun audio_voiceover.mp3 tersedia.")
            print("   🔧 Menjalankan auto-muxing FFmpeg sebelum unggah...")
            try:
                MediaMuxer.mux_video_and_audio(
                    video_path=video_file,
                    audio_path=audio_file,
                    output_path=video_file
                )
                print("   ✅ Auto-muxing berhasil! Video kini memiliki suara.")
            except Exception as e:
                issues.append(f"Video tidak memiliki audio dan auto-muxing gagal: {e}")
        else:
            issues.append("Video tidak memiliki audio stream (silent video) dan tidak ada file audio_voiceover.mp3.")

    caption_file = pkg_dir / "caption.txt"
    if not caption_file.exists() or len(caption_file.read_text(encoding="utf-8").strip()) == 0:
        issues.append("File caption.txt kosong atau tidak ditemukan.")

    return len(issues) == 0, issues


def find_latest_package(require_video: bool = False) -> str:
    """Fetches latest package path from Supabase DB (with disk fallback)."""
    try:
        from src.repository import get_repository
        repo = get_repository()
        gens = repo.list_ugc_generations()
        for g in gens:
            if g.package_path:
                p = Path(g.package_path)
                if not p.is_absolute():
                    p = Path(__file__).resolve().parent / p
                if p.exists():
                    if require_video:
                        if (p / "video.mp4").exists() or (g.video_path and Path(g.video_path).exists()):
                            return str(p.resolve())
                    else:
                        return str(p.resolve())
    except Exception:
        pass

    pkg_root = Path(__file__).resolve().parent / "ready_to_publish"
    pending_dir = pkg_root / "pending"
    if not pkg_root.exists():
        return ""

    candidates = []
    if pending_dir.exists():
        candidates.extend([p for p in pending_dir.iterdir() if p.is_dir()])
    for p in pkg_root.iterdir():
        if p.is_dir() and p.name not in ["pending", "posted"]:
            candidates.append(p)

    pkgs = sorted(candidates, key=os.path.getmtime, reverse=True)
    if require_video:
        with_video = [p for p in pkgs if (p / "video.mp4").exists()]
        return str(with_video[0].resolve()) if with_video else ""
    return str(pkgs[0].resolve()) if pkgs else ""


def main():
    parser = argparse.ArgumentParser(description="TikTok Publisher & AI Video CLI (Hermes / Velora)")
    parser.add_argument("--engine", choices=["playwright", "selenium"], default="selenium", help="Browser automation engine (default: selenium)")
    parser.add_argument("--login", action="store_true", help="Launch interactive login session for TikTok")
    parser.add_argument("--status", action="store_true", help="Check current login status for TikTok")
    parser.add_argument("--draft", action="store_true", help="Stage package as draft in TikTok Studio (recommended for assisted cart tagging)")
    parser.add_argument("--publish-live", action="store_true", help="Publish post directly (overrides draft staging)")
    parser.add_argument("--upload", type=str, nargs="?", const="latest", help="Upload package to TikTok Studio (default: latest package)")
    
    # Google Flow flags
    parser.add_argument("--flow-login", action="store_true", help="Buka browser Chrome Google Flow via Selenium untuk login & aktifkan ekstensi")
    parser.add_argument("--flow-status", action="store_true", help="Periksa status koneksi Google Flow Engine & akun cookies")
    parser.add_argument("--flow-sync", action="store_true", help="Sinkronisasi token ekstensi Google Flow via WebSocket bridge")
    parser.add_argument("--flow-generate", type=str, help="Generate video 9:16 via Google Flow berdasarkan prompt teks")
    parser.add_argument("--flow-setup-agent", action="store_true", help="Automate Google Flow Agent Settings (Confirm: Never, Aspect: 9:16)")
    parser.add_argument("--flow-create-character", action="store_true", help="Launch Hermes to build consistent character in Google Flow Character Builder")
    parser.add_argument("--flow-agent-run", type=str, nargs="?", const="latest", help="Hermes Google Flow end-to-end: synthesize prompt from brief, render 9:16 video, and assemble package")
    parser.add_argument("--flow-foundation-photos", type=str, nargs="?", const="latest", help="SOP Step 2: Generate 2 Foto Fondasi Velora (Dekat & Jauh) untuk produk/paket")
    parser.add_argument("--flow-animate-from-foundation", type=str, nargs="?", const="latest", help="SOP Step 3: Animasikan 2 Foto Fondasi menjadi video 20 detik multi-scene")
    parser.add_argument("--use-refs", action="store_true", help="Enable dual-reference conditioning (No-Face framing template + physical product photo)")
    parser.add_argument("--aspect", default="9:16", help="Aspek rasio video Google Flow (default: 9:16)")
    parser.add_argument("--duration", type=int, choices=[4, 6, 8, 10], default=10, help="Durasi video Google Flow per klip dalam detik (default: 10s)")
    parser.add_argument("--multi-scene", action="store_true", help="Generate multi-scene sequence (Scene 1 + Scene 2) berdurasi 20s")
    parser.add_argument("--style", choices=["tryon_classic", "walking_lookbook", "fabric_stretch_test", "candid_lifestyle", "layering_styling", "auto"], default="auto", help="Pilihan gaya koreografi video (default: auto - disesuaikan otomatis dengan produk)")
    parser.add_argument("--list-styles", action="store_true", help="Tampilkan daftar gaya koreografi video yang terdaftar")
    parser.add_argument("--storage-status", action="store_true", help="Tampilkan audit rincian penggunaan penyimpanan disk video (pending, posted, temp)")
    parser.add_argument("--clean-videos", action="store_true", help="Jalankan pembersihan sampah video (retensi 3 hari posted, 1 hari temp, cap 2GB)")
    parser.add_argument("--clean-videos-dry-run", action="store_true", help="Simulasikan pembersihan sampah video tanpa menghapus file nyata")
    parser.add_argument("--remotion-render", type=str, nargs="?", const="latest", help="Render video UGC dengan Remotion (Hook Title + Keranjang Kuning + Product Badge)")
    parser.add_argument("--remotion-studio", action="store_true", help="Buka Remotion Studio di browser untuk visual live preview")
    args = parser.parse_args()

    # Video Lifecycle commands
    if args.storage_status:
        from src.video_cleaner import VideoLifecycleManager
        stats = VideoLifecycleManager.get_storage_breakdown()
        print("=" * 65)
        print("💾 AUDIT PENYIMPANAN DISK VIDEO (VPS LIFECYCLE)")
        print("=" * 65)
        print(f"📦 Paket Belum Diunggah (Pending): {stats['pending']['count']} paket ({stats['pending']['mb']} MB)")
        print(f"✅ Paket Terunggah (Posted)     : {stats['posted']['count']} paket ({stats['posted']['mb']} MB)")
        print(f"🌊 Klip Render Temp (data/temp) : {stats['temp']['mb']} MB")
        print(f"📸 Debug / Output (output/)     : {stats['output']['mb']} MB")
        print("-" * 65)
        print(f"📊 Total Video Storage          : {stats['total_mb']} MB / {stats['max_storage_mb']} MB ({stats['usage_percent']}%)")
        print("=" * 65)
        return

    if args.clean_videos or args.clean_videos_dry_run:
        from src.video_cleaner import VideoLifecycleManager
        dry = bool(args.clean_videos_dry_run)
        print("=" * 65)
        print(f"🧹 {'SIMULASI ' if dry else ''}PEMBERSIHAN SAMPAH VIDEO (VPS CLEANER)")
        print("=" * 65)
        res = VideoLifecycleManager.clean_expired_videos(dry_run=dry)
        print(f"Mode                 : {'DRY RUN (Simulasi)' if res['dry_run'] else 'REAL EXECUTION (Dihapus Nyata)'}")
        print(f"Ruang Dibebaskan     : {res['reclaimed_mb']} MB ({res['reclaimed_bytes']:,} bytes)")
        print(f"Paket Posted Dihapus : {len(res['deleted_posted_packages'])} paket {res['deleted_posted_packages']}")
        print(f"File Temp Dihapus    : {res['deleted_temp_files_count']} file")
        print(f"File Output Dihapus  : {res['deleted_output_files_count']} file")
        print(f"Penyimpanan Akhir    : {res['storage_after_mb']} MB ({res['usage_percent']}%)")
        print("=" * 65)
        return

    # Remotion CLI commands
    if args.remotion_studio:
        import subprocess
        remotion_dir = Path(__file__).resolve().parent / "remotion"
        print("🎬 Membuka Remotion Studio di browser (http://localhost:3000)...")
        subprocess.run(["npm", "run", "dev"], cwd=str(remotion_dir), shell=True)
        return

    if args.remotion_render:
        from src.remotion_renderer import RemotionRenderer
        target = args.remotion_render
        pkg_path = find_latest_package(require_video=True) if target == "latest" else target
        if not pkg_path or not Path(pkg_path).exists():
            print("❌ Paket video tidak ditemukan.")
            return
        pkg_dir = Path(pkg_path)
        video_file = pkg_dir / "video.mp4"
        if not video_file.exists():
            print(f"❌ File video.mp4 tidak ada di {pkg_dir}")
            return

        brief_file = pkg_dir / "brief.json"
        metadata_file = pkg_dir / "metadata.json"
        prod_name = "Velora Fashion Outfit"
        price = "Rp 79.000"
        orig_price = "Rp 189.000"
        hook_title = "SPILL OUTFIT VIRAL INI! 😱"

        if brief_file.exists():
            try:
                b_data = json.loads(brief_file.read_text(encoding="utf-8"))
                prod_name = b_data.get("product_name", prod_name)
                hook_title = f"SPILL {prod_name.upper()}! 😱"[:45]
            except Exception:
                pass
        elif metadata_file.exists():
            try:
                m_data = json.loads(metadata_file.read_text(encoding="utf-8"))
                prod_name = m_data.get("product_name", prod_name)
                hook_title = f"SPILL {prod_name.upper()}! 😱"[:45]
            except Exception:
                pass

        print("=" * 65)
        print("🎬 REMOTION UGC VIDEO RENDERER")
        print("=" * 65)
        print(f"📦 Paket Sumber : {pkg_dir.name}")
        print(f"👗 Nama Produk  : {prod_name}")
        print(f"🏷️ Hook Title   : {hook_title}")

        renderer = RemotionRenderer()
        synced_name = renderer.sync_video_to_public(video_file, "active-video.mp4")
        output_remotion = pkg_dir / "video_remotion_ugc.mp4"

        props = {
            "videoSrc": synced_name,
            "productName": prod_name,
            "hookTitle": hook_title,
            "hookSubtitle": "Jatuh & adem banget pas dipake, look clean girl ✨",
            "originalPrice": orig_price,
            "discountPrice": price,
            "discountBadge": "DISKON 58%",
            "showCartPointer": True,
            "cartPointerText": "KLIK KERANJANG KUNING",
            "showOutroCTA": True,
        }

        print("⚡ Merender video UGC dengan Remotion (Hook + Cart Pointer + Price Badge)...")
        try:
            res_path = renderer.render_composition(
                composition_id="VeloraUGC",
                output_path=output_remotion,
                props=props,
                port=3035
            )
            print(f"🎉 SUKSES! Video UGC Remotion tersimpan di: {res_path}")
        except Exception as e:
            print(f"❌ Render Remotion gagal: {e}")
        return

    # Flow CLI commands
    if args.list_styles:
        from src.motion_planner import VideoChoreographyRegistry
        styles = VideoChoreographyRegistry.list_styles()
        print("=" * 70)
        print("✨ DAFTAR GAYA KOREOGRAFI VIDEO (SCALABLE VIDEO ENGINE)")
        print("=" * 70)
        for s in styles:
            print(f"🎬 [{s['id']}] {s['name']}")
            print(f"   Deskripsi: {s['description']}")
            print("-" * 70)
        return

    if args.flow_setup_agent:
        print("⚙️ Mengonfigurasi Agent Settings di Google Flow Studio...")
        print("   - Confirm before generating: Never")
        print("   - Default aspect ratio: 9:16")
        adapter = GoogleFlowAdapter()
        try:
            res = adapter.setup_agent_settings(confirm="Never", aspect_ratio="9:16")
            print("Hasil konfigurasi:", json.dumps(res, indent=2))
        finally:
            adapter.get_browser_agent().close()
        return

    if args.flow_create_character:
        print("🎭 Membuka Character Builder di Google Flow via Selenium...")
        adapter = GoogleFlowAdapter()
        try:
            char_agent = adapter.get_browser_agent()
            res = char_agent.create_fashion_character(
                name="Velora",
                description="Velora is a cute, cheerful, and graceful fashion try-on model. She moves softly and playfully, showcasing outfit details by gently touching collar ribbons, smoothing the fabric with delicate hands, and doing gentle 45-degree body turns to showcase the silhouette and fit. Sweet, aesthetic, and welcoming energy.",
                reference_image=Path("data/templates/velora_official.jpg") if Path("data/templates/velora_official.jpg").exists() else None
            )
            print("Hasil konfigurasi karakter Velora:", json.dumps(res, indent=2))
        finally:
            adapter.get_browser_agent().close()
        return
    if args.flow_status:
        adapter = GoogleFlowAdapter()
        doctor_res = adapter.check_doctor()
        is_auth = adapter.is_authenticated()
        print("=" * 65)
        print("🌊 GOOGLE FLOW ENGINE STATUS")
        print("=" * 65)
        print(f"Status Autentikasi: {'✅ TERHUBUNG' if is_auth else '⚠️ BELUM ADA COOKIES'}")
        print(f"Binary Engine: {adapter.bin_path} ({'Ada' if adapter.bin_path.exists() else 'Tidak Ada'})")
        print(f"Direktori Cookies: {adapter.cookies_dir}")
        print("Detail Doctor:")
        print(json.dumps(doctor_res, indent=2))
        return

    if args.flow_login:
        print("🌐 Membuka Google Chrome via Selenium untuk login Google Flow...")
        print("   Ekstensi Flow Bridge dimuat otomatis.")
        op = GoogleFlowSeleniumOperator()
        try:
            op.open_flow()
            print("Silakan login dengan akun Google Anda di jendela browser yang terbuka.")
            print("Tekan ENTER di terminal ini jika sudah selesai login...")
            input()
            status = op.check_login_status()
            print(f"Status login Google Flow: {'✅ LOGIN' if status else '⚠️ BELUM TERDETEKSI'}")
        finally:
            op.close()
        return

    if args.flow_sync:
        print("🔄 Memulai sinkronisasi cookies Google Flow via Bridge & Selenium...")
        adapter = GoogleFlowAdapter()
        res = adapter.sync_selenium_cookies(wait_seconds=20)
        print("Hasil sinkronisasi:", json.dumps(res, indent=2))
        return

    if args.flow_generate:
        print(f"🎬 Merender video vertikal {args.aspect} via Google Flow...")
        print(f"   Prompt: '{args.flow_generate}'")
        adapter = GoogleFlowAdapter()
        try:
            vid_path = adapter.generate_video(prompt=args.flow_generate, aspect=args.aspect)
            print(f"✅ Video berhasil digenerate di: {vid_path}")
        except FlowAuthError as fae:
            print(f"⚠️ {fae}")
    if args.flow_foundation_photos:
        target = args.flow_foundation_photos
        from src.repository import get_repository
        repo = get_repository()
        db_product = None

        pkg_path = find_latest_package(require_video=False) if target == "latest" else target
        if pkg_path and Path(pkg_path).exists():
            pkg_dir = Path(pkg_path)
            brief_file = pkg_dir / "brief.json"
            if brief_file.exists():
                try:
                    b_data = json.loads(brief_file.read_text(encoding="utf-8"))
                    db_product = repo.get_product(b_data.get("product_id"))
                except Exception:
                    pass
            if not db_product:
                clean_id = pkg_dir.name.replace("PKG_", "").replace("_", "-")
                db_product = repo.get_product(clean_id)

        if not db_product and target != "latest":
            db_product = repo.get_product(target)
            if not db_product:
                for p in repo.list_products():
                    if target.lower() in p.product_id.lower() or target.lower() in p.name.lower():
                        db_product = p
                        break

        if not db_product:
            all_p = repo.list_products()
            if all_p:
                db_product = all_p[0]

        if not db_product:
            print("❌ Produk tidak ditemukan di database Supabase untuk pembuatan foto fondasi.")
            return

        print("=" * 65)
        print("📸 SOP STEP 2: GENERATE 2 FOTO FONDASI VELORA (DEKAT & JAUH)")
        print("=" * 65)
        print(f"Produk Target: {db_product.name} ({db_product.product_id})")
        adapter = GoogleFlowAdapter()
        try:
            res = adapter.generate_foundation_photos(db_product)
            print("🎉 SUKSES! 2 Foto Fondasi Berhasil Disimpan:")
            print(f"   1. Foto 1 (Dekat/Macro): {res['close_up']}")
            print(f"   2. Foto 2 (Jauh/Siluet): {res['wide_silhouette']}")
            print("💡 Selanjutnya jalankan SOP Step 3 (Render Video):")
            print(f"   python publisher.py --flow-animate-from-foundation {db_product.product_id}")
        except FlowAuthError as fae:
            print(f"⚠️ {fae}")
        except Exception as exc:
            print(f"❌ Error selama pembuatan foto fondasi: {exc}")
        return

    if args.flow_animate_from_foundation:
        args.flow_agent_run = args.flow_animate_from_foundation
        args.use_refs = True
        args.multi_scene = True

    if args.flow_agent_run:
        target = args.flow_agent_run
        pkg_path = find_latest_package(require_video=False) if target == "latest" else target
        if not pkg_path or not Path(pkg_path).exists():
            print(f"❌ Paket tidak ditemukan: {target}")
            return
        pkg_dir = Path(pkg_path)
        print(f"🚀 Menjalankan Hermes Google Flow Agent untuk paket: {pkg_dir.name}")

        from src.repository import get_repository
        from src.flow_prompt_engine import GoogleFlowPromptEngine

        repo = get_repository()
        db_product = None

        brief_file = pkg_dir / "brief.json"
        if brief_file.exists():
            try:
                brief_data = json.loads(brief_file.read_text(encoding="utf-8"))
                p_id = brief_data.get("product_id")
                if p_id:
                    db_product = repo.get_product(p_id)
            except Exception:
                pass

        if not db_product:
            clean_id = pkg_dir.name.replace("PKG_", "").replace("_", "-")
            db_product = repo.get_product(clean_id)

        if not db_product:
            all_prods = repo.list_products()
            for p in all_prods:
                if p.product_id in pkg_dir.name or p.name in pkg_dir.name:
                    db_product = p
                    break

        if not db_product:
            print(f"❌ Produk tidak ditemukan di database Supabase untuk paket: {pkg_dir.name}")
            print(f"   Daftar produk di database: {[p.product_id for p in repo.list_products()]}")
            return

        print(f"📦 [DB FETCH] Menggunakan metadata produk dari database: {db_product.name} ({db_product.product_id})")
        product_name = db_product.name
        start_image = None
        references = None
        if args.use_refs:
            from src.reference_template_manager import ReferenceTemplateManager
            from src.product_media_manager import ProductMediaManager

            velora_ref = Path("data/templates/velora_official.jpg")
            if not velora_ref.exists():
                velora_ref = ReferenceTemplateManager.get_default_noface_template()
            
            clean_pid = db_product.product_id.replace("-", "_").lower()
            found_p1 = Path("data/product_images/foundation") / f"{clean_pid}_foundation_1_close.jpg"
            found_p2 = Path("data/product_images/foundation") / f"{clean_pid}_foundation_2_wide.jpg"

            if found_p1.exists() and found_p2.exists():
                print("✨ [SOP FOUNDATION DETECTED] Menggunakan 2 Foto Fondasi:")
                print(f"   - Foto 1 (Dekat/Tekstur): {found_p1.name}")
                print(f"   - Foto 2 (Jauh/Siluet):  {found_p2.name}")
                references = [found_p1, found_p2]
            elif found_p1.exists():
                print(f"✨ [SOP FOUNDATION DETECTED] Menggunakan Foto 1 Fondasi: {found_p1.name}")
                references = [velora_ref, found_p1]
            else:
                # Fetch primary media path directly from Supabase DB
                db_media = repo.list_product_media(db_product.id)
                primary_media = [m for m in db_media if m.is_primary and Path(m.file_path).exists()]
                if primary_media:
                    prod_ref = Path(primary_media[0].file_path)
                else:
                    prod_ref = ProductMediaManager.get_or_create_product_ref(db_product.product_id, pkg_dir)

                references = [velora_ref, prod_ref]
                print("🎭 Mode: No-Face Chin-Down Fashion Try-On (Dual Reference)")
                print(f"🖼️ Reference Character: {velora_ref.name}")
                print(f"👗 Reference Product: {prod_ref.name}")
            if args.multi_scene:
                style_used, scene_prompts = GoogleFlowPromptEngine.synthesize_choreographed_multiscene_prompts(
                    db_product, style_name=getattr(args, "style", "auto"), duration_per_scene=args.duration
                )
                print(f"🎬 Mode Multi-Scene UGC [Gaya: {style_used}]: {len(scene_prompts)} Scene × {args.duration}s = {len(scene_prompts)*args.duration}s")
            else:
                style_used, prompts = GoogleFlowPromptEngine.synthesize_choreographed_multiscene_prompts(
                    db_product, style_name=getattr(args, "style", "auto"), duration_per_scene=args.duration
                )
                scene_prompts = [prompts[0]]
                print(f"🎬 Mode Single-Scene UGC [Gaya: {style_used}]: 1 Scene × {args.duration}s")
        else:
            scene_prompts = [(
                f"Slow motion fashion runway walk, Indonesian female model showcasing {product_name}, "
                f"camera slowly tilting up from waist to shoulders, smooth movement, clean aesthetic, "
                f"9:16 vertical, photorealistic, 24fps motion"
            )]

        adapter = GoogleFlowAdapter()
        try:
            target_vid = pkg_dir / "video.mp4"
            if len(scene_prompts) > 1:
                print("🌊 Menghubungi Google Flow Engine untuk Multi-Scene Sequence...")
                for i, sp in enumerate(scene_prompts, 1):
                    print(f"   Scene {i}: {sp[:70]}...")
                final_vid = adapter.generate_multiscene_video(
                    scene_prompts=scene_prompts,
                    references=references,
                    duration_per_scene=args.duration,
                    aspect=args.aspect,
                    output_file=target_vid
                )
                print(f"🎉 Sukses! Video Multi-Scene tersimpan di: {final_vid}")
                print(f"   Ukuran: {final_vid.stat().st_size / (1024*1024):.2f} MB")
            else:
                print(f"📝 Prompt Google Flow Terpilih:\n   '{scene_prompts[0]}'")
                print("🌊 Menghubungi Google Flow Engine...")
                vid_path = adapter.generate_video(
                    prompt=scene_prompts[0],
                    start_image=start_image,
                    references=references,
                    aspect=args.aspect,
                    duration=args.duration
                )
                print(f"✅ Video mentah berhasil didownload: {vid_path}")

                import subprocess
                import shutil
                try:
                    import imageio_ffmpeg
                    ffmpeg_exe = shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()
                except Exception:
                    ffmpeg_exe = shutil.which("ffmpeg") or "ffmpeg"

                conv_cmd = [
                    ffmpeg_exe, "-y",
                    "-i", str(vid_path),
                    "-vf", "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920",
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-threads", "1",
                    "-c:a", "aac",
                    str(target_vid)
                ]
                print(f"🎬 Menstandarisasi video vertikal ke: {target_vid.name}...")
                conv_res = subprocess.run(conv_cmd, capture_output=True, text=True, check=False)
                if conv_res.returncode == 0 and target_vid.exists():
                    print(f"🎉 Sukses! Video 9:16 tersimpan di: {target_vid}")
                    print(f"   Ukuran: {target_vid.stat().st_size / (1024*1024):.2f} MB")
                else:
                    shutil.copy2(vid_path, target_vid)
                print(f"⚠️ FFmpeg fallback: menyalin langsung ke {target_vid}")
        except FlowAuthError as fae:
            print(f"⚠️ {fae}")
        except Exception as exc:
            print(f"❌ Error selama eksekusi Flow: {exc}")
        return

    # If no flags passed, show friendly interactive menu
    if not (args.login or args.status or args.upload or args.draft or args.publish_live):
        print("=" * 65)
        print("🎬 VELORA AI × TIKTOK STUDIO & GOOGLE FLOW PUBLISHER")
        print("=" * 65)
        print("Pilih opsi operasional:")
        print("  1. Login ke TikTok via Playwright (Buka Chrome biasa)")
        print("  2. Login ke TikTok via Selenium (undetected-chromedriver)")
        print("  3. Periksa Status Login TikTok & Ambil Screenshot")
        print("  4. Upload Paket Konten Terakhir ke TikTok Studio (Draft)")
        print("  --- GOOGLE FLOW VIDEO & SOP ---")
        print("  5. Buka Browser Google Flow via Selenium (Login Google Akun)")
        print("  6. Periksa Status Koneksi Google Flow Engine")
        print("  7. SOP Step 2: Generate 2 Foto Fondasi Velora (Dekat & Jauh)")
        print("  8. SOP Step 3: Animasikan Video 20s dari Foto Fondasi (Pilih Gaya)")
        print("  9. Lihat Daftar 5 Gaya Koreografi Video Terdaftar")
        print("  --- VPS STORAGE & GARBAGE CLEANER ---")
        print("  10. Audit Penggunaan Penyimpanan Disk Video (Storage Breakdown)")
        print("  11. Bersihkan Sampah Video (3 Hari Posted, 1 Hari Temp, Cap 2GB)")
        print("  --- REMOTION UGC OVERLAY & STUDIO ---")
        print("  12. Render Video UGC dengan Remotion (Hook Title + Keranjang Kuning + Product Badge)")
        print("  13. Buka Remotion Studio di Browser (Live Preview & Timeline)")
        print("  14. Keluar")
        print("=" * 65)
        choice = input("👉 Pilihan [1-14]: ").strip()

        if choice == "1":
            run_pw_login()
            return
        elif choice == "2":
            run_uc_login(mode="selenium")
            return
        elif choice == "3":
            sel_dir = Path(__file__).resolve().parent / "data" / "chrome_profile_tiktok_selenium"
            if sel_dir.exists():
                print("🔍 Memeriksa status sesi TikTok (Selenium)...")
                op = TikTokSeleniumOperator()
                try:
                    status = op.check_login_status()
                    print(json.dumps(status, indent=2))
                finally:
                    op.close()
            else:
                print("🔍 Memeriksa status sesi TikTok (Playwright)...")
                op = TikTokBrowserOperator()
                try:
                    if op.connect():
                        status = op.check_login_status()
                        print(json.dumps(status, indent=2))
                finally:
                    op.close()
            return
        elif choice == "4":
            pkg_path = find_latest_package(require_video=True)
            if not pkg_path:
                print("❌ Belum ada paket video yang terdaftar.")
                return
            is_valid, issues = verify_package_integrity(Path(pkg_path))
            if not is_valid:
                print("❌ PRE-FLIGHT CHECK GAGAL:")
                for iss in issues:
                    print(f"   - {iss}")
                return

            try:
                from src.repository import get_repository
                repo = get_repository()
                gens = repo.list_ugc_generations()
                matched_gen = next((g for g in gens if g.package_path and Path(g.package_path).name == Path(pkg_path).name), None)
                if matched_gen:
                    product = repo.get_product(matched_gen.product_id)
                    prod_name = product.name if product else matched_gen.product_id
                    print(f"📦 [DB FETCH] Paket dari Database Supabase:")
                    print(f"   - Produk: {prod_name}")
                    print(f"   - Generation ID: {matched_gen.id}")
            except Exception:
                pass

            print(f"📦 Mengunggah paket: {pkg_path}")
            sel_dir = Path(__file__).resolve().parent / "data" / "chrome_profile_tiktok_selenium"
            res = {}
            if sel_dir.exists():
                op = TikTokSeleniumOperator()
                try:
                    res = op.prepare_package_upload(pkg_path)
                    print(json.dumps(res, indent=2))
                finally:
                    op.close()
            else:
                op = TikTokBrowserOperator()
                try:
                    if op.connect():
                        res = op.prepare_package_upload(pkg_path)
                        print(json.dumps(res, indent=2))
                finally:
                    op.close()

            if res.get("status") in ["STAGED_AS_DRAFT", "PUBLISHED"]:
                from src.video_cleaner import VideoLifecycleManager
                try:
                    new_pkg = VideoLifecycleManager.mark_as_posted(pkg_path, status_label=res["status"])
                    print(f"📦 [LIFECYCLE] Paket berhasil dipindahkan ke arsip posted: {new_pkg.name}")
                except Exception as e:
                    print(f"⚠️ Gagal memindahkan paket ke posted: {e}")
            return
        elif choice == "5":
            print("🌐 Membuka Google Chrome via Selenium untuk login Google Flow...")
            op = GoogleFlowSeleniumOperator()
            try:
                op.open_flow()
                print("Silakan login dengan akun Google Anda di jendela browser yang terbuka.")
                print("Tekan ENTER di terminal ini jika sudah selesai login...")
                input()
                status = op.check_login_status()
                print(f"Status login Google Flow: {'✅ LOGIN' if status else '⚠️ BELUM TERDETEKSI'}")
            finally:
                op.close()
            return
        elif choice == "6":
            adapter = GoogleFlowAdapter()
            doctor_res = adapter.check_doctor()
            is_auth = adapter.is_authenticated()
            print("=" * 65)
            print("🌊 GOOGLE FLOW ENGINE STATUS")
            print("=" * 65)
            print(f"Status Autentikasi: {'✅ TERHUBUNG' if is_auth else '⚠️ BELUM ADA COOKIES'}")
            print(f"Binary Engine: {adapter.bin_path} ({'Ada' if adapter.bin_path.exists() else 'Tidak Ada'})")
            print("Detail Doctor:")
            print(json.dumps(doctor_res, indent=2))
            return
        elif choice == "7":
            from src.repository import get_repository
            repo = get_repository()
            prods = repo.list_products()
            print("Pilih Produk untuk SOP Step 2 (Generate 2 Foto Fondasi):")
            for i, p in enumerate(prods, 1):
                print(f"  {i}. {p.name} ({p.product_id})")
            p_idx = input(f"👉 Pilihan [1-{len(prods)}]: ").strip()
            try:
                selected_prod = prods[int(p_idx) - 1]
            except Exception:
                selected_prod = prods[0] if prods else None
            if not selected_prod:
                print("❌ Produk tidak ditemukan.")
                return

            print(f"📸 SOP STEP 2: Menghasilkan 2 Foto Fondasi untuk {selected_prod.name}...")
            adapter = GoogleFlowAdapter()
            try:
                res = adapter.generate_foundation_photos(selected_prod)
                print("🎉 SUKSES! 2 Foto Fondasi Berhasil Disimpan:")
                print(f"   1. Foto 1 (Dekat/Macro): {res['close_up']}")
                print(f"   2. Foto 2 (Jauh/Siluet): {res['wide_silhouette']}")
            except FlowAuthError as fae:
                print(f"⚠️ {fae}")
            except Exception as exc:
                print(f"❌ Error: {exc}")
            return
        elif choice == "8":
            pkg_path = find_latest_package(require_video=False)
            if not pkg_path:
                print("❌ Paket belum dibuat. Silakan produce paket terlebih dahulu.")
                return
            from src.motion_planner import VideoChoreographyRegistry
            styles = VideoChoreographyRegistry.list_styles()
            print("Pilih Gaya Koreografi Video:")
            print("  0. Auto (Disesuaikan otomatis dengan jenis pakaian) [DEFAULT]")
            for i, s in enumerate(styles, 1):
                print(f"  {i}. {s['name']} - {s['description']}")
            s_idx = input(f"👉 Pilihan [0-{len(styles)}] (default 0): ").strip()
            if s_idx and s_idx != "0":
                try:
                    args.style = styles[int(s_idx) - 1]["id"]
                except Exception:
                    args.style = "auto"
            else:
                args.style = "auto"

            args.flow_agent_run = pkg_path
            args.use_refs = True
            args.multi_scene = True
            # Proceed to flow_agent_run execution below
        elif choice == "9":
            from src.motion_planner import VideoChoreographyRegistry
            styles = VideoChoreographyRegistry.list_styles()
            print("=" * 70)
            print("✨ DAFTAR GAYA KOREOGRAFI VIDEO (SCALABLE VIDEO ENGINE)")
            print("=" * 70)
            for s in styles:
                print(f"🎬 [{s['id']}] {s['name']}")
                print(f"   Deskripsi: {s['description']}")
                print("-" * 70)
            return
        elif choice == "10":
            from src.video_cleaner import VideoLifecycleManager
            stats = VideoLifecycleManager.get_storage_breakdown()
            print("=" * 65)
            print("💾 AUDIT PENYIMPANAN DISK VIDEO (VPS LIFECYCLE)")
            print("=" * 65)
            print(f"📦 Paket Belum Diunggah (Pending): {stats['pending']['count']} paket ({stats['pending']['mb']} MB)")
            print(f"✅ Paket Terunggah (Posted)     : {stats['posted']['count']} paket ({stats['posted']['mb']} MB)")
            print(f"🌊 Klip Render Temp (data/temp) : {stats['temp']['mb']} MB")
            print(f"📸 Debug / Output (output/)     : {stats['output']['mb']} MB")
            print("-" * 65)
            print(f"📊 Total Video Storage          : {stats['total_mb']} MB / {stats['max_storage_mb']} MB ({stats['usage_percent']}%)")
            print("=" * 65)
            return
        elif choice == "11":
            from src.video_cleaner import VideoLifecycleManager
            confirm = input("👉 Jalankan pembersihan sampah video sekarang? [y/N]: ").strip().lower()
            if confirm == "y":
                res = VideoLifecycleManager.clean_expired_videos(dry_run=False)
                print("=" * 65)
                print("🧹 HASIL PEMBERSIHAN SAMPAH VIDEO (VPS CLEANER)")
                print("=" * 65)
                print(f"Ruang Dibebaskan     : {res['reclaimed_mb']} MB ({res['reclaimed_bytes']:,} bytes)")
                print(f"Paket Posted Dihapus : {len(res['deleted_posted_packages'])} paket {res['deleted_posted_packages']}")
                print(f"File Temp Dihapus    : {res['deleted_temp_files_count']} file")
                print(f"File Output Dihapus  : {res['deleted_output_files_count']} file")
                print(f"Penyimpanan Akhir    : {res['storage_after_mb']} MB ({res['usage_percent']}%)")
                print("=" * 65)
            else:
                print("Pembersihan dibatalkan.")
            return
        elif choice == "12":
            args.remotion_render = "latest"
        elif choice == "13":
            import subprocess
            remotion_dir = Path(__file__).resolve().parent / "remotion"
            print("🎬 Membuka Remotion Studio di browser (http://localhost:3000)...")
            subprocess.run(["npm", "run", "dev"], cwd=str(remotion_dir), shell=True)
            return
        else:
            print("Keluar.")
            return

    # CLI flag execution
    if args.login:
        if args.engine == "selenium":
            run_uc_login(mode="selenium")
        else:
            run_pw_login()
    elif args.status:
        if args.engine == "selenium":
            op = TikTokSeleniumOperator()
            try:
                res = op.check_login_status()
                print(json.dumps(res, indent=2))
            finally:
                op.close()
        else:
            op = TikTokBrowserOperator()
            try:
                if op.connect():
                    res = op.check_login_status()
                    print(json.dumps(res, indent=2))
            finally:
                op.close()
    elif args.upload or args.draft:
        target = args.upload if args.upload and args.upload != "latest" else "latest"
        pkg_path = find_latest_package(require_video=True) if target == "latest" else target
        if not pkg_path or not Path(pkg_path).exists():
            print(f"❌ Paket video tidak ditemukan: {pkg_path}")
            sys.exit(1)

        pkg_dir = Path(pkg_path)
        try:
            from src.repository import get_repository
            repo = get_repository()
            gens = repo.list_ugc_generations()
            matched_gen = next((g for g in gens if g.package_path and Path(g.package_path).name == pkg_dir.name), None)
            if matched_gen:
                product = repo.get_product(matched_gen.product_id)
                prod_name = product.name if product else matched_gen.product_id
                print(f"📦 [DB FETCH] Paket dari Database Supabase:")
                print(f"   - Produk: {prod_name}")
                print(f"   - Generation ID: {matched_gen.id}")
        except Exception:
            pass

        is_valid, issues = verify_package_integrity(pkg_dir)
        if not is_valid:
            print("❌ PRE-FLIGHT CHECK GAGAL:")
            for iss in issues:
                print(f"   - {iss}")
            sys.exit(1)

        is_live = bool(args.publish_live)
        print(f"📦 Mempersiapkan unggahan paket: {pkg_path}")
        print(f"   Mode: {'PUBLIKASI LANGSUNG (LIVE)' if is_live else 'DRAF DI STUDIO (ASSISTED STAGING)'}")
        if is_live:
            print("⚠️ [PERINGATAN AFFILIATE] Anda memilih PUBLISH LANGSUNG (LIVE).")
            print("   Pastikan produk Keranjang Kuning sudah ditautkan agar komisi tidak Rp 0!")
        else:
            print("💡 Video akan disimpan sebagai DRAF. Tautkan Keranjang Kuning di HP sebelum posting!")

        res = {}
        if args.engine == "selenium":
            op = TikTokSeleniumOperator()
            try:
                res = op.prepare_package_upload(pkg_path, save_draft=(not is_live), publish_live=is_live)
                print(json.dumps(res, indent=2))
            finally:
                op.close()
        else:
            op = TikTokBrowserOperator()
            try:
                if op.connect():
                    res = op.prepare_package_upload(pkg_path, save_draft=(not is_live), publish_live=is_live)
                    print(json.dumps(res, indent=2))
            finally:
                op.close()

        if res.get("status") in ["STAGED_AS_DRAFT", "PUBLISHED"]:
            from src.video_cleaner import VideoLifecycleManager
            try:
                new_pkg = VideoLifecycleManager.mark_as_posted(pkg_path, status_label=res["status"])
                print(f"📦 [LIFECYCLE] Paket berhasil dipindahkan ke arsip posted: {new_pkg.name}")
            except Exception as e:
                print(f"⚠️ Gagal memindahkan paket ke posted: {e}")


if __name__ == "__main__":
    main()

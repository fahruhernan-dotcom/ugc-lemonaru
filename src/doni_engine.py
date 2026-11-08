"""Doni Master Engine — Autonomous YouTube Shorts Producer for DoniesDaily.
Combines:
- Verified 100% Real Motion Cat Videos (Multi-clip seamless transitions)
- Viral Format Synthesis:
    * Top Bar: High-contrast Dark Container with All-Caps Bold Hook (NahhJadi style)
    * Lower Banner: Punchy Contrarian Subtitle with Thick Black Stroke (Funrice style)
    * Audio: Humanized Indonesian Female Voiceover (id-ID-GadisNeural, +6% rate, +2Hz pitch)
    * Soundtrack: Soft Playful Acoustic BGM with Auto-Ducking
    * Retention Hook: Native Question CTA + Channel Handle Watermark
- YouTube Data API v3 OAuth Publishing
"""

import asyncio
import json
import logging
import os
import random
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import edge_tts

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.youtube_api_publisher import YouTubeAPIPublisher
from src.elevenlabs_tts import generate_speech as generate_elevenlabs_speech

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("doni_master_engine")

WORKSPACE = ROOT_DIR
ASSETS_DIR = WORKSPACE / "assets"
CAT_VIDEOS_DIR = ASSETS_DIR / "cat_videos"
AUDIO_DIR = ASSETS_DIR / "audio"
OUTPUT_DIR = WORKSPACE / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 10 Curated High-Engagement Cat Story Blueprints (NahhJadi + Funrice style)
CAT_TOPICS: List[Dict[str, Any]] = [
    {
        "title": "KUCING DENGAN EKOR PENDEK",
        "hook_subtitle": "MUTASI GENETIK BUKAN KEJEPIT PINTU!",
        "script": (
            "Pernah gak sih... kalian perhatiin, kenapa banyak kucing kampung di sekitar kita... ekornya buntung atau pendek banget? "
            "Banyak yang ngira ini karena kejepit pintu, atau dipotong orang jahat... padahal bukan sama sekali! "
            "Ini murni mutasi genetik alami bernama gen HES-7—yang bikin tulang ekornya memendek sejak lahir. "
            "Kucing ekor pendek justru lincah banget, dan punya daya tahan tubuh yang luar biasa! "
            "Kucing kamu di rumah ekornya panjang apa pendek nih? Coba komen di bawah, dan jangan lupa subscribe ya!"
        ),
        "clips": ["clip8_stock.mp4", "clip6_stock.mp4", "clip9_stock.mp4"],
        "tags": ["#Shorts", "#KucingEkorPendek", "#FaktaKucing", "#DoniesDaily", "#CatLovers"]
    },
    {
        "title": "KENAPA KUCING SUKA NATAP DINDING KOSONG?",
        "hook_subtitle": "BUKAN LIHAT HANTU, TAPI INI!",
        "script": (
            "Pernah gak merinding... lihat kucing kamu bengong natap tembok kosong tanpa kedip? "
            "Tenang... mereka bukan lagi lihat makhluk halus kok! "
            "Kucing punya pendengaran super hingga enam puluh empat ribu Hertz, dan bisa menangkap gelombang ultraviolet. "
            "Mereka sebenarnya lagi mendengar langkah rayap di dalam tembok—atau debu mikroskopis yang lagi melayang! "
            "Kucing kamu sering begini juga gak? Tulis di komentar, dan subscribe ya!"
        ),
        "clips": ["clip6_stock.mp4", "clip7_stock.mp4", "clip2_ball.mp4"],
        "tags": ["#Shorts", "#KucingLucu", "#MisteriKucing", "#DoniesDaily", "#KucingAneh"]
    },
    {
        "title": "KENAPA KUCING SUKA IKUT KE TOILET?",
        "hook_subtitle": "MEREKA LAGI JAGA NYAWA KAMU!",
        "script": (
            "Setiap kali kamu masuk kamar mandi... kucing kamu pasti heboh nungguin di depan pintu, atau maksa minta masuk? "
            "Di dunia hewan liar... saat buang air adalah momen paling rentan diserang predator! "
            "Kucing menganggap kamu bagian dari keluarganya—jadi mereka merasa wajib berpatroli menjaga keselamatanmu di toilet! "
            "Manis banget kan rasa setianya? Kucing siapa nih yang suka jadi satpam toilet? Komen di bawah ya!"
        ),
        "clips": ["clip5_meow.mp4", "clip7_stock.mp4", "clip8_stock.mp4"],
        "tags": ["#Shorts", "#KucingToilet", "#PerilakuKucing", "#DoniesDaily", "#CatLife"]
    },
    {
        "title": "KUCING MENDENGKUR BISA SEMBUHKAN TULANG?",
        "hook_subtitle": "FREKUENSI AJAIB DOKTER ALAMI!",
        "script": (
            "Tahu gak sih? Dengkuran kucing atau purring ternyata bukan cuma tanda kalau mereka lagi manja! "
            "Getaran dengkuran kucing berada di frekuensi dua puluh sampai seratus empat puluh Hertz. "
            "Dalam dunia medis, frekuensi getaran ini terbukti ilmiah mempercepat regenerasi tulang yang retak, menurunkan tekanan darah, dan meredakan radang otot. "
            "Punya kucing di rumah serasa punya dokter terapi pribadi! Kucing kamu hobi ngorok juga gak? Subscribe ya!"
        ),
        "clips": ["clip13_sleepy.mp4", "clip14_yawning.mp4", "clip8_stock.mp4"],
        "tags": ["#Shorts", "#PurringCat", "#TerapiKucing", "#DoniesDaily", "#CatHealth"]
    },
    {
        "title": "KENAPA KUCING TAKUT SAMA TIMUN?",
        "hook_subtitle": "REFLEKS PURBA LAWAN ULAR!",
        "script": (
            "Pasti sering lihat video kucing loncat histeris cuma gara-gara di belakangnya ada timun? "
            "Kucing bukan takut sama sayurannya, tapi refleks bawaan purba mereka langsung mengira benda panjang hijau itu adalah ular berbisa! "
            "Karena gerakannya tiba-tiba, otak kucing langsung memicu mode panik bertahan hidup. "
            "Tapi tolong jangan usil jahilin kucing kamu pakai timun ya, karena bisa bikin mereka trauma dan stres berat. Sayangi anabul kamu dan subscribe!"
        ),
        "clips": ["clip1_fight.mp4", "clip4_kitten.mp4", "clip6_stock.mp4"],
        "tags": ["#Shorts", "#KucingVsTimun", "#PsikologiKucing", "#DoniesDaily", "#Anabul"]
    },
    {
        "title": "ARTI GERAKAN EKOR KUCING YANG WAJIB TAHU",
        "hook_subtitle": "JANGAN DIELUS PAS KIBAS KERAS!",
        "script": (
            "Jangan sampai dicakar! Ini cara membaca isi hati kucing lewat ekornya. "
            "Kalau ekornya tegak lurus dengan ujung melengkung seperti tanda tanya, artinya dia lagi super ramah dan senang ketemu kamu. "
            "Tapi kalau ekornya mulai dikibas-kibaskan ke lantai dengan cepat dan keras, itu sinyal merah kalau dia lagi jengkel dan butuh waktu sendiri! "
            "Sudah paham kan bahasanya? Share ke teman sesama cat lovers dan jangan lupa subscribe!"
        ),
        "clips": ["clip8_stock.mp4", "clip9_stock.mp4", "clip1_fight.mp4"],
        "tags": ["#Shorts", "#BahasaKucing", "#EkorKucing", "#DoniesDaily", "#TipsKucing"]
    },
    {
        "title": "KENAPA KUCING TIDUR 16 JAM SEHARI?",
        "hook_subtitle": "BUKAN MALAS TAPI HEMAT ENERGI!",
        "script": (
            "Jangan julid dulu lihat kucing kamu seharian cuma molor di sofa! "
            "Kucing secara alami menghabiskan tujuh puluh persen hidupnya untuk tidur. "
            "Di alam liar, energi berburu mangsa membutuhkan ledakan stamina yang sangat besar, jadi tidur panjang adalah cara biologis mereka menghemat daya baterai tubuh. "
            "Jadi mereka bukan pemalas, tapi predator taktis yang cerdas! Kucing kamu sehari tidur berapa jam? Tulis di komentar ya!"
        ),
        "clips": ["clip13_sleepy.mp4", "clip14_yawning.mp4", "clip7_stock.mp4"],
        "tags": ["#Shorts", "#KucingTidur", "#KaumRebahan", "#DoniesDaily", "#CatNap"]
    },
    {
        "title": "KENAPA KUCING OYEN LEBIH BARBAR?",
        "hook_subtitle": "ILMUWAN BONGKAR FAKTA INI!",
        "script": (
            "Kucing oyen sering banget dicap biang kerok, petakilan, dan paling barbar di jagat maya! Benar gak sih? "
            "Penelitian genetika menunjukkan bahwa delapan puluh persen kucing oyen berjenis kelamin jantan. "
            "Kucing jantan secara alami memiliki hormon testosteron lebih tinggi yang bikin mereka lebih aktif bereksplorasi, pemberani, dan vokal mengeong. "
            "Jadi reputasi barbar si oyen memang ada penjelasan ilmiahnya! Siapa di sini babu si oyen? Absen di komentar yuk!"
        ),
        "clips": ["clip1_fight.mp4", "clip2_ball.mp4", "clip8_stock.mp4"],
        "tags": ["#Shorts", "#KucingOyen", "#SiOyenBarbar", "#DoniesDaily", "#OyenAlert"]
    },
    {
        "title": "RAHASIA KUCING MENGUSAP KEPALANYA KE KITA",
        "hook_subtitle": "KAMU RESMI JADI PROPERTI MEREKA!",
        "script": (
            "Pernah gak kaki atau dagu kamu disundul-sundul manja sama kepala kucing? "
            "Di pipi dan dahi kucing terdapat kelenjar aroma feromon yang hanya bisa tercium oleh sesama kucing. "
            "Saat mereka menggosokkan kepalanya ke kamu, itu adalah ritual resmi menandai bahwa kamu adalah pemilik sah dan properti berharga milik mereka! "
            "Bukan kamu yang punya kucing, tapi kucing yang punya kamu! Kucing kamu suka nyundul juga? Komen di bawah ya!"
        ),
        "clips": ["clip3_mouse.mp4", "clip4_kitten.mp4", "clip8_stock.mp4"],
        "tags": ["#Shorts", "#KucingManja", "#CatBunting", "#DoniesDaily", "#KucingPeliharaan"]
    },
    {
        "title": "KUCING BISA TAHU PERASAAN SEDIH KITA?",
        "hook_subtitle": "EMPATI TERSEMBUNYI ANABUL!",
        "script": (
            "Banyak yang bilang kucing itu hewan cuek dan egois. Tapi pernah gak pas kamu lagi menangis atau sedih, kucing kamu tiba-tiba datang dan duduk di pangkuanmu? "
            "Studi perilaku hewan membuktikan kucing sangat peka terhadap perubahan nada suara dan ekspresi wajah pemiliknya. "
            "Duduk dekat saat kamu sedih adalah bentuk dukungan emosional tanpa kata dari mereka. "
            "Anabul memang sahabat terbaik manusia! Peluk kucingmu hari ini dan klik tombol subscribe ya!"
        ),
        "clips": ["clip7_stock.mp4", "clip6_stock.mp4", "clip8_stock.mp4"],
        "tags": ["#Shorts", "#KucingPeka", "#SahabatAnabul", "#DoniesDaily", "#CatLoversIndonesia"]
    }
]

class DoniMasterEngine:
    def __init__(self):
        self.publisher = YouTubeAPIPublisher()
        self.voice = "id-ID-GadisNeural"
        self.bgm_path = AUDIO_DIR / "cat_playful_bgm.mp3"
        self.venv_python = WORKSPACE / ".venv" / "bin" / "python"

    def pick_story(self, topic_index: Optional[int] = None) -> Dict[str, Any]:
        # Priority 1: Query database ai_brain.doniesdaily_content_ideas for status = 'ready' (Anti-Deduplication)
        try:
            sql = "SELECT json_agg(t) FROM (SELECT topic_key, title, hook_banner, hook_vocal, full_script, scene_breakdown, status FROM ai_brain.doniesdaily_content_ideas WHERE status = 'ready' ORDER BY created_at ASC) t;"
            res = subprocess.run([
                "docker", "exec", "-i", "supabase-db",
                "psql", "-U", "postgres", "-d", "postgres", "-t", "-A", "-c", sql
            ], capture_output=True, text=True, timeout=10)
            raw = res.stdout.strip()
            if raw and raw != "null":
                ideas = json.loads(raw)
                if ideas:
                    chosen = ideas[topic_index] if (topic_index is not None and 0 <= topic_index < len(ideas)) else ideas[0]
                    clips = ["clip8_stock.mp4", "clip6_stock.mp4", "clip9_stock.mp4"]
                    sb = chosen.get("scene_breakdown")
                    if isinstance(sb, list) and sb and isinstance(sb[0], str):
                        clips = sb
                    return {
                        "topic_key": chosen["topic_key"],
                        "title": chosen["title"],
                        "hook_subtitle": chosen.get("hook_banner") or "FAKTA ANABUL VIRAL",
                        "script": chosen["full_script"],
                        "clips": clips,
                        "tags": ["#Shorts", "#KucingLucu", "#FaktaKucing", "#DoniesDaily", "#CatLovers"]
                    }
        except Exception as e:
            logger.warning(f"DB pick_story error ({e}), falling back to memory topics...")

        if topic_index is not None and 0 <= topic_index < len(CAT_TOPICS):
            return CAT_TOPICS[topic_index]
        return random.choice(CAT_TOPICS)

    def generate_voice_sync(self, text: str, out_path: Path) -> Path:
        """Generates expressive, humanized female voice narration using ElevenLabs Multilingual v2 with acoustic punctuation tuning."""
        try:
            logger.info("🎙️ Synthesizing humanized narration with ElevenLabs (Kak Ceria - d15jrIAARvF899pDoC6T)...")
            generate_elevenlabs_speech(text, str(out_path))
            return out_path
        except Exception as e:
            logger.warning(f"⚠️ ElevenLabs generation failed ({e}), falling back to edge-tts GadisNeural...")
            cmd = [
                str(WORKSPACE / ".venv" / "bin" / "edge-tts"),
                "--text", text,
                "--voice", self.voice,
                "--rate", "+6%",
                "--pitch", "+2Hz",
                "--write-media", str(out_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return out_path

    def assemble_master_short(self, topic: Dict[str, Any], output_path: Path) -> Path:
        """Assembles verified cat multi-clips with NahhJadi header + Funrice lower subtitle."""
        temp_dir = Path("/tmp/doni_render_master")
        temp_dir.mkdir(parents=True, exist_ok=True)
        raw_voice = temp_dir / "voice.mp3"
        master_audio = temp_dir / "master_audio.mp3"

        # 1. Voice generation
        logger.info("🎙️ Synthesizing GadisNeural narration via edge-tts CLI...")
        self.generate_voice_sync(topic["script"], raw_voice)

        # 2. Audio mixing with BGM
        logger.info("🎵 Mixing audio with acoustic cat BGM...")
        cmd_audio = [
            "ffmpeg", "-y",
            "-i", str(raw_voice),
            "-i", str(self.bgm_path),
            "-filter_complex",
            "[0:a]volume=1.25,highpass=f=80,dynaudnorm[voice];[1:a]volume=0.08[bgm];[voice][bgm]amix=inputs=2:duration=first[aout]",
            "-map", "[aout]",
            "-c:a", "libmp3lame", "-q:a", "2",
            str(master_audio)
        ]
        subprocess.run(cmd_audio, check=True, capture_output=True)

        # Probe duration
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(master_audio)],
            capture_output=True, text=True, check=True
        )
        duration = float(probe.stdout.strip())
        logger.info(f"⏱️ Audio duration: {duration:.2f} seconds")

        # 3. Multi-clip sequence selection (strictly Fahru's clips and Google Flow)
        fahru_dir = CAT_VIDEOS_DIR / "fahru_clips"
        flow_dir = CAT_VIDEOS_DIR / "flow_renders"
        active_clips = []
        banned_arya = {"domba", "kambing", "ternak", "seminar", "selfie", "karaoke", "cermin", "tutorial", "merokok", "pekerja", "sekolah", "pemuda"}
        if fahru_dir.exists():
            active_clips = [c for c in sorted(list(fahru_dir.glob("*.mp4"))) if not any(b in c.stem.lower() for b in banned_arya)][:3]
        if not active_clips and flow_dir.exists():
            active_clips = sorted(list(flow_dir.rglob("*.mp4")))[:3]

        num_clips = len(active_clips)
        slice_dur = duration / float(num_clips)

        # 4. Filter Complex building
        # NahhJadi Style: Top Dark Rounded Container with Bold Title
        # Funrice Style: Bottom High-Impact Contrarian Hook with Thick Black Border
        headline = topic["title"]
        hook_sub = topic["hook_subtitle"]

        inputs = []
        filter_parts = []
        for idx, clip in enumerate(active_clips):
            inputs.extend(["-stream_loop", "2", "-i", str(clip)])
            filter_parts.append(
                f"[{idx}:v]trim=0:{slice_dur:.2f},setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30[v{idx}];"
            )

        concat_in = "".join(f"[v{i}]" for i in range(num_clips))
        concat_filter = f"{concat_in}concat=n={num_clips}:v=1:a=0[vbase];"

        # Styling typography
        text_overlay = (
            f"[vbase]"
            f"drawbox=y=160:color=black@0.90:width=iw-120:x=60:height=110:t=fill,"
            f"drawtext=text='{headline}':fontcolor=white:fontsize=50:x=(w-text_w)/2:y=188:shadowcolor=black:shadowx=2:shadowy=2,"
            f"drawtext=text='{hook_sub}':fontcolor=yellow:fontsize=46:x=(w-text_w)/2:y=h-480:borderw=4:bordercolor=black,"
            f"drawtext=text='Kucing kamu di rumah begini juga? 💬':fontcolor=white:fontsize=42:x=(w-text_w)/2:y=h-410:borderw=4:bordercolor=black,"
            f"drawtext=text='@DoniesDaily':fontcolor=white@0.75:fontsize=32:x=(w-text_w)/2:y=h-340:borderw=2:bordercolor=black"
            f"[vout]"
        )

        full_filter = "".join(filter_parts) + concat_filter + text_overlay

        cmd_video = [
            "ffmpeg", "-y",
            *inputs,
            "-i", str(master_audio),
            "-filter_complex", full_filter,
            "-map", "[vout]",
            "-map", f"{num_clips}:a",
            "-c:v", "libx264", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{duration + 0.4:.2f}",
            "-shortest",
            str(output_path)
        ]

        logger.info(f"🎬 Rendering Master Shorts to {output_path}...")
        subprocess.run(cmd_video, check=True)
        logger.info("✅ Rendering complete!")
        return output_path

    def run_production_cycle(
        self,
        topic_index: Optional[int] = None,
        publish_mode: str = "public",
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Full pipeline: Select -> Generate Script & Voice (ElevenLabs Kak Ceria) -> Remotion Studio Render -> Publish to YouTube."""
        # Delegates to the Master Remotion & Google Flow Pipeline for consistent golden standard output
        from src.doni_remotion_flow_pipeline import DoniRemotionFlowPipeline
        import asyncio

        pipeline = DoniRemotionFlowPipeline()
        topic = self.pick_story(topic_index)
        t_key = topic.get("topic_key")
        logger.info(f"🎯 Selected Master Story: {topic['title']} ({t_key})")

        res = asyncio.run(pipeline.run(
            topic_key=t_key,
            publish=(not dry_run),
            privacy_status=publish_mode
        ))
        return res

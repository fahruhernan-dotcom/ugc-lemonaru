"""End-to-End Orchestrator: Generate Cat Shorts Video & Upload to YouTube Studio.
"""

import asyncio
import json
import logging
import random
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.cat_shorts_maker import build_cat_short
from src.youtube_publisher import YouTubePublisher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cat_youtube_pipeline")

CAT_SCRIPTS = [
    {
        "title": "Kenapa Kucing Mendengkur? 🐱",
        "script": "Tahukah kamu? Kucing mendengkur bukan cuma saat bahagia, tapi getarannya juga bisa menyembuhkan luka dan menenangkan diri!",
        "desc": "Fakta unik kenapa kucing suka mendengkur! 🐱✨ #Shorts #CatFacts #KucingLucu #KucingOyen #DoniesDaily",
        "image_url": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=1080&q=80"
    },
    {
        "title": "Rahasia Kucing Suka Bikin Roti! 🍞",
        "script": "Pernah lihat kucing kamu mijit-mijit kasur kayak bikin roti? Ternyata itu kebiasaan bawaan sejak bayi untuk merasakan kenyamanan!",
        "desc": "Arti di balik kucing yang suka memijat atau kneading! 🐾🍞 #Shorts #KucingGemoy #CatLovers #DoniesDaily",
        "image_url": "https://images.unsplash.com/photo-1573865526739-10659fec78a5?w=1080&q=80"
    },
    {
        "title": "Kucing Tidur 16 Jam Sehari?! 😴",
        "script": "Kucing menghabiskan tujuh puluh persen hidupnya hanya untuk tidur. Jangan iri ya, mereka tidur lama demi menghemat energi berburu!",
        "desc": "Fakta tidur kucing yang bikin kaum rebahan relate! 😴🐱 #Shorts #KucingLucu #KucingRebahan #DoniesDaily",
        "image_url": "https://images.unsplash.com/photo-1543852786-1cf6624b9987?w=1080&q=80"
    }
]

async def run_pipeline(publish_mode: str = "public"):
    logger.info("🚀 Starting Autonomous Cat Shorts Pipeline...")
    
    # 1. Pick a topic
    item = random.choice(CAT_SCRIPTS)
    logger.info(f"Selected Topic: {item['title']}")
    
    # 2. Download Image
    temp_img = Path("/tmp/current_cat.jpg")
    import urllib.request
    logger.info("Downloading cat visual asset...")
    urllib.request.urlretrieve(item["image_url"], str(temp_img))
    
    # 3. Render 9:16 Shorts Video
    video_out = ROOT_DIR / "output" / f"cat_short_{random.randint(1000, 9999)}.mp4"
    logger.info(f"Rendering video to {video_out}...")
    build_cat_short(
        script_text=item["script"],
        image_path=str(temp_img),
        output_video_path=str(video_out),
        title_caption=item["title"]
    )
    
    # 4. Upload to YouTube Studio
    logger.info("Connecting to YouTube Studio via Playwright...")
    pub = YouTubePublisher()
    upload_res = await pub.upload_shorts(
        video_path=str(video_out),
        title=f"{item['title']} #Shorts",
        description=item["desc"],
        publish_mode=publish_mode,
        headless=True
    )
    
    logger.info(f"Upload Result: {json.dumps(upload_res, indent=2)}")
    return upload_res

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "public"
    res = asyncio.run(run_pipeline(publish_mode=mode))
    print("\n=== PIPELINE FINISHED ===")
    print(json.dumps(res, indent=2))

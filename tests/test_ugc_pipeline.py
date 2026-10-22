"""Unit and Integration Tests for the Master UgcProductionEngine."""

import json
from pathlib import Path
import pytest

from src.models import Product
from src.ugc_pipeline import UgcProductionEngine
from src.repository import LocalRepository


@pytest.fixture
def local_repo(tmp_path):
    storage_file = tmp_path / "test_store.json"
    return LocalRepository(storage_path=storage_file)


@pytest.fixture
def ugc_engine(local_repo, tmp_path):
    engine = UgcProductionEngine(repo=local_repo)
    engine.packages_dir = tmp_path / "test_packages"
    engine.packages_dir.mkdir(parents=True, exist_ok=True)
    return engine


@pytest.fixture
def sample_peplum_product():
    return Product(
        product_id="TEST-GARMENT-05",
        name="CLASSY - TESSA Peplum Top Wanita Blouse Tanpa Lengan",
        category="fashion_peplum_top",
        price_idr=129000.0,
        commission_rate=0.15,
        sales_count=1840,
        rating=4.9,
        shop_name="CLASSY Official",
        stock_available=250
    )


def test_get_or_create_product(ugc_engine):
    prod = ugc_engine.get_or_create_product(
        product_id="TEST-NEW-01",
        name="Blouse Crop Katun",
        category="fashion_top_outerwear",
        price_idr=99000.0,
        shop_name="Daily Chic"
    )
    assert prod.product_id == "TEST-NEW-01"
    assert prod.price_idr == 99000.0

    # Retrieve again should return same instance
    cached = ugc_engine.get_or_create_product(product_id="TEST-NEW-01")
    assert cached.name == "Blouse Crop Katun"


def test_produce_ugc_package_dry_run(ugc_engine, sample_peplum_product, tmp_path):
    # Create mock product image
    mock_img = tmp_path / "test_peplum.jpg"
    from PIL import Image
    im = Image.new("RGB", (720, 1280), color=(255, 255, 255))
    im.save(mock_img)

    # Produce package
    res = ugc_engine.produce_ugc_package(
        sample_peplum_product,
        raw_image_path=mock_img,
        dry_run=True,
        generate_voiceover=False  # test without network TTS
    )

    assert res["success"] is True
    pkg_path = Path(res["package_dir"])
    assert pkg_path.exists()

    # Verify standard package files exist
    assert (pkg_path / "copywriting.txt").exists()
    assert (pkg_path / "caption.txt").exists()
    assert (pkg_path / "brief.json").exists()
    assert (pkg_path / "reference_isolated.jpg").exists()

    # Verify copywriting contains dynamic peplum cues
    copy_text = (pkg_path / "copywriting.txt").read_text(encoding="utf-8")
    assert "peplum" in copy_text.lower() or "pinggang" in copy_text.lower()
    assert "keranjang kuning" in copy_text.lower()

    # Verify brief metadata
    brief_data = json.loads((pkg_path / "brief.json").read_text(encoding="utf-8"))
    assert brief_data["product_id"] == "TEST-GARMENT-05"
    assert len(brief_data["motion_timeline"]) == 4

    # Verify database persistence
    gen_record = ugc_engine.repo.get_ugc_generation(res["generation_id"])
    assert gen_record is not None
    assert gen_record.quality_score == 8.5


def test_produce_ugc_package_with_audio_muxing(ugc_engine, sample_peplum_product, tmp_path):
    from src.media_muxer import MediaMuxer
    import subprocess

    ffmpeg_bin = MediaMuxer.get_ffmpeg_binary()
    dummy_video = tmp_path / "mock_vid.mp4"
    dummy_audio = tmp_path / "mock_audio.mp3"

    # Create short 2s test video and audio
    subprocess.run([
        ffmpeg_bin, "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=24",
        "-c:v", "libx264", "-preset", "ultrafast", str(dummy_video)
    ], capture_output=True, check=True)
    subprocess.run([
        ffmpeg_bin, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
        "-c:a", "libmp3lame", str(dummy_audio)
    ], capture_output=True, check=True)

    # Mock product image
    from PIL import Image
    mock_img = tmp_path / "test_peplum2.jpg"
    im = Image.new("RGB", (720, 1280), color=(255, 255, 255))
    im.save(mock_img)

    # Produce package with mock video and pre-populated audio
    res = ugc_engine.produce_ugc_package(
        sample_peplum_product,
        raw_image_path=mock_img,
        video_source_path=dummy_video,
        dry_run=False,
        generate_voiceover=False,
        script_mode="snackable_10s"
    )

    pkg_path = Path(res["package_dir"])
    target_vid = pkg_path / "video.mp4"
    assert target_vid.exists()

    # Pre-populate audio in package and re-run muxing check
    shutil_dest_audio = pkg_path / "audio_voiceover.mp3"
    import shutil
    shutil.copy2(dummy_audio, shutil_dest_audio)

    # Run muxing
    MediaMuxer.mux_video_and_audio(
        video_path=dummy_video,
        audio_path=shutil_dest_audio,
        output_path=target_vid
    )

    assert MediaMuxer.verify_has_audio(target_vid) is True

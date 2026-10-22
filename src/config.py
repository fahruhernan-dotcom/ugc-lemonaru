"""Configuration manager for Velora AI / AI Fashion Affiliate Engine."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# Supabase Credentials (optional for local/test mode)
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

# App settings
APP_ENV = os.getenv("APP_ENV", "development").strip()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip()
APP_NAME = os.getenv("APP_NAME", "Velora AI Studio").strip()

# Paths
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(ROOT_DIR / "output")))
PACKAGES_DIR = Path(os.getenv("PACKAGES_DIR", str(ROOT_DIR / "ready_to_publish")))
PACKAGES_PENDING_DIR = Path(os.getenv("PACKAGES_PENDING_DIR", str(PACKAGES_DIR / "pending")))
PACKAGES_POSTED_DIR = Path(os.getenv("PACKAGES_POSTED_DIR", str(PACKAGES_DIR / "posted")))
DATA_DIR = Path(os.getenv("DATA_DIR", str(ROOT_DIR / "data")))
TEMP_DIR = Path(os.getenv("TEMP_DIR", str(DATA_DIR / "temp")))
FLOW_CLIPS_DIR = Path(os.getenv("FLOW_CLIPS_DIR", str(TEMP_DIR / "flow_clips")))

# Video Storage & Lifecycle Retention Limits (VPS protection)
MAX_VIDEO_STORAGE_MB = float(os.getenv("MAX_VIDEO_STORAGE_MB", "2048.0"))  # 2 GB cap
RETENTION_POSTED_HOURS = int(os.getenv("RETENTION_POSTED_HOURS", "72"))    # 3 days
RETENTION_TEMP_HOURS = int(os.getenv("RETENTION_TEMP_HOURS", "24"))        # 1 day

# Flow Agent Paths
FLOW_AGENT_DIR = ROOT_DIR / "tools" / "flow-agent" / "flow-agent"
FLOW_BIN_PATH = FLOW_AGENT_DIR / "bin" / "flow-windows.exe"
FLOW_EXTENSION_DIR = ROOT_DIR / "tools" / "flow-agent" / "flow-extension"

# Ensure directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
PACKAGES_PENDING_DIR.mkdir(parents=True, exist_ok=True)
PACKAGES_POSTED_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
FLOW_CLIPS_DIR.mkdir(parents=True, exist_ok=True)

# Guard against Drive C filling by routing TEMP/TMP to Drive D
os.environ["TEMP"] = str(TEMP_DIR)
os.environ["TMP"] = str(TEMP_DIR)

# Scoring Gates
SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "70.0"))
MIN_STOCK_GATE = int(os.getenv("MIN_STOCK_GATE", "10"))
MIN_COMMISSION_RATE_GATE = float(os.getenv("MIN_COMMISSION_RATE_GATE", "0.05"))
MIN_PRICE_IDR_GATE = float(os.getenv("MIN_PRICE_IDR_GATE", "25000.0"))


# TikTok Shop Open API
TIKTOK_SHOP_APP_KEY = os.getenv("TIKTOK_SHOP_APP_KEY", "").strip()
TIKTOK_SHOP_APP_SECRET = os.getenv("TIKTOK_SHOP_APP_SECRET", "").strip()
TIKTOK_SHOP_REDIRECT_URI = os.getenv("TIKTOK_SHOP_REDIRECT_URI", "https://127.0.0.1:3000/callback").strip()


def has_supabase_credentials() -> bool:
    """Returns True if valid Supabase URL and Key are configured."""
    return bool(SUPABASE_URL and (SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY))


def has_tiktok_shop_credentials() -> bool:
    """Returns True if valid TikTok Shop App Key and Secret are configured."""
    return bool(TIKTOK_SHOP_APP_KEY and TIKTOK_SHOP_APP_SECRET)

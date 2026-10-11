"""
Configuration settings for TakeoutRoulette
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / ".cache"
DIST_DIR = BASE_DIR / "dist"
INDEX_HTML = BASE_DIR / "index.html"

# Load local environment if present (.env is gitignored)
load_dotenv(BASE_DIR / ".env")

# Station Configuration (configurable via environment variables)
DEFAULT_STATION = {
    "id": os.getenv("STATION_ID", "station"),
    "name": os.getenv("STATION_NAME", "Local Station"),
    "name_ja": os.getenv("STATION_NAME_JA", "駅"),
    "lat": float(os.getenv("STATION_LAT", "35.681236")),
    "lng": float(os.getenv("STATION_LNG", "139.767125")),
    "tabelog_area_path": os.getenv("TABELOG_AREA_PATH", ""),
    "tabelog_station_id": os.getenv("TABELOG_STATION_ID", ""),
    "landmarks": []
}

STATION_PRESETS = {
    DEFAULT_STATION["id"]: DEFAULT_STATION
}

# Network Scraper Config
REQUEST_DELAY_MIN = 1.0
REQUEST_DELAY_MAX = 2.2
HTTP_TIMEOUT = 12

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
]

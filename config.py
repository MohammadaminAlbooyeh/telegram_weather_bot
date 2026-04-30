import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
CITIES_FILE = DATA_DIR / "cities.json"
WEATHER_CACHE_FILE = DATA_DIR / "weatherapi_cache.json"


def get_env_str(name: str) -> str:
    value = os.getenv(name)
    return value if value is not None else ""


TELEGRAM_BOT_TOKEN: str = get_env_str("TELEGRAM_BOT_TOKEN")
WEATHER_API_KEY: str = get_env_str("WEATHER_API_KEY")


def get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except Exception:
        return default


# Optional scheduler configuration (used only when MONITOR_COORDS is set)
MONITOR_COORDS: str = get_env_str("MONITOR_COORDS")
WEATHER_FETCH_INTERVAL_MIN: int = get_env_int("WEATHER_FETCH_INTERVAL_MIN", 10)

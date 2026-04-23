import os
import time
import json
import threading
from typing import List, Tuple
from datetime import datetime

from .met_no import get_locationforecast_compact

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
CACHE_FILE = os.path.join(CACHE_DIR, 'met_cache.json')

def _ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)


def parse_coords_list(coords_str: str) -> List[Tuple[float, float]]:
    """Parse semicolon-separated coords 'lat,lon;lat,lon' into list of tuples."""
    out = []
    if not coords_str:
        return out
    for part in coords_str.split(';'):
        part = part.strip()
        if not part:
            continue
        try:
            lat_s, lon_s = part.split(',', 1)
            lat = float(lat_s.strip())
            lon = float(lon_s.strip())
            out.append((lat, lon))
        except Exception:
            continue
    return out


def load_cache() -> dict:
    _ensure_cache_dir()
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(obj: dict):
    _ensure_cache_dir()
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def fetch_and_cache_all(coords: List[Tuple[float, float]]):
    """Fetch MET data for each coord and cache it."""
    if not coords:
        return
    cache = load_cache()
    for lat, lon in coords:
        key = f"{lat},{lon}"
        try:
            data = get_locationforecast_compact(lat, lon)
            cache[key] = {
                'lat': lat,
                'lon': lon,
                'fetched_at': datetime.utcnow().isoformat() + 'Z',
                'data': data,
            }
        except Exception as e:
            # keep previous cache if fetch fails
            cache.setdefault(key, {})
            cache[key]['error'] = str(e)
    save_cache(cache)


def get_cached(lat: float, lon: float):
    cache = load_cache()
    return cache.get(f"{lat},{lon}")


class SchedulerThread(threading.Thread):
    def __init__(self, coords: List[Tuple[float, float]], interval_min: int = 10):
        super().__init__(daemon=True)
        self.coords = coords
        self.interval = max(1, int(interval_min))
        self._stop = threading.Event()

    def run(self):
        while not self._stop.is_set():
            try:
                fetch_and_cache_all(self.coords)
            except Exception:
                pass
            # Sleep interval minutes
            for _ in range(self.interval * 60):
                if self._stop.is_set():
                    break
                time.sleep(1)

    def stop(self):
        self._stop.set()


def start_background_scheduler_from_env():
    """Start scheduler using environment variables:
    - MONITOR_COORDS: semicolon-separated list of lat,lon pairs
    - MET_FETCH_INTERVAL_MIN: minutes between fetches (default 10)
    """
    coords_str = os.getenv('MONITOR_COORDS', '')
    coords = parse_coords_list(coords_str)
    if not coords:
        return None
    try:
        interval = int(os.getenv('MET_FETCH_INTERVAL_MIN', '10'))
    except Exception:
        interval = 10

    thr = SchedulerThread(coords=coords, interval_min=interval)
    thr.start()
    return thr

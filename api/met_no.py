import os
import requests
from dotenv import load_dotenv

load_dotenv()

MET_USER_AGENT = os.getenv('MET_USER_AGENT') or 'telegram_weather_bot/1.0 (contact: youremail@example.com)'
BASE_URL = 'https://api.met.no/weatherapi'


def get_locationforecast_compact(lat: float, lon: float, timeout: int = 10) -> dict:
    """Fetch MET Norway 'locationforecast/2.0/compact' for given coordinates.

    Returns the parsed JSON response (dict). Raises requests.exceptions.HTTPError on bad responses.
    MET Norway requires a proper User-Agent header identifying the application.
    """
    headers = {
        'User-Agent': MET_USER_AGENT,
        'Accept': 'application/json'
    }

    url = f"{BASE_URL}/locationforecast/2.0/compact"
    params = {'lat': lat, 'lon': lon}

    resp = requests.get(url, headers=headers, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def get_all_timeseries(lat: float, lon: float, timeout: int = 10) -> list:
    """Return the list of timeseries entries (each contains time and weather data).

    Example entry: {"time": "2026-04-22T12:00:00Z", "data": {...}}
    """
    data = get_locationforecast_compact(lat, lon, timeout=timeout)
    return data.get('properties', {}).get('timeseries', [])


if __name__ == '__main__':
    # Quick manual test: run `python api/met_no.py 59.91 10.75`
    import sys
    if len(sys.argv) >= 3:
        try:
            lat = float(sys.argv[1])
            lon = float(sys.argv[2])
        except ValueError:
            print('Usage: python api/met_no.py <lat> <lon>')
            sys.exit(1)

        try:
            ts = get_all_timeseries(lat, lon)
            print(f"Received {len(ts)} timeseries entries")
            # Print first entry as an example
            if ts:
                import json
                print(json.dumps(ts[0], indent=2))
        except Exception as e:
            print('Error fetching data:', e)
    else:
        print('Usage: python api/met_no.py <lat> <lon>')

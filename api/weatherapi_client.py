import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.weatherapi.com/v1"
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")


def get_current_weather(query: str, timeout: int = 10, aqi: str = "yes") -> dict:
    """Fetch current weather from WeatherAPI for a query (city name, zip, or lat,lon)."""
    if not query or not str(query).strip():
        raise ValueError("query must not be empty")
    if not WEATHER_API_KEY:
        raise RuntimeError("WEATHER_API_KEY is not set. Please configure it in your environment or .env file.")

    params = {
        "key": WEATHER_API_KEY,
        "q": str(query).strip(),
        "aqi": aqi,
    }
    resp = requests.get(f"{BASE_URL}/current.json", params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def get_current_weather_by_coords(lat: float, lon: float, timeout: int = 10, aqi: str = "yes") -> dict:
    """Fetch current weather from WeatherAPI for latitude/longitude."""
    return get_current_weather(f"{lat},{lon}", timeout=timeout, aqi=aqi)


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) >= 2:
        q = " ".join(sys.argv[1:]).strip()
        try:
            result = get_current_weather(q)
            print(json.dumps(result, indent=2))
        except Exception as exc:
            print("Error fetching weather data:", exc)
    else:
        print("Usage: python api/weatherapi_client.py <city|lat,lon>")
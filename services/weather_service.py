from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from api import weatherapi_client
from config import CITIES_FILE
from utils.logger import get_logger

logger = get_logger(__name__)


class WeatherService:
    def __init__(self, cities_file: Path | None = None):
        self.cities_file = Path(cities_file or CITIES_FILE)
        self.city_fallback = self._load_city_fallbacks()

    def _normalize_city_key(self, city_name: str) -> str:
        return " ".join(str(city_name).strip().lower().split())

    def _load_city_fallbacks(self) -> dict:
        """Load built-in city coordinates from `data/cities.json`."""
        fallback: dict[str, tuple[float, float, str, str]] = {}

        try:
            with self.cities_file.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception:
            logger.exception("Unable to load city catalog from %s", self.cities_file)
            return fallback

        for item in payload.get("cities", []):
            key = self._normalize_city_key(item.get("key") or item.get("name") or "")
            try:
                fallback[key] = (
                    float(item["lat"]),
                    float(item["lon"]),
                    str(item.get("name") or item.get("key") or ""),
                    str(item.get("country") or ""),
                )
            except Exception:
                continue

        return fallback

    def _get_fallback_coords(self, city_name: str) -> Optional[tuple[float, float, str, str]]:
        return self.city_fallback.get(self._normalize_city_key(city_name))

    def get_aqi_from_weatherapi(self, air_quality: Any) -> Optional[dict]:
        """Normalize WeatherAPI air quality payload to the bot's internal AQI shape."""
        if not isinstance(air_quality, dict):
            return None

        us_epa = air_quality.get("us-epa-index")
        if us_epa is None:
            return None

        try:
            us_epa = int(us_epa)
        except Exception:
            return None

        if us_epa <= 1:
            idx, desc = 1, "Good"
        elif us_epa == 2:
            idx, desc = 2, "Moderate"
        elif us_epa == 3:
            idx, desc = 3, "Unhealthy for Sensitive Groups"
        elif us_epa == 4:
            idx, desc = 4, "Unhealthy"
        else:
            idx, desc = 5, "Very Unhealthy / Hazardous"

        return {
            "aqi": idx,
            "description": f"{desc} (US EPA {us_epa})",
            "components": {
                "pm2_5": air_quality.get("pm2_5"),
                "pm10": air_quality.get("pm10"),
                "no2": air_quality.get("no2"),
                "o3": air_quality.get("o3"),
                "co": air_quality.get("co"),
                "so2": air_quality.get("so2"),
            },
        }

    def get_weather_by_city(self, city_name: str) -> Optional[dict]:
        """Get current weather data for a city"""
        try:
            q = city_name.strip()
            if not q:
                return None

            payload = weatherapi_client.get_current_weather(q)

            if not payload:
                fallback = self._get_fallback_coords(q)
                if fallback:
                    lat, lon, _, _ = fallback
                    payload = weatherapi_client.get_current_weather_by_coords(lat, lon)

            if not payload:
                return None

            location = payload.get("location", {})
            current = payload.get("current", {})
            condition = current.get("condition", {})

            desc_lower = str(condition.get("text") or "").lower()
            if "thunder" in desc_lower:
                weather_id = 200
            elif any(k in desc_lower for k in ("snow", "sleet", "blizzard", "ice")):
                weather_id = 600
            elif any(k in desc_lower for k in ("rain", "drizzle", "shower")):
                weather_id = 500
            elif any(k in desc_lower for k in ("fog", "mist", "haze", "smoke", "dust", "sand")):
                weather_id = 700
            elif any(k in desc_lower for k in ("cloud", "overcast", "partly cloudy")):
                weather_id = 801
            elif any(k in desc_lower for k in ("sunny", "clear")):
                weather_id = 800
            else:
                weather_id = 800
            description = condition.get("text") or "Weather"

            # Build OpenWeather-like dict expected by format_weather_message
            weather_data = {
                "name": location.get("name") or city_name,
                "sys": {"country": location.get("country") or ""},
                "main": {
                    "temp": current.get("temp_c", 0.0),
                    "feels_like": current.get("feelslike_c", current.get("temp_c", 0.0)),
                    "humidity": current.get("humidity"),
                    "pressure": current.get("pressure_mb"),
                },
                "weather": [{"description": description, "id": weather_id}],
                "wind": {"speed": current.get("wind_kph", 0.0) / 3.6},
            }

            aqi_info = self.get_aqi_from_weatherapi(current.get("air_quality"))
            if aqi_info:
                weather_data["aqi"] = aqi_info

            return weather_data

        except Exception:
            logger.exception("Failed to get weather by city")
            return None

    def format_weather_message(self, weather_data: Optional[dict]) -> str:
        """Format weather data into a readable message

        Accepts optional `aqi_data` inside `weather_data` under key 'aqi'
        (added by `get_aqi_by_coords` when available).
        """
        if not weather_data:
            return "❌ Sorry, I couldn't fetch the weather data. Please try again."

        try:
            city = weather_data["name"]
            country = weather_data["sys"]["country"]
            temp = round(weather_data["main"]["temp"])
            feels_like = round(weather_data["main"]["feels_like"])
            humidity = weather_data["main"]["humidity"]
            pressure = weather_data["main"]["pressure"]
            description = weather_data["weather"][0]["description"].title()
            wind_speed = weather_data["wind"]["speed"]
            wind_speed = f"{wind_speed:.2f}"

            # Get weather emoji based on weather condition ID
            weather_id = weather_data["weather"][0]["id"]
            emoji = self.get_weather_emoji(weather_id)

            message = f"{emoji} **Weather in {city}, {country}**\n\n"
            message += f"🌡️ **Temperature:** {temp}°C (feels like {feels_like}°C)\n"
            message += f"📝 **Description:** {description}\n"
            message += f"💧 **Humidity:** {humidity}%\n"
            message += f"🔽 **Pressure:** {pressure} hPa\n"
            message += f"💨 **Wind Speed:** {wind_speed} m/s\n"

            # Include AQI if provided
            aqi_info = weather_data.get("aqi") if isinstance(weather_data, dict) else None
            if aqi_info:
                aqi_idx = aqi_info.get("aqi")
                aqi_desc = aqi_info.get("description")
                message += f"\n🌫️ **Air Quality (AQI):** {aqi_idx} — {aqi_desc}\n"

                # Show pollutant concentrations when available
                comps = aqi_info.get("components") or {}

                def fmt(v: Any) -> str:
                    try:
                        return f"{float(v):.1f}"
                    except Exception:
                        return "N/A"

                pm25 = fmt(comps.get("pm2_5"))
                pm10 = fmt(comps.get("pm10"))
                no2 = fmt(comps.get("no2"))
                o3 = fmt(comps.get("o3"))
                co = fmt(comps.get("co"))
                so2 = fmt(comps.get("so2"))

                if any(x != "N/A" for x in (pm25, pm10, no2, o3, co, so2)):
                    message += f"• PM2.5: {pm25} µg/m³ | PM10: {pm10} µg/m³\n"
                    message += f"• NO₂: {no2} µg/m³ | O₃: {o3} µg/m³\n"

                # Health recommendation based on AQI index
                rec_map = {
                    1: "Air quality is good for outdoor activities.",
                    2: "Air quality is fair; sensitive individuals should consider reducing prolonged outdoor exertion.",
                    3: "Air quality is moderate; people with respiratory or heart conditions should reduce prolonged outdoor exertion.",
                    4: "Air quality is poor; consider avoiding outdoor activities.",
                    5: "Air quality is very poor; avoid outdoor exposure if possible.",
                }
                recommendation = rec_map.get(aqi_idx, None)
                if recommendation:
                    message += f"\n⚠️ Recommendation: {recommendation}\n"

            # Add timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message += f"\n🕐 *Updated: {timestamp}*"

            return message

        except KeyError as e:
            logger.error(f"Error formatting weather message: {e}")
            return "❌ Error formatting weather data. Please try again."

    def get_weather_emoji(self, weather_id: int) -> str:
        """Get appropriate emoji based on weather condition ID"""
        if weather_id < 300:
            return "⛈️"  # Thunderstorm
        elif weather_id < 400:
            return "🌧️"  # Drizzle
        elif weather_id < 600:
            return "🌧️"  # Rain
        elif weather_id < 700:
            return "❄️"  # Snow
        elif weather_id < 800:
            return "🌫️"  # Atmosphere (fog, etc.)
        elif weather_id == 800:
            return "☀️"  # Clear sky
        else:
            return "☁️"  # Clouds

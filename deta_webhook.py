import os
import json
import requests
from datetime import datetime
from typing import Optional

# Environment variables (set as Deta secrets or in environment)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
WEATHER_BASE_URL = 'http://api.openweathermap.org/data/2.5'


def _get_weather(city_name: str):
    try:
        resp = requests.get(
            f"{WEATHER_BASE_URL}/weather",
            params={"q": city_name, "appid": OPENWEATHER_API_KEY, "units": "metric"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _get_aqi(lat: float, lon: float):
    try:
        resp = requests.get(
            f"{WEATHER_BASE_URL}/air_pollution",
            params={"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if 'list' in data and len(data['list']) > 0:
            info = data['list'][0]
            aqi_idx = info.get('main', {}).get('aqi')
            comps = info.get('components', {})
            aqi_map = {1: 'Good', 2: 'Fair', 3: 'Moderate', 4: 'Poor', 5: 'Very Poor'}
            return {'aqi': aqi_idx, 'description': aqi_map.get(aqi_idx, 'Unknown'), 'components': comps}
        return None
    except Exception:
        return None


def _format_message(weather_data: dict, aqi_info: Optional[dict]) -> str:
    try:
        city = weather_data.get('name')
        country = weather_data.get('sys', {}).get('country')
        temp = round(weather_data.get('main', {}).get('temp', 0))
        feels = round(weather_data.get('main', {}).get('feels_like', 0))
        humidity = weather_data.get('main', {}).get('humidity', 'N/A')
        pressure = weather_data.get('main', {}).get('pressure', 'N/A')
        description = weather_data.get('weather', [{}])[0].get('description', '').title()
        wind = weather_data.get('wind', {}).get('speed', 'N/A')

        msg = f"**Weather in {city}, {country}**\n\n"
        msg += f"🌡️ **Temperature:** {temp}°C (feels like {feels}°C)\n"
        msg += f"📝 **Description:** {description}\n"
        msg += f"💧 **Humidity:** {humidity}%\n"
        msg += f"🔽 **Pressure:** {pressure} hPa\n"
        msg += f"💨 **Wind Speed:** {wind} m/s\n"

        if aqi_info:
            aqi_idx = aqi_info.get('aqi')
            aqi_desc = aqi_info.get('description')
            msg += f"\n🌫️ **Air Quality (AQI):** {aqi_idx} — {aqi_desc}\n"
            comps = aqi_info.get('components') or {}
            def fmt(v):
                try:
                    return f"{float(v):.1f}"
                except Exception:
                    return "N/A"
            pm25 = fmt(comps.get('pm2_5'))
            pm10 = fmt(comps.get('pm10'))
            no2 = fmt(comps.get('no2'))
            o3 = fmt(comps.get('o3'))
            if any(x != "N/A" for x in (pm25, pm10, no2, o3)):
                msg += f"• PM2.5: {pm25} µg/m³ | PM10: {pm10} µg/m³\n"
                msg += f"• NO₂: {no2} µg/m³ | O₃: {o3} µg/m³\n"
            rec_map = {
                1: "Air quality is good for outdoor activities.",
                2: "Air quality is fair; sensitive individuals should reduce prolonged outdoor exertion.",
                3: "Air quality is moderate; people with respiratory or heart conditions should reduce prolonged outdoor exertion.",
                4: "Air quality is poor; consider avoiding outdoor activities.",
                5: "Air quality is very poor; avoid outdoor exposure if possible."
            }
            rec = rec_map.get(aqi_idx)
            if rec:
                msg += f"\n⚠️ Recommendation: {rec}\n"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg += f"\n🕐 Updated: {timestamp}"
        return msg
    except Exception:
        return "❌ Error formatting data."


def _send_telegram(chat_id: int, text: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except Exception:
        pass


def handler(event, context=None):
    """Deta-compatible handler. Expects `event` to contain the raw request body (Telegram update).

    Deploy this file to Deta and configure `TELEGRAM_BOT_TOKEN` and `OPENWEATHER_API_KEY` as secrets.
    """
    try:
        body = event.get('body') if isinstance(event, dict) else event
        if isinstance(body, str):
            update = json.loads(body)
        else:
            update = body or {}

        message = update.get('message') or update.get('edited_message')
        if not message:
            return {"statusCode": 200, "body": "no message"}

        text = message.get('text', '').strip()
        chat = message.get('chat', {})
        chat_id = chat.get('id')
        if not text or not chat_id:
            return {"statusCode": 200, "body": "no text or chat"}

        # Short initial reply (optional): Telegram will show typing if you reply fast
        weather = _get_weather(text)
        if not weather or weather.get('cod') != 200:
            _send_telegram(chat_id, "❌ City not found. Please check the spelling and try again.")
            return {"statusCode": 200, "body": "city not found"}

        coord = weather.get('coord', {})
        lat = coord.get('lat')
        lon = coord.get('lon')
        aqi = None
        if lat is not None and lon is not None:
            aqi = _get_aqi(lat, lon)

        msg = _format_message(weather, aqi)
        _send_telegram(chat_id, msg)

        return {"statusCode": 200, "body": "ok"}

    except Exception as e:
        return {"statusCode": 200, "body": "error"}

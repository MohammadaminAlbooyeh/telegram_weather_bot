import os
import logging
from datetime import datetime

import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Ensure project root is on sys.path so `from api import ...` works when running src/main.py directly
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import scheduler
from api import met_no

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

class WeatherBot:
    def __init__(self):
        self.application = None

        # Fallback coordinates when geocoding providers are unavailable.
        # Format: normalized city -> (lat, lon, display_name, country_code)
        self.city_fallback = {
            'turin': (45.0703, 7.6869, 'Turin', 'IT'),
            'torino': (45.0703, 7.6869, 'Turin', 'IT'),
            'milan': (45.4642, 9.1900, 'Milan', 'IT'),
            'rome': (41.9028, 12.4964, 'Rome', 'IT'),
            'paris': (48.8566, 2.3522, 'Paris', 'FR'),
            'london': (51.5072, -0.1276, 'London', 'GB'),
            'berlin': (52.5200, 13.4050, 'Berlin', 'DE'),
            'madrid': (40.4168, -3.7038, 'Madrid', 'ES'),
            'new york': (40.7128, -74.0060, 'New York', 'US'),
            'tokyo': (35.6762, 139.6503, 'Tokyo', 'JP'),
        }

    def get_aqi_by_coords(self, lat: float, lon: float) -> dict:
        """Fetch AQI and pollutant data using Open-Meteo Air Quality API (no API key)."""
        try:
            url = "https://air-quality-api.open-meteo.com/v1/air-quality"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "european_aqi,pm2_5,pm10,nitrogen_dioxide,ozone,carbon_monoxide,sulphur_dioxide",
                "timezone": "auto",
            }
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            payload = resp.json() or {}

            current = payload.get("current", {})
            eu_aqi = current.get("european_aqi")
            if eu_aqi is None:
                return None

            eu_aqi = float(eu_aqi)

            if eu_aqi <= 20:
                idx, desc = 1, "Good"
            elif eu_aqi <= 40:
                idx, desc = 2, "Fair"
            elif eu_aqi <= 60:
                idx, desc = 3, "Moderate"
            elif eu_aqi <= 80:
                idx, desc = 4, "Poor"
            else:
                idx, desc = 5, "Very Poor"

            return {
                "aqi": idx,
                "description": f"{desc} (EU AQI {eu_aqi:.0f})",
                "components": {
                    "pm2_5": current.get("pm2_5"),
                    "pm10": current.get("pm10"),
                    "no2": current.get("nitrogen_dioxide"),
                    "o3": current.get("ozone"),
                    "co": current.get("carbon_monoxide"),
                    "so2": current.get("sulphur_dioxide"),
                },
            }
        except Exception as e:
            logger.warning("AQI lookup failed: %s", e)
            return None
    
    def get_weather_by_city(self, city_name: str) -> dict:
        """Get current weather data for a city"""
        # Use Nominatim (OpenStreetMap) for simple geocoding, then fetch MET Norway data
        try:
            q = city_name.strip()
            if not q:
                return None

            normalized = q.lower().strip()

            lat = lon = None
            display_name = q
            country_code = ''

            # Geocode with Nominatim
            nom_url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": q,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
            }
            # Use MET_USER_AGENT if provided; include mailto per Nominatim policy
            met_ua = os.getenv('MET_USER_AGENT') or 'telegram_weather_bot/1.0 (mailto:youremail@example.com)'
            headers = {"User-Agent": met_ua, "Accept-Language": "en"}

            try:
                r = requests.get(nom_url, params=params, headers=headers, timeout=10)
                r.raise_for_status()
                results = r.json() or []
                if results:
                    loc = results[0]
                    lat = float(loc.get('lat'))
                    lon = float(loc.get('lon'))
                    display_name = loc.get('display_name', city_name)
                    country_code = (loc.get('address', {}) or {}).get('country_code', '').upper()
            except requests.RequestException as geocode_err:
                logger.warning("Nominatim geocoding failed (%s), trying fallback mapping", geocode_err)

            # Fallback mapping for popular cities when geocoding fails
            if lat is None or lon is None:
                fallback = self.city_fallback.get(normalized)
                if not fallback:
                    return None
                lat, lon, display_name, country_code = fallback

            # Fetch MET timeseries
            timeseries = met_no.get_all_timeseries(lat, lon)
            if not timeseries:
                return None

            # Choose the first available timeseries entry
            entry = timeseries[0]
            data = entry.get('data', {})
            instant = data.get('instant', {}).get('details', {})

            temp = instant.get('air_temperature')
            humidity = instant.get('relative_humidity') or instant.get('humidity')
            pressure = instant.get('air_pressure_at_sea_level') or instant.get('pressure')
            wind_speed = instant.get('wind_speed') or instant.get('wind_speed_of_gust') or 0.0

            # Try to get a summary / symbol from next_1_hours or next_6_hours
            symbol = None
            summary = None
            for key in ('next_1_hours', 'next_6_hours', 'next_12_hours'):
                seg = data.get(key)
                if seg and isinstance(seg, dict):
                    summary = seg.get('summary', {})
                    symbol = summary.get('symbol_code')
                    if symbol:
                        break

            def symbol_to_id(sym: str) -> int:
                if not sym:
                    return 800
                s = sym.lower()
                if 'thunder' in s or 'lightning' in s:
                    return 200
                if 'snow' in s or 'sleet' in s:
                    return 600
                if 'rain' in s or 'drizzle' in s or 'shower' in s:
                    return 500
                if 'fog' in s or 'mist' in s or 'cloud' not in s and 'clear' not in s and ('cloud' in s):
                    return 700
                if 'clear' in s:
                    return 800
                if 'cloud' in s or 'overcast' in s:
                    return 801
                return 800

            weather_id = symbol_to_id(symbol)
            description = symbol.replace('_', ' ').title() if symbol else 'Weather'

            # Build OpenWeather-like dict expected by format_weather_message
            weather_data = {
                'name': display_name.split(',')[0],
                'sys': {'country': country_code},
                'main': {
                    'temp': temp if temp is not None else 0.0,
                    'feels_like': temp if temp is not None else 0.0,
                    'humidity': int(humidity) if humidity is not None else None,
                    'pressure': int(pressure) if pressure is not None else None,
                },
                'weather': [{'description': description, 'id': weather_id}],
                'wind': {'speed': float(wind_speed) if wind_speed is not None else 0.0}
            }

            aqi_info = self.get_aqi_by_coords(lat, lon)
            if aqi_info:
                weather_data['aqi'] = aqi_info

            return weather_data

        except Exception as e:
            logger.exception("Failed to get weather by city: %s", e)
            return None
    

    

    
    def format_weather_message(self, weather_data: dict) -> str:
        """Format weather data into a readable message

        Accepts optional `aqi_data` inside `weather_data` under key 'aqi'
        (added by `get_aqi_by_coords` when available).
        """
        if not weather_data:
            return "❌ Sorry, I couldn't fetch the weather data. Please try again."
        
        try:
            city = weather_data['name']
            country = weather_data['sys']['country']
            temp = round(weather_data['main']['temp'])
            feels_like = round(weather_data['main']['feels_like'])
            humidity = weather_data['main']['humidity']
            pressure = weather_data['main']['pressure']
            description = weather_data['weather'][0]['description'].title()
            wind_speed = weather_data['wind']['speed']
            
            # Get weather emoji based on weather condition
            weather_id = weather_data['weather'][0]['id']
            emoji = self.get_weather_emoji(weather_id)
            
            message = f"{emoji} **Weather in {city}, {country}**\n\n"
            message += f"🌡️ **Temperature:** {temp}°C (feels like {feels_like}°C)\n"
            message += f"📝 **Description:** {description}\n"
            message += f"💧 **Humidity:** {humidity}%\n"
            message += f"🔽 **Pressure:** {pressure} hPa\n"
            message += f"💨 **Wind Speed:** {wind_speed} m/s\n"

            # Include AQI if provided
            aqi_info = weather_data.get('aqi') if isinstance(weather_data, dict) else None
            if aqi_info:
                aqi_idx = aqi_info.get('aqi')
                aqi_desc = aqi_info.get('description')
                message += f"\n🌫️ **Air Quality (AQI):** {aqi_idx} — {aqi_desc}\n"
                # Show pollutant concentrations when available
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
                co = fmt(comps.get('co'))
                so2 = fmt(comps.get('so2'))

                if any(x != "N/A" for x in (pm25, pm10, no2, o3, co, so2)):
                    message += f"• PM2.5: {pm25} µg/m³ | PM10: {pm10} µg/m³\n"
                    message += f"• NO₂: {no2} µg/m³ | O₃: {o3} µg/m³\n"

                # Health recommendation based on AQI index
                rec_map = {
                    1: "Air quality is good for outdoor activities.",
                    2: "Air quality is fair; sensitive individuals should consider reducing prolonged outdoor exertion.",
                    3: "Air quality is moderate; people with respiratory or heart conditions should reduce prolonged outdoor exertion.",
                    4: "Air quality is poor; consider avoiding outdoor activities.",
                    5: "Air quality is very poor; avoid outdoor exposure if possible."
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

    # AQI via OpenWeather removed. Use a different AQI provider if needed.
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        welcome_message = f"""👋 Hello {user.first_name}! Welcome to the Weather Bot!

🌤️ I can help you get current weather for any city.

**Commands:**
• Send me a city name (e.g. "London")
• Use /weather <city> for weather
• Use /help for more info

Just type a city name to get started! 🌍"""
        
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """🌤️ Weather Bot Help

**Commands:**
• /start - Start the bot
• /help - Show this help
• /weather <city> - Get weather for a city

**Examples:**
• London
• /weather Paris
• New York

🌍 Just type any city name!"""
        
        await update.message.reply_text(help_message)
    
    async def weather_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /weather command"""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a city name.\n\n"
                "**Usage:** `/weather <city name>`\n"
                "**Example:** `/weather London`",
                parse_mode='Markdown'
            )
            return
        
        city_name = ' '.join(context.args)
        await self.send_weather_info(update, city_name)
    

    

    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages (city names)"""
        message_text = update.message.text
        
        # Check if it looks like a city name (not a command)
        if not message_text.startswith('/'):
            await self.send_weather_info(update, message_text)
        else:
            await update.message.reply_text(
                "❌ Unknown command. Use /help to see available commands."
            )
    
    async def send_weather_info(self, update: Update, city_name: str):
        """Send weather information for a city"""
        # Send "typing" action
        await update.message.reply_chat_action("typing")
        
        await update.message.reply_text(f"🔍 Getting weather for {city_name}...")
        
        weather_data = self.get_weather_by_city(city_name)

        if weather_data:
            weather_message = self.format_weather_message(weather_data)
            await update.message.reply_text(weather_message, parse_mode='Markdown')
        else:
            error_message = (
                "❌ Couldn't resolve that city right now.\n\n"
                "Please try another city format (example: `Turin, Italy`) or try again in a few seconds."
            )
            await update.message.reply_text(error_message, parse_mode='Markdown')
    

    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.message:
            await update.message.reply_text(
                "❌ An error occurred. Please try again later."
            )
    
    def run(self):
        """Run the bot"""
        if not BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
            return
        
        # Note: OpenWeather removed; MET Norway is used via `api/met_no.py` and scheduler
        
        # Create application
        self.application = Application.builder().token(BOT_TOKEN).build()
        # Start background MET scheduler (if MONITOR_COORDS is configured)
        try:
            thr = scheduler.start_background_scheduler_from_env()
            if thr:
                logger.info("Started MET scheduler thread for periodic fetches")
        except Exception:
            logger.exception("Failed to start MET scheduler")
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("weather", self.weather_command))
        
        # Text message handler (for city names)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
        
        # Start the bot
        logger.info("Starting Weather Bot...")
        print("🤖 Weather Bot is starting...")
        print("Press Ctrl+C to stop the bot")
        
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = WeatherBot()
    bot.run()
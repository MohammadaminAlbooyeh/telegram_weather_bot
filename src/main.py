import os
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Ensure project root is on sys.path so `from api import ...` works when running src/main.py directly
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api import scheduler
from api import weatherapi_client

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

    def get_aqi_from_weatherapi(self, air_quality: dict) -> dict:
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
    
    def get_weather_by_city(self, city_name: str) -> dict:
        """Get current weather data for a city"""
        try:
            q = city_name.strip()
            if not q:
                return None

            payload = weatherapi_client.get_current_weather(q)
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
                'name': location.get('name') or city_name,
                'sys': {'country': location.get('country') or ''},
                'main': {
                    'temp': current.get('temp_c', 0.0),
                    'feels_like': current.get('feelslike_c', current.get('temp_c', 0.0)),
                    'humidity': current.get('humidity'),
                    'pressure': current.get('pressure_mb'),
                },
                'weather': [{'description': description, 'id': weather_id}],
                'wind': {'speed': current.get('wind_kph', 0.0) / 3.6}
            }

            aqi_info = self.get_aqi_from_weatherapi(current.get('air_quality'))
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
        
        # Weather data is provided via WeatherAPI (`api/weatherapi_client.py`).
        
        # Create application
        self.application = Application.builder().token(BOT_TOKEN).build()
        # Start background scheduler (if MONITOR_COORDS is configured)
        try:
            thr = scheduler.start_background_scheduler_from_env()
            if thr:
                logger.info("Started weather scheduler thread for periodic fetches")
        except Exception:
            logger.exception("Failed to start weather scheduler")
        
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
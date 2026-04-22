import os
import logging
from datetime import datetime

import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
WEATHER_BASE_URL = 'http://api.openweathermap.org/data/2.5'

class WeatherBot:
    def __init__(self):
        self.application = None
    
    def get_weather_by_city(self, city_name: str) -> dict:
        """Get current weather data for a city"""
        try:
            url = f"{WEATHER_BASE_URL}/weather"
            params = {
                'q': city_name,
                'appid': WEATHER_API_KEY,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching weather data: {e}")
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

    def get_aqi_by_coords(self, lat: float, lon: float) -> dict:
        """Fetch AQI (air pollution) data for given coordinates using OpenWeather Air Pollution API.

        Returns a dict like `{'aqi': 1, 'description': 'Good'}` or None on error.
        """
        try:
            url = f"{WEATHER_BASE_URL}/air_pollution"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': WEATHER_API_KEY,
            }

            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # Data contains a 'list' with first item having 'main': {'aqi': int}
            if 'list' in data and len(data['list']) > 0:
                info = data['list'][0]
                aqi_idx = info.get('main', {}).get('aqi')
                components = info.get('components', {})
                # Map numeric AQI to human description (1-5)
                aqi_map = {
                    1: 'Good',
                    2: 'Fair',
                    3: 'Moderate',
                    4: 'Poor',
                    5: 'Very Poor'
                }
                return {'aqi': aqi_idx, 'description': aqi_map.get(aqi_idx, 'Unknown'), 'components': components}
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching AQI data: {e}")
            return None
    
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

        # Try to fetch AQI if coordinates are available
        if weather_data and weather_data.get('cod') == 200:
            coord = weather_data.get('coord') or {}
            lat = coord.get('lat')
            lon = coord.get('lon')
            if lat is not None and lon is not None:
                aqi_data = self.get_aqi_by_coords(lat, lon)
                if aqi_data:
                    # Attach AQI info to weather_data for formatting
                    weather_data['aqi'] = aqi_data

            weather_message = self.format_weather_message(weather_data)
            await update.message.reply_text(weather_message, parse_mode='Markdown')
        else:
            error_message = "❌ City not found. Please check the spelling and try again.\n\n"
            error_message += "**Tips:**\n"
            error_message += "• Use the full city name\n"
            error_message += "• Try adding country name (e.g., 'Paris, France')\n"
            error_message += "• Check for typos"
            
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
        
        if not WEATHER_API_KEY:
            logger.error("OPENWEATHER_API_KEY not found in environment variables")
            return
        
        # Create application
        self.application = Application.builder().token(BOT_TOKEN).build()
        
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
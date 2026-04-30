import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from api import scheduler
from config import TELEGRAM_BOT_TOKEN
from handlers.start import start_command as start_handler
from handlers.help import help_command as help_handler
from handlers.weather import (
    weather_command as weather_command_handler,
    handle_text_message as handle_text_message_handler,
    error_handler as error_handler_func,
)
from services.weather_service import WeatherService
from utils.logger import get_logger

logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)


class WeatherBot:
    def __init__(self):
        self.application = None
        self.service = WeatherService()
        self.city_fallback = self.service.city_fallback

    def get_weather_by_city(self, city_name: str) -> dict:
        """Get current weather data for a city"""
        return self.service.get_weather_by_city(city_name)

    def format_weather_message(self, weather_data: dict) -> str:
        """Format weather data into a readable message"""
        return self.service.format_weather_message(weather_data)

    def get_weather_emoji(self, weather_id: int) -> str:
        """Get appropriate emoji based on weather condition ID"""
        return self.service.get_weather_emoji(weather_id)

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
        if not TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
            return

        # Create application
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Start background scheduler (if MONITOR_COORDS is configured)
        try:
            thr = scheduler.start_background_scheduler_from_env()
            if thr:
                logger.info("Started weather scheduler thread for periodic fetches")
        except Exception:
            logger.exception("Failed to start weather scheduler")

        # Add handlers (wired to the new handlers/ modules; UI text is preserved)
        self.application.add_handler(CommandHandler("start", start_handler))
        self.application.add_handler(CommandHandler("help", help_handler))
        self.application.add_handler(
            CommandHandler("weather", lambda u, c: weather_command_handler(u, c, self.service))
        )

        # Text message handler (for city names)
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                lambda u, c: handle_text_message_handler(u, c, self.service),
            )
        )

        # Error handler
        self.application.add_error_handler(lambda u, c: error_handler_func(u, c))

        # Start the bot
        logger.info("Starting Weather Bot...")
        print("🤖 Weather Bot is starting...")
        print("Press Ctrl+C to stop the bot")

        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    bot = WeatherBot()
    bot.run()

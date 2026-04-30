from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from services.weather_service import WeatherService
from utils.validators import is_plausible_city_text
from utils.logger import get_logger

logger = get_logger(__name__)


async def _send_typing_action(update: Update):
    message = getattr(update, "message", None)
    if message and hasattr(message, "reply_chat_action"):
        await message.reply_chat_action("typing")
        return

    chat = getattr(update, "effective_chat", None)
    if chat and hasattr(chat, "send_action"):
        await chat.send_action("typing")


async def weather_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    service: WeatherService,
):
    """Handle /weather command"""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a city name.\n\n"
            "**Usage:** `/weather <city name>`\n"
            "**Example:** `/weather London`",
            parse_mode="Markdown",
        )
        return

    city_name = " ".join(context.args)
    await send_weather_info(update, city_name, service)


async def handle_text_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    service: WeatherService,
):
    """Handle regular text messages (city names)"""
    _ = context  # unused

    message_text = getattr(update.message, "text", "") or ""

    # Check if it looks like a city name (not a command)
    if not message_text.startswith("/") and is_plausible_city_text(message_text):
        await send_weather_info(update, message_text, service)
    else:
        await update.message.reply_text(
            "❌ Unknown command. Use /help to see available commands."
        )


async def send_weather_info(
    update: Update,
    city_name: str,
    service: WeatherService,
):
    """Send weather information for a city"""
    # Send "typing" action
    await _send_typing_action(update)

    await update.message.reply_text(f"🔍 Getting weather for {city_name}...")

    weather_data = service.get_weather_by_city(city_name)

    if weather_data:
        weather_message = service.format_weather_message(weather_data)
        await update.message.reply_text(weather_message, parse_mode="Markdown")
    else:
        error_message = (
            "❌ Couldn't resolve that city right now.\n\n"
            "Please try another city format (example: `Turin, Italy`) or try again in a few seconds."
        )
        await update.message.reply_text(error_message, parse_mode="Markdown")


async def error_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

    if update and update.message:
        await update.message.reply_text(
            "❌ An error occurred. Please try again later."
        )

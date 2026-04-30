from telegram import Update
from telegram.ext import ContextTypes


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

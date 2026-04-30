from telegram import Update
from telegram.ext import ContextTypes


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

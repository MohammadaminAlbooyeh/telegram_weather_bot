# 🌤️ Telegram Weather Bot

A simple Telegram bot that provides current weather information for any city worldwide.

## ✨ Features

- 🌡️ **Current Weather**: Get real-time weather data for any city
- 🌍 **Global Coverage**: Support for cities worldwide
- 🎨 **Clean Interface**: Simple commands with emoji-rich responses
 - ⚡ **Fast & Reliable**: Powered by WeatherAPI

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- WeatherAPI key (from [weatherapi.com](https://www.weatherapi.com/))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/telegram_weather_bot.git
   cd telegram_weather_bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` file with your credentials:
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   WEATHER_API_KEY=5e5f7abe65074015b7f130224251809
   ```

4. **Run the bot**
   ```bash
   python src/main.py
   ```

## 🐳 Run With Docker On Raspberry Pi

1. Put your bot token in `.env`:

   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```

2. Build and run:

   ```bash
   docker compose up --build -d
   ```

3. Check logs:

   ```bash
   docker compose logs -f
   ```

4. Stop:

   ```bash
   docker compose down
   ```

Notes:
- `docker-compose.yml` is set to `platform: linux/arm64` for 64-bit Raspberry Pi OS.
- If your Pi OS is 32-bit, change platform to `linux/arm/v7`.

## 🚫 CI/CD

CI/CD workflows and automated deployments have been removed from this repository.
Run the bot locally using the instructions in the "Quick Start" section above.

## 🔧 Getting API Keys

### Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the token provided by BotFather

### WeatherAPI

1. Create an account at [weatherapi.com](https://www.weatherapi.com/).
2. Copy your API key and set `WEATHER_API_KEY` in `.env`.
3. This project uses WeatherAPI `current.json` endpoint for weather and air quality.

## 🤖 Bot Commands

- `/start` - Initialize the bot and see welcome message
- `/help` - Display help information
- `/weather <city>` - Get current weather for a specific city

## 💬 Usage Examples

### Basic Usage
- Send: `London` → Get current weather for London
- Send: `New York` → Get current weather for New York
- Send: `Paris, France` → Get weather with country specification

### Commands
- `/weather Tokyo` → Current weather in Tokyo
- `/weather Berlin` → Current weather in Berlin

## 🌟 Features in Detail

### Weather Information Includes:
- 🌡️ Temperature (current and "feels like")
- 📝 Weather description
- 💧 Humidity percentage
- 🔽 Atmospheric pressure
- 💨 Wind speed
- 🕐 Last updated timestamp

## 📁 Project Structure

```
telegram_weather_bot/
├── src/
│   └── main.py          # Main bot implementation
├── requirements.txt      # Python dependencies
├── .env.example         # Environment variables template
└── README.md           # This file
```

## 🛠️ How It Works

### Dependencies
- `python-telegram-bot` - Telegram Bot API wrapper
- `requests` - HTTP requests for weather API
- `python-dotenv` - Environment variable management

### APIs Used
- **Telegram Bot API** - For bot functionality
- **WeatherAPI** - For current weather and air quality data (see `api/weatherapi_client.py`)

## 🔒 Security

- Never commit your `.env` file to version control
- Keep your bot token and API key secure
- The `.env.example` file is provided as a template

## 🐛 Troubleshooting

- **"Import errors"**: Run `pip install -r requirements.txt`
- **"Token not found"**: Check your `.env` file exists and contains valid tokens
- **"City not found"**: Check spelling or try adding country name
 - **No weather data**: Verify your configuration and monitored coordinates in `.env` (see `MONITOR_COORDS`).

## 📈 Future Ideas

- Weather alerts
- Multiple languages
- User favorites
- Weather maps

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test your changes
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Excellent Telegram Bot framework
- [WeatherAPI](https://www.weatherapi.com/) - Weather and air quality data provider
- Weather emojis and icons from Unicode standard

## 📞 Support

If you encounter any issues or have questions:

1. Check the troubleshooting section above
2. Search existing issues on GitHub
3. Create a new issue with detailed information

---

**Happy Weather Botting! 🌈**
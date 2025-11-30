# 🌤️ Telegram Weather Bot

A simple Telegram bot that provides current weather information for any city worldwide.

## ✨ Features

- 🌡️ **Current Weather**: Get real-time weather data for any city
- 🌍 **Global Coverage**: Support for cities worldwide
- 🎨 **Clean Interface**: Simple commands with emoji-rich responses
- ⚡ **Fast & Reliable**: Powered by OpenWeatherMap API

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- OpenWeatherMap API Key (from [OpenWeatherMap](https://openweathermap.org/api))

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
   OPENWEATHER_API_KEY=your_api_key_here
   ```

4. **Run the bot**
   ```bash
   python src/main.py
   ```

## 🔄 CI/CD Pipeline

This project includes automated workflows:

- **CI**: Tests code syntax and imports on every push/PR
- **Docker Build**: Creates container images and pushes to GitHub Container Registry
- **Deploy**: Automated deployment on version tags

### Deployment

Create a new release to trigger deployment:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Or manually trigger deployment from GitHub Actions.

## 🔧 Getting API Keys

### Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the token provided by BotFather

### OpenWeatherMap API Key

1. Visit [OpenWeatherMap](https://openweathermap.org/api)
2. Sign up for a free account
3. Go to API Keys section in your profile
4. Copy your default API key

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
- **OpenWeatherMap API** - For weather data

## 🔒 Security

- Never commit your `.env` file to version control
- Keep your bot token and API key secure
- The `.env.example` file is provided as a template

## 🐛 Troubleshooting

- **"Import errors"**: Run `pip install -r requirements.txt`
- **"Token not found"**: Check your `.env` file exists and contains valid tokens
- **"City not found"**: Check spelling or try adding country name
- **No weather data**: Verify your OpenWeatherMap API key is active

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
- [OpenWeatherMap](https://openweathermap.org/) - Reliable weather data API
- Weather emojis and icons from Unicode standard

## 📞 Support

If you encounter any issues or have questions:

1. Check the troubleshooting section above
2. Search existing issues on GitHub
3. Create a new issue with detailed information

---

**Happy Weather Botting! 🌈**
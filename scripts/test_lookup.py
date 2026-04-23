from dotenv import load_dotenv
import os
import sys
from pathlib import Path
import json

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

load_dotenv()

from src.main import WeatherBot

bot = WeatherBot()
print('Testing get_weather_by_city("Turin")')
wd = bot.get_weather_by_city('Turin')
print('\n--- RAW WEATHER DATA ---')
print(json.dumps(wd, indent=2, ensure_ascii=False))
print('\n--- FORMATTED MESSAGE ---')
print(bot.format_weather_message(wd))

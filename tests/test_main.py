import pytest
from unittest.mock import patch, Mock

import requests

from src.main import WeatherBot


def sample_weather_data():
    return {
        "name": "TestCity",
        "sys": {"country": "TC"},
        "main": {"temp": 21.4, "feels_like": 20.0, "humidity": 55, "pressure": 1012},
        "weather": [{"description": "clear sky", "id": 800}],
        "wind": {"speed": 3.5}
    }


def test_get_weather_emoji_ranges():
    bot = WeatherBot()
    assert bot.get_weather_emoji(200) == "⛈️"
    assert bot.get_weather_emoji(301) == "🌧️"
    assert bot.get_weather_emoji(501) == "🌧️"
    assert bot.get_weather_emoji(611) == "❄️"
    assert bot.get_weather_emoji(741) == "🌫️"
    assert bot.get_weather_emoji(800) == "☀️"
    assert bot.get_weather_emoji(801) == "☁️"


def test_format_weather_message_success_contains_fields():
    bot = WeatherBot()
    data = sample_weather_data()
    message = bot.format_weather_message(data)

    # Check essential parts of the formatted message
    assert "Weather in TestCity, TC" in message
    assert "🌡️ **Temperature:** 21°C (feels like 20°C)" in message
    assert "📝 **Description:** Clear Sky" in message
    assert "💧 **Humidity:** 55%" in message
    assert "🔽 **Pressure:** 1012 hPa" in message
    assert "💨 **Wind Speed:** 3.5 m/s" in message
    assert "🕐 *Updated:" in message


def test_format_weather_message_none_returns_error():
    bot = WeatherBot()
    assert bot.format_weather_message(None).startswith("❌ Sorry")


def test_get_weather_by_city_success(monkeypatch):
    bot = WeatherBot()

    fake_json = {"cod": 200, "name": "X"}

    mock_resp = Mock()
    mock_resp.json.return_value = fake_json
    mock_resp.raise_for_status.return_value = None

    with patch('src.main.requests.get', return_value=mock_resp) as mock_get:
        result = bot.get_weather_by_city('X')
        mock_get.assert_called_once()
        assert result == fake_json


def test_get_weather_by_city_request_exception(monkeypatch):
    bot = WeatherBot()

    with patch('src.main.requests.get', side_effect=requests.exceptions.RequestException("err")):
        result = bot.get_weather_by_city('Nowhere')
        assert result is None

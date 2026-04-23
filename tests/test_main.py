import pytest
from unittest.mock import patch

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
    assert "💨 **Wind Speed:** 3.50 m/s" in message
    assert "🕐 *Updated:" in message


def test_format_weather_message_none_returns_error():
    bot = WeatherBot()
    assert bot.format_weather_message(None).startswith("❌ Sorry")


def test_get_weather_by_city_success(monkeypatch):
    bot = WeatherBot()

    fake_json = {
        "location": {"name": "X", "country": "TC"},
        "current": {
            "temp_c": 19.3,
            "feelslike_c": 18.1,
            "humidity": 61,
            "pressure_mb": 1010,
            "wind_kph": 14.4,
            "condition": {"text": "Sunny", "code": 1000},
            "air_quality": {
                "us-epa-index": 2,
                "pm2_5": 8.2,
                "pm10": 14.0,
                "no2": 9.1,
                "o3": 45.3,
                "co": 240.0,
                "so2": 4.0,
            },
        },
    }

    with patch('src.main.weatherapi_client.get_current_weather', return_value=fake_json) as mock_get:
        result = bot.get_weather_by_city('X')
        mock_get.assert_called_once()
        assert result["name"] == "X"
        assert result["sys"]["country"] == "TC"
        assert result["main"]["temp"] == 19.3
        assert result["weather"][0]["description"] == "Sunny"
        assert result["aqi"]["aqi"] == 2


def test_get_weather_by_city_request_exception(monkeypatch):
    bot = WeatherBot()

    with patch('src.main.weatherapi_client.get_current_weather', side_effect=Exception("err")):
        result = bot.get_weather_by_city('Nowhere')
        assert result is None

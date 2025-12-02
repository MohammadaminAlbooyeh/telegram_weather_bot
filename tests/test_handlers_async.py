import pytest
from types import SimpleNamespace

from src.main import WeatherBot


def sample_weather_data():
    return {
        "cod": 200,
        "name": "TestCity",
        "sys": {"country": "TC"},
        "main": {"temp": 21.4, "feels_like": 20.0, "humidity": 55, "pressure": 1012},
        "weather": [{"description": "clear sky", "id": 800}],
        "wind": {"speed": 3.5}
    }


class AsyncMessage:
    def __init__(self):
        self.sent_texts = []
        self.last_action = None

    async def reply_text(self, text, **kwargs):
        self.sent_texts.append(text)

    async def reply_chat_action(self, action):
        self.last_action = action


@pytest.mark.asyncio
async def test_start_command_replies_welcome():
    bot = WeatherBot()
    update = SimpleNamespace(effective_user=SimpleNamespace(first_name='Alice'), message=AsyncMessage())

    await bot.start_command(update, None)

    assert any('Hello Alice' in t or 'Welcome to the Weather Bot' in t for t in update.message.sent_texts)


@pytest.mark.asyncio
async def test_help_command_replies_help():
    bot = WeatherBot()
    update = SimpleNamespace(message=AsyncMessage())

    await bot.help_command(update, None)

    assert any('Weather Bot Help' in t or '/weather' in t for t in update.message.sent_texts)


@pytest.mark.asyncio
async def test_weather_command_no_args_replies_usage():
    bot = WeatherBot()
    update = SimpleNamespace(message=AsyncMessage())
    context = SimpleNamespace(args=[])

    await bot.weather_command(update, context)

    assert any('Please provide a city name' in t for t in update.message.sent_texts)


@pytest.mark.asyncio
async def test_weather_command_with_args_calls_send_weather_info(monkeypatch):
    bot = WeatherBot()

    called = {}

    async def fake_send(update_arg, city_name):
        called['args'] = (update_arg, city_name)

    bot.send_weather_info = fake_send

    update = SimpleNamespace(message=AsyncMessage())
    context = SimpleNamespace(args=['London', 'UK'])

    await bot.weather_command(update, context)

    assert 'args' in called
    assert called['args'][1] == 'London UK'


@pytest.mark.asyncio
async def test_send_weather_info_success(monkeypatch):
    bot = WeatherBot()
    data = sample_weather_data()

    update = SimpleNamespace(message=AsyncMessage())

    # Patch get_weather_by_city to return our sample data
    bot.get_weather_by_city = lambda city: data

    await bot.send_weather_info(update, 'TestCity')

    # First reply should be the searching message
    assert any('Getting weather for TestCity' in t for t in update.message.sent_texts)

    # Later replies should include formatted weather message
    assert any('Weather in TestCity' in t or 'Temperature' in t for t in update.message.sent_texts)
    assert update.message.last_action == 'typing'

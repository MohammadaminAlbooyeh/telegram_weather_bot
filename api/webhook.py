from fastapi import FastAPI, Request
from deta_webhook import _get_weather, _get_aqi, _format_message, _send_telegram

app = FastAPI()


@app.post("/api/webhook")
async def webhook(request: Request):
    update = await request.json()
    message = update.get('message') or update.get('edited_message')
    if not message:
        return {"ok": True}

    text = (message.get('text') or '').strip()
    chat = message.get('chat') or {}
    chat_id = chat.get('id')
    if not text or not chat_id:
        return {"ok": True}

    weather = _get_weather(text)
    if not weather or weather.get('cod') != 200:
        _send_telegram(chat_id, "❌ City not found. Please check the spelling and try again.")
        return {"ok": True}

    coord = weather.get('coord', {})
    aqi = None
    if coord.get('lat') is not None and coord.get('lon') is not None:
        aqi = _get_aqi(coord.get('lat'), coord.get('lon'))

    msg = _format_message(weather, aqi)
    _send_telegram(chat_id, msg)

    return {"ok": True}

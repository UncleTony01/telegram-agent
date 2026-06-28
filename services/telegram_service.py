import requests

from config import BOT_TOKEN

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id, text):
    requests.post(
        f"{BASE_URL}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text[:4000],
        },
        timeout=30,
    )


def get_updates(offset=None):
    params = {"timeout": 30}

    if offset is not None:
        params["offset"] = offset

    r = requests.get(
        f"{BASE_URL}/getUpdates",
        params=params,
        timeout=35,
    )

    return r.json()

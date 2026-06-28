import subprocess
import time
import requests

from config import BOT_TOKEN, CHAT_ID, HERMES_CMD

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

last_update_id = None


def send_message(chat_id, text):
    requests.post(
        f"{BASE_URL}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text[:4000]
        },
        timeout=30
    )


def ask_hermes(prompt):
    try:
        result = subprocess.run(
            [
                HERMES_CMD,
                "chat",
                "-q",
                prompt,
                "-Q"
            ],
            capture_output=True,
            text=True,
            timeout=180
        )

        output = result.stdout.strip()

        if not output:
            output = result.stderr.strip()

        if not output:
            output = "Hermes returned no output."

        return output

    except subprocess.TimeoutExpired:
        return "Hermes timed out."

    except Exception as e:
        return f"Error: {e}"


def handle_message(chat_id, text):

    text = text.strip()

    if text == "/start":
        send_message(
            chat_id,
            "UNCLE TONY is online.\n\n"
            "Examples:\n"
            "hello\n"
            "What is Bitcoin?\n"
            "Check OKX market for BTC and ETH"
        )
        return

    if text.lower() == "ping":
        send_message(chat_id, "pong")
        return

    send_message(chat_id, "Thinking...")

    reply = ask_hermes(text)

    send_message(chat_id, reply)


def get_updates(offset=None):

    params = {"timeout": 30}

    if offset is not None:
        params["offset"] = offset

    r = requests.get(
        f"{BASE_URL}/getUpdates",
        params=params,
        timeout=35
    )

    return r.json()


print("UNCLE TONY started.")

while True:

    try:

        updates = get_updates(
            last_update_id + 1 if last_update_id is not None else None
        )

        if updates.get("ok"):

            for update in updates["result"]:

                last_update_id = update["update_id"]

                if "message" not in update:
                    continue

                message = update["message"]

                if "text" not in message:
                    continue

                chat_id = str(message["chat"]["id"])

                if chat_id != CHAT_ID:
                    continue

                handle_message(chat_id, message["text"])

        time.sleep(2)

    except Exception as e:
        print(e)
        time.sleep(5)

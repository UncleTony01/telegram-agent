from services.hermes_service import ask_hermes
from services.telegram_service import send_message


def handle_message(chat_id, text):
    text = text.strip()

    if text == "/start":
        send_message(
            chat_id,
            "UNCLE TONY is online.\n\n"
            "Examples:\n"
            "hello\n"
            "What is Bitcoin?\n"
            "Check OKX market for BTC and ETH",
        )
        return

    if text.lower() == "ping":
        send_message(chat_id, "pong")
        return

    send_message(chat_id, "Thinking...")

    reply = ask_hermes(text)

    send_message(chat_id, reply)

from memory.conversation_memory import (
    add_message,
    get_history,
    clear_history,
)

from routers.command_router import detect_command
from services.hermes_service import ask_hermes
from services.okx_service import build_market_context, extract_symbols
from services.telegram_service import send_message


def handle_message(chat_id, text):

    text = text.strip()

    if text == "/start":
        send_message(
            chat_id,
            "UNCLE TONY is online.\n\n"
            "Now with conversation memory 🧠"
        )
        return

    if text.lower() == "ping":
        send_message(chat_id, "pong")
        return

    if text.lower() == "/clear":
        clear_history(chat_id)
        send_message(chat_id, "Conversation memory cleared.")
        return

    send_message(chat_id, "Thinking...")

    history = get_history(chat_id)
    symbols = extract_symbols(text)
    market_context = build_market_context(symbols)

    if market_context:
        prompt = (
            f"{market_context}\n\n"
            f"---\n\n"
            f"User request: {text}"
        )
    else:
        prompt = text

    reply = ask_hermes(prompt, history)

    add_message(chat_id, "user", text)
    add_message(chat_id, "assistant", reply)

    send_message(chat_id, reply)

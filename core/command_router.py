from handlers.message_handler import handle_message
from services.analysis_service import handle_analysis_command
from services.help_service import send_help
from services.price_service import handle_price_command


def route_command(chat_id: str, text: str):
    text = text.strip()
    if not text:
        return

    normalized = text.lower()
    if normalized.startswith("/help"):
        return send_help(chat_id)

    if normalized.startswith("/price"):
        return handle_price_command(chat_id, text)

    if normalized.startswith("/analysis"):
        return handle_analysis_command(chat_id, text)

    return handle_message(chat_id, text)

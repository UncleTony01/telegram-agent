from services.telegram_service import send_message


HELP_TEXT = (
    "Uncle Tony Command Menu:\n"
    "\n"
    "/help - Show this help menu\n"
    "/price <symbol> - Fetch current price for a coin\n"
    "/analysis <symbol> - Provide market analysis for a coin\n"
    "/intelligence <symbol> - Full market intelligence report\n"
    "/tactical <symbol> - Local rule-based analysis (no AI)\n"
    "/analyze <symbol> - AnalysisObject pipeline report\n"
    "/clear - Clear conversation memory\n"
    "\n"
    "Example:\n"
    "/price BTC"
)


def send_help(chat_id: str):
    send_message(chat_id, HELP_TEXT)

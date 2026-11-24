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
    "/scan - Scan the watchlist now and send a market brief\n"
    "/portfolio - Your OKX holdings and profit/loss\n"
    "/status - Check Uncle Tony is healthy\n"
    "/check AVAX 100B - Reality check a price claim (also $20 or 10x)\n"
    "/ledger - Review past claims (owner only)\n"
    "/xpost - Today's X post draft (owner only). Also: /xpost ai | journey | data | governance | debate | reality | recovery | dilution | hype | AVAX 100B\n"
    "/redo shorter hook - Rewrite the X draft waiting for review, with your note (owner only)\n"
    "/clear - Clear conversation memory\n"
    "\n"
    "Example:\n"
    "/price BTC"
)


def send_help(chat_id: str):
    send_message(chat_id, HELP_TEXT)

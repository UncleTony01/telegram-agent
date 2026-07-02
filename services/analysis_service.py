from services.okx_service import build_market_context, KNOWN_SYMBOLS
from services.telegram_service import send_message
from services.hermes_service import ask_hermes


def handle_analysis_command(chat_id: str, text: str):
    parts = text.strip().split()
    if len(parts) < 2:
        send_message(
            chat_id,
            "Usage: /analysis <symbol> [your question]\n"
            "Example: /analysis BTC Should I long?\n"
            "Example: /analysis HYPE\n"
            "Example: /analysis ETH What's the outlook?"
        )
        return

    symbol = parts[1].upper()
    if symbol not in KNOWN_SYMBOLS:
        send_message(chat_id, f"Unknown symbol: {symbol}. I don't have market data for it.")
        return

    market_block = build_market_context([symbol])

    if not market_block:
        send_message(chat_id, f"No market data available for {symbol} right now. Try again shortly.")
        return

    user_question = " ".join(parts[2:]) if len(parts) > 2 else f"Analyze {symbol} for me."

    prompt = (
        f"{market_block}\n\n"
        f"---\n\n"
        f"User request: {user_question}\n\n"
        f"Provide a clear, actionable analysis. Include technical and fundamental context where relevant."
    )

    response = ask_hermes(prompt)
    send_message(chat_id, response)

from services.okx_service import OKXError, get_ticker
from services.telegram_service import send_message


def handle_price_command(chat_id: str, text: str):
    parts = text.strip().split()
    if len(parts) < 2:
        send_message(chat_id, "Usage: /price <symbol>\nExample: /price BTC")
        return

    symbol = parts[1].upper()
    try:
        price_data = get_ticker(symbol)
    except OKXError as exc:
        send_message(chat_id, f"Could not fetch price for {symbol}: {exc}")
        return

    if not price_data or price_data.get("price_usd") is None:
        send_message(chat_id, f"No price data available for {symbol}.")
        return

    message = (
        f"{price_data['symbol']} price: ${price_data['price_usd']}\n"
        f"24h change: {price_data['change_24h']:+.2f}%\n"
    )
    if price_data.get("bid_price") is not None and price_data.get("ask_price") is not None:
        message += (
            f"Bid: ${price_data['bid_price']}\n"
            f"Ask: ${price_data['ask_price']}"
        )
    send_message(chat_id, message)

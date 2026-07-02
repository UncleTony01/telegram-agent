def detect_command(text: str):
    text = text.strip()

    if text.startswith("/price"):
        return "price"

    if text.startswith("/analysis"):
        return "analysis"

    if text.startswith("/watchlist"):
        return "watchlist"

    if text.startswith("/help"):
        return "help"

    return "chat"

def should_process_chat(chat_id, configured_chat_id, bot_id):
    if configured_chat_id is None or configured_chat_id == "":
        return True

    if bot_id is not None and bot_id != "" and configured_chat_id == bot_id:
        return True

    return str(chat_id) == str(configured_chat_id)

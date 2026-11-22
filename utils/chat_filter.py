def should_process_chat(chat_id, configured_chat_id, bot_id):
    if configured_chat_id is None or configured_chat_id == "":
        return True

    if bot_id is not None and bot_id != "" and configured_chat_id == bot_id:
        return True

    return str(chat_id) == str(configured_chat_id)


def is_owner(chat_id, owner_chat_id=None):
    """True only for the bot owner's chat. Portfolio data is shown to the owner alone.

    The owner is OWNER_CHAT_ID (falls back to CHAT_ID). If neither is set, nobody
    counts as the owner, so private data is never shown by mistake.
    """
    if owner_chat_id is None:
        import config

        owner_chat_id = getattr(config, "OWNER_CHAT_ID", None)
    if owner_chat_id is None or str(owner_chat_id).strip() == "":
        return False
    return str(chat_id) == str(owner_chat_id).strip()

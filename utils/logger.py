"""Logging utilities for the Telegram agent."""

import logging
import os


class _RedactSecrets(logging.Filter):
    """Replace the bot token with *** so it never appears in logs."""

    def filter(self, record):
        token = os.getenv("BOT_TOKEN")
        if token:
            message = record.getMessage()
            if token in message:
                record.msg = message.replace(token, "***")
                record.args = ()
        return True


def get_logger(name):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        handler.addFilter(_RedactSecrets())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger

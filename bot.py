import fcntl
import sys
import time
import traceback
from pathlib import Path

from config import BOT_TOKEN, CHAT_ID
from core.command_router import route_command
from services.telegram_service import get_updates
from utils.chat_filter import should_process_chat

if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN":
    raise RuntimeError("BOT_TOKEN is not configured. Set a real Telegram bot token in the environment or .env file.")

lock_path = Path("/tmp/telegram-agent-bot.lock")
lock_handle = lock_path.open("w")
try:
    fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    print("Another bot instance is already running. Exiting.")
    sys.exit(1)

last_update_id = None
bot_id = BOT_TOKEN.split(":", 1)[0] if BOT_TOKEN else None

print("UNCLE TONY started.")

while True:
    try:
        updates = get_updates(
            last_update_id + 1 if last_update_id is not None else None
        )

        print(updates)

        if updates.get("ok"):
            for update in updates["result"]:
                last_update_id = update["update_id"]

                if "message" not in update:
                    continue

                message = update["message"]

                if "text" not in message:
                    continue

                chat_id = str(message["chat"]["id"])

                if not should_process_chat(chat_id, CHAT_ID, bot_id):
                    continue

                route_command(chat_id, message["text"])

        time.sleep(2)

    except Exception:
        traceback.print_exc()
        time.sleep(5)

import time

from config import CHAT_ID
from handlers.message_handler import handle_message
from services.telegram_service import get_updates

last_update_id = None

print("UNCLE TONY started.")

while True:
    try:
        updates = get_updates(
            last_update_id + 1 if last_update_id is not None else None
        )

        if updates.get("ok"):
            for update in updates["result"]:
                last_update_id = update["update_id"]

                if "message" not in update:
                    continue

                message = update["message"]

                if "text" not in message:
                    continue

                chat_id = str(message["chat"]["id"])

                if chat_id != CHAT_ID:
                    continue

                handle_message(chat_id, message["text"])

        time.sleep(2)

    except Exception as e:
        print(e)
        time.sleep(5)

from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
HERMES_CMD = os.getenv("HERMES_CMD") or "hermes"
TELEGRAM_API_IPS = [
    ip.strip()
    for ip in os.getenv("TELEGRAM_API_IPS", "149.154.167.99,149.154.167.40,149.154.166.110").split(",")
    if ip.strip()
]

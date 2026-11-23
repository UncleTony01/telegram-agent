from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
# The only chat that may see portfolio data. Defaults to CHAT_ID. Set it before
# opening the bot to other people (clearing CHAT_ID).
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID") or CHAT_ID
HERMES_CMD = os.getenv("HERMES_CMD")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# Optional paid fallback, used only when the free OpenRouter models fail.
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
# Comma-separated; OpenRouter tries each in order if the previous one is unavailable.
OPENROUTER_MODELS = [
    m.strip()
    for m in os.getenv(
        "OPENROUTER_MODEL",
        "minimax/minimax-m3.1-flash:free,nvidia/nemotron-3.5-lightning:free",
    ).split(",")
    if m.strip()
]
TELEGRAM_API_IPS = [
    ip.strip()
    for ip in os.getenv("TELEGRAM_API_IPS", "149.154.167.99,149.154.167.40,149.154.166.110").split(",")
    if ip.strip()
]

# Background market scanner: setup alerts plus 8am/8pm briefs. Set SCANNER_ENABLED=0 to turn off.
SCANNER_ENABLED = os.getenv("SCANNER_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}

# Heartbeat: start-up message, daily check-in and a watchdog that warns if the scanner
# or Telegram polling stalls. Set HEARTBEAT_ENABLED=0 to turn off.
HEARTBEAT_ENABLED = os.getenv("HEARTBEAT_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
# Hour of the daily check-in, in the VM's local time (0-23).
try:
    HEARTBEAT_HOUR = min(23, max(0, int(os.getenv("HEARTBEAT_HOUR", "7"))))
except ValueError:
    HEARTBEAT_HOUR = 7

# Daily Reality Check post on X. Without all four X keys it runs in preview mode:
# the draft goes to the owner on Telegram and nothing is posted. Set X_POST_ENABLED=0 to turn off.
X_POST_ENABLED = os.getenv("X_POST_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}
try:
    X_POST_HOUR = min(23, max(0, int(os.getenv("X_POST_HOUR", "18"))))
except ValueError:
    X_POST_HOUR = 18
X_API_KEY = os.getenv("X_API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_SECRET = os.getenv("X_ACCESS_SECRET")

# x402 paid API (api/server.py). Starts on Base Sepolia test USDC with the free
# x402.org facilitator. For real USDC: X402_NETWORK=eip155:8453 and a mainnet facilitator.
X402_PAY_TO = os.getenv("X402_PAY_TO")  # wallet address that receives payments
X402_NETWORK = os.getenv("X402_NETWORK", "eip155:84532")
X402_PRICE = os.getenv("X402_PRICE", "$0.01")
X402_FACILITATOR_URL = os.getenv("X402_FACILITATOR_URL", "https://x402.org/facilitator")

# Setup Instructions

## Requirements
- Python 3.12+
- Telegram bot token
- Hermes CLI installed and configured

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Configure

Create a `.env` file:

```text
BOT_TOKEN=your_real_bot_token
CHAT_ID=your_chat_id
HERMES_CMD=/path/to/hermes
```

## Run

```bash
source .venv/bin/activate
python bot.py
```

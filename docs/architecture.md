# Architecture Overview

Uncle Tony is designed as a modular Telegram AI assistant with a command router at its core.

## Core layers

- `bot.py`
  - Telegram polling and update loop
  - passes messages to the command router

- `core/command_router.py`
  - parses commands
  - routes requests to services

- `services/`
  - contains domain-specific logic
  - examples: `help_service.py`, `price_service.py`, `analysis_service.py`

- `handlers/`
  - contains legacy message handling and AI fallback logic
  - preserves conversation memory behavior

- `memory/`
  - stores conversation history per chat

- `utils/`
  - shared helpers such as chat filtering

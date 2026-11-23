# Uncle Tony – handover (2026-11-23)

Read this first when continuing work from a new Claude session (e.g. Claude Code on mobile/web).

## Done today
- **Reality Check** `/check AVAX 100B | $20 | 10x`, **hype ledger**, `/ledger`, **heartbeat** `/status`,
  owner-only portfolio → merged to `main` (c7cec36) and running on the server.
- **Daily X post** (branch `feature/x-post`, NOT merged): 18:00 EAT, 10x Reality Check on a trending
  top-100 coin, no links. Runs in **preview mode** (draft sent to owner on Telegram) until 4 X keys
  (`X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET`) are added. `/xpost` = draft on demand.
  X API is pay-per-use (~$0.015/post, ~$0.20 with a link).
- **x402 paid API** (branch `feature/x402-api`, built on `feature/x-post`, NOT merged):
  `GET https://147-224-181-200.sslip.io/check?claim=AVAX%20100B`, $0.01 test USDC on Base Sepolia
  (`eip155:84532`) via the free x402.org facilitator. Two paid test purchases succeeded.
  Runs as a sandboxed system service (`sudo systemctl status uncle-tony-api`) that cannot read `.env`,
  the OKX key, SSH keys or wallets. Caddy gives HTTPS. Configs in `deploy/`.
  Test wallets live on the server in `~/.x402/` (test money only).

## Server
- Oracle **trial** VM, 147.224.181.200, user `ubuntu`, Ubuntu 24.04 arm64. **Trial ends ~6 Dec 2026**:
  bot + API must move before then (laptop or another host).
- Bot: `systemctl --user status uncle-tony`. API: `sudo systemctl status uncle-tony-api`. Caddy: `caddy`.
- Open ports: 22, 80, 443. Code is **rsynced from the laptop** (not a git clone). Deploy excludes:
  `.env .git __pycache__ *.json .venv* venv *.db *.sqlite* memory/ logs data/`.
- SSH key lives only on the laptop, so a cloud/mobile session cannot reach the server.

## Rules
- All bot messages must be calm and factual: no fear/greed words or alarm emojis, never "buy/sell" advice.
- Never commit secrets (`.env`, keys).

## Next steps (waiting on the owner)
1. Check the 6pm X draft on Telegram → if OK, merge `feature/x-post` then `feature/x402-api` into `main`.
2. Optional: X developer account + credits + 4 keys → real X posting.
3. Real USDC for x402: owner's Base wallet address, mainnet facilitator (Coinbase CDP key likely), price.
4. Before 6 Dec: decide where the bot + API move.

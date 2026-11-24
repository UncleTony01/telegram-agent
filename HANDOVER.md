# Uncle Tony – handover (updated 2026-11-24)

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

## Loop 1: self-improving X drafts (branch `feature/post-loop`, built 2026-11-24, NOT merged)
Spec: `docs/LOOP1_SPEC.md`. Code: `services/post_loop.py` (LangGraph), tests `tests/test_post_loop.py`.
- 18:00 daily (and `/xpost`): draft → **guard** (≤280, banned words, no links/hashtags, disclaimer,
  every number/$TICKER must come from the market data) → DeepSeek **critic** (0–10 rubric, JSON) →
  **revise** if score < 8 (max 3 rewrites) → owner gets the image card with **✅ Approve · 🔁 Redo · ✖ Skip**.
- `/redo <note>` (owner only, ≤200 chars) rewrites the waiting draft with your note (2 more rounds).
- Nothing is posted to X without ✅ Approve, even with X keys. Without keys, Approve sends the
  "✍️ Post on X" button. Approved Reality Checks go to the hype ledger.
- Max 12 DeepSeek calls a day. Any AI failure or a missing `DEEPSEEK_API_KEY` sends the plain draft for review.
  If LangGraph fails to load, the bot falls back to the old plain draft (never auto-posts).
- Files (mode 0600, in git-ignored `data/`): `post_loop.sqlite` (paused reviews survive restarts),
  `post_loop_state.json` (daily AI-call count, pending draft), `post_loop_log.jsonl` (results for Loop 2).
- New deps pinned: `langgraph==1.2.24`, `langgraph-checkpoint-sqlite==3.1.3` (pip-audit: clean).
- **Deploy note:** the server also runs `feature/raise-order` (`/raise`), which is kept OFF GitHub on purpose
  (it contains the owner's cost basis). Deploy from the laptop's local branch `local/post-loop-deploy`
  (= this branch + raise-order), otherwise `/raise` disappears from the server.
  Steps: rsync as usual (excludes `.env`, `data/`), then on the VM
  `~/telegram-agent/.venv/bin/pip install -r ~/telegram-agent/requirements.txt` and
  `systemctl --user restart uncle-tony`. Check the server `.env` still has `DEEPSEEK_API_KEY`.
  Test: `/xpost`, tap ✅ / 🔁 / ✖, try `/redo make it spicier`.

## Diversified loops (branch `feature/loop-diversify`, 2026-11-24)
- **X topics**: crypto is now 1 day in 7. Week: Mon ai · Tue journey · Wed data (rotates reality →
  recovery → dilution → hype) · Thu ai · Fri journey · Sat governance · Sun debate (`services/content_mix.py`).
  `journey` = true build-in-public stories told as human experience; `ai` = first-hand agentic-AI takes.
  Journey posts must stay true and never include holdings, prices paid, IPs or keys (a test checks this).
  The critic uses a "human" rubric (hook, human, clarity, specific detail, rules) for non-data posts.
- **Analysis loop** (`services/analysis_loop.py`, LangGraph, no human step): the AI take on `/analysis`
  and the AI narration for chat questions go write → guard (numbers must come from the data, calm words,
  no buy/sell instructions, no links) → DeepSeek critic → at most 1 rewrite. Any failure → rule-based text.
  Cap 60 DeepSeek calls/day (`data/analysis_loop_state.json`).

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

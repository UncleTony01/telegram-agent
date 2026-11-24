# Loop 1 spec: self-improving X drafts with owner approval (LangGraph)

Status: **to build**. Branch: `feature/post-loop` (this file is its first commit; it is based on
`feature/content-mix`, which has the weekly content mix, hook-first posts, image cards and AI angles).
Do **not** merge to `main` until the owner approves on Telegram.

## Goal
The daily 6pm X draft should only reach the owner once it is good. A critic scores each draft,
weak drafts are rewritten (max 3 rounds), and the owner approves, redoes or skips it on Telegram.
Nothing is ever posted to X without the owner's approval.

## Graph (LangGraph `StateGraph`)

```
START → draft → guard → critique ──(score ≥ 8 or round ≥ 3)──→ human_review ──approve──→ finalize → END
                          ↑   │                                   │ redo(note)        skip → END
                          │   └──(score < 8 and round < 3)──→ revise
                          └──────────── guard ←───────────────────┘
```

### State (`TypedDict`)
`fmt`, `claim` (optional), `facts` (numbers and names taken from market data), `draft`, `score` (0–10),
`critique` (list of short issues), `round` (int), `owner_note` (≤200 chars), `decision`
(`approve` | `redo` | `skip`), `thread_id`, `history` (list of {round, draft, score}).

### Nodes
1. **draft**: reuse `services.x_poster.build_post()` (respects the weekday format and the content mix).
   Store `facts`: every number/ticker the data produced (e.g. `["$AVAX", "95%", "+1,992%", "20.9x"]`).
2. **guard** (deterministic, no LLM): length ≤ 280, `post_studio.BANNED` regex, no links/hashtags,
   ends with the disclaimer for data formats, and **every number in the draft must appear in `facts`**
   (blocks invented statistics). On failure: revert to the last passing draft (or the original) and
   add the reason to `critique`.
3. **critique** (DeepSeek, JSON only): score 0–10 against the rubric below; return
   `{"score": int, "issues": [str, ...]}`. Parse with `json.loads`, validate types and ranges;
   on any parse error treat as `score = 0` with issue "critic unavailable" and route to human_review
   (never loop forever on a broken critic).
4. **revise** (DeepSeek): rewrite using `critique` and `owner_note`. Must keep every fact unchanged,
   stay ≤ 280 chars, same format. Output plain text only.
5. **human_review**: `interrupt()` with the draft, its score and round. The Telegram layer sends the
   image card (existing `post_studio.render_card`) with buttons **✅ Approve · 🔁 Redo · ✖ Skip**.
   Resume with `Command(resume={"decision": ..., "note": ...})`.
6. **finalize**: send the final draft with the existing "✍️ Post on X" intent button (and post via API
   only if X keys exist **and** the owner approved). Write the hype ledger entry if it is a Reality
   Check, and append `{date, fmt, rounds, final_score}` to `data/post_loop_log.jsonl` for Loop 2.

### Critic rubric (put in the prompt, score each 0–2, total 10)
1. Hook: first line stops the scroll (curiosity, contrast or a surprising number).
2. Debate: contains a clear, defensible stance people could disagree with.
3. Clarity: a stranger understands it without context; no jargon.
4. Proof: numbers or a concrete example back the point.
5. Rules: calm, no buy/sell advice, no predictions, no hype words, fits 280 characters.

### Routing and limits
- `critique` → `human_review` if `score >= 8` or `round >= 3`, else `revise`.
- After a **redo** from the owner: allow up to 2 more automatic rounds (`round` cap becomes `round + 2`).
- Compile with a checkpointer; invoke with `{"recursion_limit": 20}` as a safety net.
- Daily cap: max **12 DeepSeek calls per day** for this loop (count in state file); when exceeded,
  skip critique/revise and send the current draft for review.

## Persistence
- `SqliteSaver` (package `langgraph-checkpoint-sqlite`) at `data/post_loop.sqlite`.
- `thread_id = "xpost-YYYY-MM-DD"` so a paused review survives restarts; a new day starts a new thread.
- `data/` is already git-ignored and excluded from the rsync deploy. Create files with mode `0600`.

## Telegram changes
- `bot.py` currently ignores updates without `"message"`. Add handling for `callback_query`:
  - Only accept callbacks whose `from.id`/chat equals `config.OWNER_CHAT_ID`; ignore everything else.
  - `callback_data` format: `pl:<approve|redo|skip>:<YYYY-MM-DD>` (≤ 64 bytes). Validate with a strict
    regex before use; ignore anything that does not match or refers to an old/unknown thread.
  - Always call `answerCallbackQuery` (stops the loading spinner).
  - Add `allowed_updates=["message","callback_query"]` to `getUpdates`.
- New owner-only command: `/redo <note>` (note ≤ 200 chars, strip control characters) resumes the
  current thread with `decision="redo"`.
- `/xpost` (on demand) runs the same graph with a separate thread id (`xpost-manual-<timestamp>`).

## Security requirements (must all be met)
1. **Owner-only control**: every button and `/redo` checks `OWNER_CHAT_ID`; nobody else can approve,
   redo, or see drafts. Reject callbacks from other chats silently (log at info level).
2. **No auto-posting**: even with X keys present, posting happens only after an explicit ✅ Approve.
3. **Prompt injection**: market data (coin names, symbols, trending lists) and the owner note are
   untrusted text. Wrap them in clearly marked data blocks in prompts, truncate (names ≤ 40 chars,
   note ≤ 200), strip control characters, and tell the model to treat them as data, not instructions.
4. **LLM output is data, never code**: no `eval`/`exec`, no shell calls, no URLs followed. Critic output
   must pass JSON schema checks; revise output must pass `guard`.
5. **No invented numbers**: the `guard` facts check above is mandatory.
6. **Secrets**: keys only from `.env` via `config`; never put keys, chat IDs or wallet data in prompts,
   logs, image cards or Telegram messages. Never commit `.env` or `data/`.
7. **Cost and loop limits**: 3 automatic rounds, `recursion_limit` 20, daily LLM-call cap, 40 s timeouts,
   and fall back to the plain draft on any LLM failure.
8. **Dependencies**: pin `langgraph` and `langgraph-checkpoint-sqlite` to exact versions in
   `requirements.txt`; install in the existing venv only. Optional: run `pip-audit` once.
9. **Fail safe**: if LangGraph or the checkpointer fails to import or load, fall back to today's
   behaviour (single draft with the image card) and log a warning. The bot must never crash.

## Tests (pytest, no network)
- Routing: high score → human_review; low score → revise; round cap → human_review.
- Guard: rejects >280 chars, banned words, links, and any number not in `facts`; reverts correctly.
- Critic parsing: valid JSON accepted; malformed JSON → score 0 → human_review (no infinite loop).
- Interrupt/resume with an in-memory checkpointer: approve → finalize; redo(note) → revise with note;
  skip → END; resuming after a simulated restart works with SqliteSaver in a temp dir.
- Telegram: callbacks from a non-owner are ignored; malformed `callback_data` ignored;
  `answerCallbackQuery` always called; `/redo` is owner-only and truncates notes.
- Daily LLM cap respected; LLM failure falls back to the plain draft.
- Existing test suite still passes.

## Deploy (owner, from the laptop)
```bash
git fetch origin && git checkout feature/post-loop   # review first; merge to main only when happy
# rsync as usual (data/ stays excluded), then on the VM:
~/telegram-agent/.venv/bin/pip install -r ~/telegram-agent/requirements.txt
systemctl --user restart uncle-tony && systemctl --user is-active uncle-tony
```
Then send `/xpost` on Telegram and try ✅ / 🔁 / ✖ and `/redo make it spicier`.

## Done means
All tests pass, `HANDOVER.md` updated with what was built and how to use it, branch pushed,
not merged to `main`.

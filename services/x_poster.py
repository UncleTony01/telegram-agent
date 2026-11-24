"""Daily Reality Check post for X (Twitter).

Once a day (X_POST_HOUR, VM local time) Uncle Tony picks a coin, runs a
Reality Check on a "10x" claim and posts a short, calm summary to X.

- The coin is the first one trending on CoinGecko that sits in the top 100 by
  market cap and wasn't posted in the past 14 days. If none fits, a fixed list
  of large coins is used in turn.
- Posts never contain links: on X's pay-per-use API a post with a URL costs
  about 13x more than a plain one.
- Nothing is ever posted without the owner's approval. The day's draft goes
  through Loop 1 (services/post_loop.py): a critic scores it, weak drafts are
  rewritten, then the owner taps Approve / Redo / Skip on Telegram. With all
  four X keys in .env an approved draft is posted via the API; without them
  the owner gets a "Post on X" button.
- Approved Reality Checks are written to the hype ledger, so /ledger can later
  show whether the claim happened.
- /xpost (owner only) shows a draft now, without posting: /xpost or /xpost AVAX 100B.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

import config
from utils.logger import get_logger

logger = get_logger(__name__)

STATE_FILE = Path(__file__).resolve().parent.parent / ".x_post_state.json"
POST_URL = "https://api.x.com/2/tweets"
MAX_LEN = 280
CHECK_EVERY_SECONDS = 300
REPEAT_DAYS = 14
FALLBACK_COINS = ["BTC", "ETH", "SOL", "XRP", "BNB", "AVAX", "ADA", "LINK", "DOT", "TRX", "TON", "SUI"]

_stop_event = threading.Event()
_thread: Optional[threading.Thread] = None


# ------------------------------ Keys -------------------------------------
def _keys() -> Optional[Dict[str, str]]:
    keys = {
        "api_key": getattr(config, "X_API_KEY", None),
        "api_secret": getattr(config, "X_API_SECRET", None),
        "access_token": getattr(config, "X_ACCESS_TOKEN", None),
        "access_secret": getattr(config, "X_ACCESS_SECRET", None),
    }
    return keys if all(keys.values()) else None


def live_mode() -> bool:
    return _keys() is not None


# ------------------------------ State ------------------------------------
def _read_state() -> Dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def _write_state(state: Dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state))
    except Exception as e:
        logger.warning("Could not save X post state: %s", e)


# ------------------------------ Coin choice ------------------------------
def _trending_symbols() -> List[str]:
    """Trending coins on CoinGecko that are in the top 100 by market cap."""
    from services.market_service import COINGECKO_BASE_URL, _fetch_json

    try:
        data = _fetch_json(f"{COINGECKO_BASE_URL}/search/trending")
    except Exception as e:
        logger.warning("Trending list unavailable: %s", e)
        return []
    out = []
    for c in data.get("coins", []):
        item = c.get("item", {})
        rank = item.get("market_cap_rank")
        if rank and rank <= 100 and item.get("symbol"):
            out.append(item["symbol"].upper())
    return out


def pick_symbol(state: Dict, now: float, trending: Optional[List[str]] = None) -> str:
    recent = {
        sym for sym, ts in (state.get("recent") or {}).items() if now - ts < REPEAT_DAYS * 86400
    }
    candidates = trending if trending is not None else _trending_symbols()
    for sym in candidates:
        if sym not in recent:
            return sym
    # Rotate through the fallback list, starting after the last one used.
    idx = int(state.get("fallback_idx", -1))
    for step in range(1, len(FALLBACK_COINS) + 1):
        sym = FALLBACK_COINS[(idx + step) % len(FALLBACK_COINS)]
        if sym not in recent:
            state["fallback_idx"] = (idx + step) % len(FALLBACK_COINS)
            return sym
    state["fallback_idx"] = (idx + 1) % len(FALLBACK_COINS)
    return FALLBACK_COINS[state["fallback_idx"]]


# ------------------------------ Post text --------------------------------
def _claim_phrase(r: Dict) -> str:
    from services.reality_check import _usd

    c = r["claim"]
    if c.kind == "multiple":
        return f"can {c.value:g}x"
    if c.kind == "price":
        return f"will hit {_usd(c.value)}"
    return f"will reach a {_usd(c.value)} market cap"


def format_post(r: Dict) -> str:
    """Hook first, numbers second, a question last. At most 280 characters; optional lines drop to fit."""
    from services.reality_check import _usd

    sym = r["symbol"]
    head = f"Someone will tell you ${sym} {_claim_phrase(r)}.\nHere's what that really means:"
    price_line = f"• Price: {_usd(r['price'])} → {_usd(r['target_price'])}"
    mcap_line = f"• Market cap: {_usd(r['mcap'])} → {_usd(r['target_mcap'])}"
    if r["rank_at_target"] <= 100:
        mcap_line += f" (#{r['rank_at_target']}"
        if r["passes"]:
            mcap_line += f", above {' & '.join(r['passes'][:2])}"
        mcap_line += ")"

    optional: List[str] = []
    d = r.get("dilution")
    if d:
        optional.append(f"• Supply still to come: +{d['extra_pct']:.0f}%")
    if r.get("ath"):
        if r["target_price"] and r["target_price"] > r["ath"]:
            optional.append(f"• That's above its all-time high ({_usd(r['ath'])})")
        else:
            optional.append(f"• All-time high: {_usd(r['ath'])}")

    tail = "Not impossible. Just know what you're betting on.\n\nWould you take that bet? (Data, not advice)"

    def build(opt: List[str]) -> str:
        return "\n".join([head, "", price_line, mcap_line] + opt + ["", tail])

    text = build(optional)
    while len(text) > MAX_LEN and optional:
        optional.pop()
        text = build(optional)
    if len(text) > MAX_LEN:
        text = "\n".join([head, "", price_line, "", tail])
    return text[:MAX_LEN]


def build_post(claim_text: Optional[str] = None, state: Optional[Dict] = None,
               now: Optional[float] = None) -> Optional[Dict]:
    """Return {'text', 'report', 'symbol', 'format'} or None if data is unavailable.

    With no claim, the format follows the day of the week (see services/content_mix.py).
    claim_text may also be a format name, e.g. "recovery" or "ai".
    """
    from services.content_mix import FORMATS, build_mixed_post, format_for_day
    from services.reality_check import analyse, fetch_inputs, parse_claim

    state = state if state is not None else {}
    now = now or time.time()
    fmt = "reality"
    if claim_text and claim_text.strip().lower() in FORMATS:
        fmt = claim_text.strip().lower()
        claim_text = None
    elif not claim_text:
        fmt = format_for_day(datetime.fromtimestamp(now).weekday())
    if fmt == "data":
        from services.content_mix import next_data_format

        fmt = next_data_format(state)

    if fmt != "reality":
        recent = {s for s, ts in (state.get("recent") or {}).items() if now - ts < REPEAT_DAYS * 86400}
        try:
            post = build_mixed_post(fmt, state, recent, trending=_trending_symbols() if fmt == "hype" else None)
        except Exception as e:
            logger.warning("%s post failed, falling back to a Reality Check: %s", fmt, e)
            post = None
        if post:
            return {"text": _with_angle(post["text"], fmt), "base_text": post["text"], "report": None,
                    "symbol": post.get("symbol"), "format": fmt}
        fmt = "reality"

    if claim_text:
        claim = parse_claim("/check " + claim_text)
    else:
        sym = pick_symbol(state, now)
        claim = parse_claim(f"/check {sym} 10x")
    if not claim:
        return None
    inputs = fetch_inputs(claim.symbol)
    if not inputs:
        return None
    report = analyse(claim, inputs)
    base = format_post(report)
    return {"text": _with_angle(base, "reality"), "base_text": base, "report": report,
            "symbol": report["symbol"], "format": "reality"}


def _with_angle(text: str, fmt: str) -> str:
    """Add an AI-written stance + question to data posts when DeepSeek is available."""
    from services.post_studio import add_discussion_angle

    return add_discussion_angle(text, fmt)


# ------------------------------ Posting to X -----------------------------
def _oauth_header(method: str, url: str, keys: Dict[str, str], extra: Optional[Dict[str, str]] = None) -> str:
    """OAuth 1.0a (user context) header. A JSON body is not part of the signature;
    `extra` holds query or form parameters, which are."""
    params = {
        "oauth_consumer_key": keys["api_key"],
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": keys["access_token"],
        "oauth_version": "1.0",
    }
    q = lambda s: urllib.parse.quote(str(s), safe="")
    signed = {**params, **(extra or {})}
    param_str = "&".join(f"{k}={v}" for k, v in sorted((q(k), q(v)) for k, v in signed.items()))
    base = "&".join([method.upper(), q(url), q(param_str)])
    signing_key = f"{q(keys['api_secret'])}&{q(keys['access_secret'])}"
    sig = hmac.new(signing_key.encode(), base.encode(), hashlib.sha1).digest()
    params["oauth_signature"] = base64.b64encode(sig).decode()
    _oauth_header.last_signature = params["oauth_signature"]  # for tests
    return "OAuth " + ", ".join(f'{q(k)}="{q(v)}"' for k, v in sorted(params.items()))


def post_to_x(text: str) -> str:
    """Post and return the new post's id. Raises on failure."""
    keys = _keys()
    if not keys:
        raise RuntimeError("X keys are not set")
    resp = requests.post(
        POST_URL,
        json={"text": text},
        headers={"Authorization": _oauth_header("POST", POST_URL, keys)},
        timeout=20,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"X API {resp.status_code}: {resp.text[:200]}")
    return resp.json()["data"]["id"]


# ------------------------------ Manual posting ---------------------------
INTENT_URL = "https://x.com/intent/post"


def intent_link(text: str) -> str:
    """A link that opens X (app or web) with the post already written. Free: no API needed."""
    return f"{INTENT_URL}?{urllib.parse.urlencode({'text': text}, quote_via=urllib.parse.quote)}"


def send_draft(chat_id: str, text: str, header: str, fmt: str = "reality") -> None:
    """Send the draft with its image card: save the picture, then tap the button to post."""
    import html as _html

    from services.telegram_service import send_message, send_photo

    markup = {"inline_keyboard": [[{"text": "✍️ Post on X", "url": intent_link(text)}]]}
    body = f"{header}\n\n<pre>{_html.escape(text, quote=False)}</pre>"
    hint = "\n<i>Save the picture, tap Post on X, then attach it. Or tap the text to copy.</i>"
    try:
        from services.post_studio import render_card

        card = render_card(text, fmt, handle=getattr(config, "X_HANDLE", None))
        if send_photo(chat_id, card, caption=body + hint, parse_mode="HTML", reply_markup=markup):
            return
    except Exception as e:
        logger.warning("Image card failed, sending text only: %s", e)
    send_message(chat_id, body + "\n<i>Tap the text to copy, or the button to open X with it ready.</i>",
                 parse_mode="HTML", reply_markup=markup)


# ------------------------------ Daily job --------------------------------
def _send_owner(text: str) -> None:
    chat_id = getattr(config, "OWNER_CHAT_ID", None) or getattr(config, "CHAT_ID", None)
    if not chat_id:
        logger.info("X poster (no owner chat): %s", text)
        return
    try:
        from services.telegram_service import send_message

        send_message(chat_id, text)
    except Exception as e:
        logger.warning("X poster Telegram send failed: %s", e)


def maybe_post_daily(now: Optional[float] = None) -> Optional[str]:
    """Post (or preview) once per day, at or after X_POST_HOUR. Returns the text, if any."""
    now = now or time.time()
    moment = datetime.fromtimestamp(now)
    if moment.hour < getattr(config, "X_POST_HOUR", 18):
        return None
    today = moment.strftime("%Y-%m-%d")
    state = _read_state()
    if state.get("last_day") == today:
        return None

    try:
        post = build_post(state=state, now=now)
    except Exception as e:
        logger.warning("X post build failed, will retry: %s", e)
        return None  # usually a CoinGecko rate limit; try again in 5 minutes
    if not post:
        return None

    # Mark the day as done before posting, so a failure never causes repeat posts.
    report = post["report"]
    state["last_day"] = today
    if post.get("symbol"):
        state.setdefault("recent", {})[post["symbol"]] = now
    _write_state(state)

    # Loop 1: critic + rewrites, then the owner approves on Telegram. Posting to X
    # (when keys exist) happens only after that approval.
    try:
        from services import post_loop

        if post_loop.available():
            post_loop.run_new(today, post_loop.to_prebuilt(post))
            return post["text"]
    except Exception as e:
        logger.warning("Post loop failed, sending the plain draft: %s", e)

    # Fallback: the plain draft with its image card. Never posted automatically.
    chat_id = getattr(config, "OWNER_CHAT_ID", None) or getattr(config, "CHAT_ID", None)
    if chat_id:
        try:
            send_draft(chat_id, post["text"], f"📝 Today's X post is ready ({len(post['text'])}/280)",
                       fmt=post.get("format", "reality"))
        except Exception as e:
            logger.warning("X draft send failed: %s", e)

    if report:
        try:
            from services.hype_ledger import record_check

            record_check(report)
        except Exception as e:
            logger.warning("Hype ledger write failed: %s", e)
    return post["text"]


def _run_loop() -> None:
    while True:
        try:
            maybe_post_daily()
        except Exception as e:
            logger.error("X poster check failed: %s", e)
        if _stop_event.wait(CHECK_EVERY_SECONDS):
            return


def start_x_poster() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=_run_loop, daemon=True)
    _thread.start()
    logger.info("X poster started (%s mode)", "live" if live_mode() else "preview")


def stop_x_poster() -> None:
    _stop_event.set()


# ------------------------------ /xpost -----------------------------------
def handle_xpost_command(chat_id: str, text: str) -> None:
    """Owner only. Shows a draft post now; never posts."""
    from services.telegram_service import send_message
    from utils.chat_filter import is_owner

    if not is_owner(chat_id):
        send_message(chat_id, "🔒 /xpost is for the bot owner.")
        return
    claim_text = text.strip().split(None, 1)[1] if len(text.strip().split(None, 1)) > 1 else None
    try:
        post = build_post(claim_text=claim_text, state=dict(_read_state()))
    except Exception as e:
        logger.error("X draft failed: %s", e)
        send_message(chat_id, "Market data is unavailable right now. Try again in a minute.")
        return
    if not post:
        send_message(chat_id, "I couldn't build a draft for that. Try /xpost, /xpost ai, /xpost journey, /xpost data or /xpost AVAX 100B")
        return
    try:
        from services import post_loop

        if post_loop.available():
            send_message(chat_id, "📝 Drafting. A critic scores it and rewrites weak versions, "
                                  "then you get it to approve. About a minute.")
            post_loop.start_manual(chat_id, post_loop.to_prebuilt(post))
            return
    except Exception as e:
        logger.warning("Post loop unavailable for /xpost: %s", e)
    mode = "sent to you to approve" if live_mode() else "sent to you to post yourself"
    hour = getattr(config, "X_POST_HOUR", 18)
    send_draft(
        chat_id,
        post["text"],
        f"📝 Draft ({len(post['text'])}/280). Not posted.\nDaily post at {hour:02d}:00, {mode}.",
        fmt=post.get("format", "reality"),
    )

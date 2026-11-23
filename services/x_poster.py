"""Daily Reality Check post for X (Twitter).

Once a day (X_POST_HOUR, VM local time) Uncle Tony picks a coin, runs a
Reality Check on a "10x" claim and posts a short, calm summary to X.

- The coin is the first one trending on CoinGecko that sits in the top 100 by
  market cap and wasn't posted in the past 14 days. If none fits, a fixed list
  of large coins is used in turn.
- Posts never contain links: on X's pay-per-use API a post with a URL costs
  about 13x more than a plain one.
- Until all four X keys are in .env, nothing is posted. The day's draft goes to
  the owner on Telegram instead ("preview mode"), so you can judge the posts
  before paying for anything.
- Every post is also written to the hype ledger, so /ledger can later show
  whether the claim happened.
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
def format_post(r: Dict) -> str:
    """A plain-text post of at most 280 characters. Optional lines are dropped to fit."""
    from services.reality_check import _usd

    sym = r["symbol"]
    head = f"Reality Check: ${sym} {r['claim'].text.split(None, 1)[-1]} → {_usd(r['target_price'])}"
    now_line = f"Now {_usd(r['price'])} · rank #{r['rank_now'] or '?'}"
    if r["multiple"]:
        now_line += f" · needs {r['multiple']:,.1f}x"

    if r["rank_at_target"] > 100:
        rank_line = f"Market cap at target: {_usd(r['target_mcap'])}, still outside today's top 100."
    else:
        rank_line = f"Market cap at target: {_usd(r['target_mcap'])}, #{r['rank_at_target']} today"
        if r["passes"]:
            rank_line += f", above {', '.join(r['passes'][:3])}"
        rank_line += "."

    optional: List[str] = []
    d = r.get("dilution")
    if d:
        optional.append(f"Supply can still grow ~{d['extra_pct']:.0f}%.")
    if r.get("ath"):
        if r["target_price"] and r["target_price"] > r["ath"]:
            optional.append(f"Above the all-time high ({_usd(r['ath'])}).")
        else:
            optional.append(f"All-time high: {_usd(r['ath'])}.")

    tail = "Not impossible, not guaranteed. Just the maths. Data, not advice."

    lines = [head, "", now_line, rank_line] + optional + ["", tail]
    text = "\n".join(lines)
    while len(text) > MAX_LEN and optional:
        optional.pop()
        lines = [head, "", now_line, rank_line] + optional + ["", tail]
        text = "\n".join(lines)
    if len(text) > MAX_LEN:
        text = "\n".join([head, "", now_line, "", tail])
    return text[:MAX_LEN]


def build_post(claim_text: Optional[str] = None, state: Optional[Dict] = None,
               now: Optional[float] = None) -> Optional[Dict]:
    """Return {'text', 'report'} or None if data is unavailable."""
    from services.reality_check import analyse, fetch_inputs, parse_claim

    if claim_text:
        claim = parse_claim("/check " + claim_text)
    else:
        sym = pick_symbol(state if state is not None else {}, now or time.time())
        claim = parse_claim(f"/check {sym} 10x")
    if not claim:
        return None
    inputs = fetch_inputs(claim.symbol)
    if not inputs:
        return None
    report = analyse(claim, inputs)
    return {"text": format_post(report), "report": report}


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
    state.setdefault("recent", {})[report["symbol"]] = now
    _write_state(state)

    if live_mode():
        try:
            post_id = post_to_x(post["text"])
            logger.info("Posted to X: %s", post_id)
            _send_owner(f"📝 Posted today's Reality Check to X:\n\n{post['text']}")
        except Exception as e:
            logger.error("X post failed: %s", e)
            _send_owner(
                f"📝 Today's X post didn't go out ({e}). I'll try again tomorrow.\n\nDraft:\n\n{post['text']}"
            )
            return post["text"]
    else:
        _send_owner(
            "📝 Draft X post for today (preview: X keys aren't set, so nothing was posted):\n\n"
            + post["text"]
        )

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
        send_message(chat_id, "I couldn't build a draft for that. Try /xpost or /xpost AVAX 100B")
        return
    mode = "live: the daily post goes to X" if live_mode() else "preview: X keys not set"
    hour = getattr(config, "X_POST_HOUR", 18)
    send_message(
        chat_id,
        f"📝 Draft ({len(post['text'])}/280 characters). Not posted.\n"
        f"Daily post at {hour:02d}:00, {mode}.\n\n{post['text']}",
    )

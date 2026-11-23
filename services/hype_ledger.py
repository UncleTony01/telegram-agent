"""Hype ledger: a record of every claim checked, and what actually happened.

Each /check is appended to data/hype_ledger.jsonl with the claim and the market
at that moment. /ledger (owner only) reviews checks that are 30+ and 90+ days
old against today's price: did the target happen, and how far did price move?

Over time this becomes a dataset nobody else has: which kinds of claims tend to
come true. Privacy by design: no chat IDs or usernames are stored, only the
claim and public market data.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

LEDGER_FILE = Path(__file__).resolve().parent.parent / "data" / "hype_ledger.jsonl"
REVIEW_DAYS = (30, 90)
DAY = 86400


def record_check(report: Dict, now: Optional[float] = None) -> Dict:
    claim = report["claim"]
    entry = {
        "id": uuid.uuid4().hex[:10],
        "ts": now or time.time(),
        "symbol": report["symbol"],
        "coin_id": report.get("coin_id") or _coin_id_for(report["symbol"]),
        "claim": claim.text,
        "kind": claim.kind,
        "value": claim.value,
        "target_price": report["target_price"],
        "price_then": report["price"],
        "mcap_then": report["mcap"],
        "multiple_needed": report["multiple"],
    }
    LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def _coin_id_for(symbol: str) -> Optional[str]:
    from services.market_service import resolve_coin_id

    return resolve_coin_id(symbol)


def load_entries() -> List[Dict]:
    if not LEDGER_FILE.exists():
        return []
    entries = []
    for line in LEDGER_FILE.read_text().splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _current_prices(coin_ids: List[str]) -> Dict[str, float]:
    if not coin_ids:
        return {}
    from services.market_service import COINGECKO_BASE_URL, _fetch_json

    data = _fetch_json(
        f"{COINGECKO_BASE_URL}/simple/price",
        params={"ids": ",".join(sorted(set(coin_ids))), "vs_currencies": "usd"},
    )
    return {k: v.get("usd") for k, v in data.items() if v.get("usd")}


def review(now: Optional[float] = None, prices: Optional[Dict[str, float]] = None) -> Dict:
    """Group entries by age and score them against today's prices."""
    now = now or time.time()
    entries = load_entries()
    due = [e for e in entries if now - e["ts"] >= REVIEW_DAYS[0] * DAY and e.get("coin_id")]
    if prices is None:
        prices = _current_prices([e["coin_id"] for e in due])

    scored = []
    for e in due:
        p = prices.get(e["coin_id"])
        if not p:
            continue
        scored.append({
            **e,
            "age_days": int((now - e["ts"]) // DAY),
            "price_now": p,
            "change_pct": (p / e["price_then"] - 1) * 100,
            "hit": bool(e.get("target_price")) and p >= e["target_price"],
            "progress_pct": _progress(e["price_then"], e.get("target_price"), p),
        })
    hits = sum(1 for s in scored if s["hit"])
    return {"total": len(entries), "reviewed": scored, "hits": hits}


def _progress(start: float, target: Optional[float], now: float) -> Optional[float]:
    """How far price travelled toward the target, as a % of the distance (can be negative)."""
    if not target or target == start:
        return None
    return (now - start) / (target - start) * 100


def format_review(result: Dict) -> str:
    lines = [f"📒 <b>Hype ledger</b>: {result['total']} claims checked"]
    reviewed = result["reviewed"]
    if not reviewed:
        lines.append("Nothing is 30+ days old yet. Check back later.")
        return "\n".join(lines)
    lines.append(f"{len(reviewed)} ready to review · {result['hits']} reached their target\n")
    for s in sorted(reviewed, key=lambda s: -s["ts"])[:15]:
        when = datetime.fromtimestamp(s["ts"], tz=timezone.utc).strftime("%d %b")
        mark = "✅" if s["hit"] else "·"
        prog = f", {s['progress_pct']:.0f}% of the way" if s["progress_pct"] is not None and not s["hit"] else ""
        lines.append(
            f"{mark} {s['symbol']} \"{s['claim']}\" ({when}, {s['age_days']}d ago): "
            f"{s['change_pct']:+.0f}% since{prog}"
        )
    return "\n".join(lines)


def handle_ledger_command(chat_id: str) -> None:
    from services.telegram_service import send_message
    from utils.chat_filter import is_owner

    if not is_owner(chat_id):
        send_message(chat_id, "🔒 The hype ledger is private to the bot owner.")
        return
    try:
        result = review()
    except Exception as e:
        logger.error("Ledger review failed: %s", e)
        send_message(chat_id, "Couldn't fetch prices for the review right now. Try again later.")
        return
    send_message(chat_id, format_review(result), parse_mode="HTML")

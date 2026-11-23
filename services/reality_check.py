"""Reality Check: maths-checked answers to market claims.

    /check AVAX 100B    → market-cap target ($100 billion)
    /check AVAX $20     → price target
    /check SOL 10x      → multiple of today's price

The maths runs in code, so the numbers can't be invented: implied market cap,
the rank that would mean today, the coins it would pass, the effect of coins
still to be issued, and how the target compares with the past year and the
all-time high. No AI is needed. The tone stays neutral: it never says a target
is "impossible" or "guaranteed", and it never says buy or sell.

Every check is also written to the hype ledger (see services/hype_ledger.py).
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from services.market_service import COINGECKO_BASE_URL, _fetch_json, resolve_coin_id
from utils.logger import get_logger

logger = get_logger(__name__)

USAGE = (
    "🔎 <b>Reality Check</b>\n"
    "Check any price claim against the maths.\n\n"
    "<code>/check AVAX 100B</code>  market cap target\n"
    "<code>/check AVAX $20</code>   price target\n"
    "<code>/check SOL 10x</code>    multiple of today's price"
)

_SUFFIX = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}


@dataclass
class Claim:
    symbol: str
    kind: str  # "mcap" | "price" | "multiple"
    value: float
    text: str


# ------------------------------ Parsing ----------------------------------
def parse_claim(text: str) -> Optional[Claim]:
    """Parse '/check AVAX 100B', '/check avax $20', '/check SOL 10x', 'AVAX to 100b'."""
    body = re.sub(r"^/check(@\w+)?", "", text.strip(), flags=re.IGNORECASE).strip()
    parts = [p for p in re.split(r"[\s,]+", body) if p and p.lower() not in {"to", "at", "hit", "reach", "mcap", "price"}]
    if len(parts) < 2:
        return None
    symbol = parts[0].upper().lstrip("$")
    raw = parts[1].replace(",", "")

    m = re.fullmatch(r"(\d+(?:\.\d+)?)x", raw, re.IGNORECASE)
    if m:
        return Claim(symbol, "multiple", float(m.group(1)), body)

    m = re.fullmatch(r"\$?(\d+(?:\.\d+)?)([kmbt])", raw, re.IGNORECASE)
    if m:
        value = float(m.group(1)) * _SUFFIX[m.group(2).upper()]
        # Small K/M values are almost certainly prices (e.g. "BTC 150K"), big ones market caps.
        kind = "price" if value < 1e7 else "mcap"
        return Claim(symbol, kind, value, body)

    m = re.fullmatch(r"\$?(\d+(?:\.\d+)?)", raw)
    if m:
        return Claim(symbol, "price", float(m.group(1)), body)
    return None


# ------------------------------ Data -------------------------------------
def _coin_id(symbol: str) -> Optional[str]:
    coin_id = resolve_coin_id(symbol)
    if coin_id:
        return coin_id
    try:
        found = _fetch_json(f"{COINGECKO_BASE_URL}/search", params={"query": symbol})
        for coin in found.get("coins", []):
            if str(coin.get("symbol", "")).upper() == symbol.upper():
                return coin.get("id")
    except Exception as e:
        logger.warning("Coin search failed for %s: %s", symbol, e)
    return None


def fetch_inputs(symbol: str) -> Optional[Dict]:
    """Everything the maths needs, in 3 CoinGecko calls."""
    coin_id = _coin_id(symbol)
    if not coin_id:
        return None
    coin = _fetch_json(f"{COINGECKO_BASE_URL}/coins/markets", params={"vs_currency": "usd", "ids": coin_id})
    if not coin:
        return None
    top = _fetch_json(
        f"{COINGECKO_BASE_URL}/coins/markets",
        params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": 100, "page": 1},
    )
    chart = {}
    try:
        chart = _fetch_json(
            f"{COINGECKO_BASE_URL}/coins/{coin_id}/market_chart",
            params={"vs_currency": "usd", "days": 365, "interval": "daily"},
        )
    except Exception as e:  # the year range is a bonus, not essential
        logger.warning("Year chart unavailable for %s: %s", coin_id, e)
    return {"coin": coin[0], "top": top or [], "prices": chart.get("prices", [])}


# ------------------------------ Maths ------------------------------------
def analyse(claim: Claim, inputs: Dict) -> Dict:
    c = inputs["coin"]
    price = float(c["current_price"])
    mcap = float(c.get("market_cap") or 0)
    circ = float(c.get("circulating_supply") or 0) or (mcap / price if price else 0)
    max_supply = c.get("max_supply") or c.get("total_supply")
    max_supply = float(max_supply) if max_supply else None

    if claim.kind == "mcap":
        target_mcap = claim.value
        target_price = target_mcap / circ if circ else None
    elif claim.kind == "price":
        target_price = claim.value
        target_mcap = target_price * circ
    else:
        target_price = price * claim.value
        target_mcap = target_price * circ

    multiple = target_price / price if price and target_price else None
    my_id = c.get("id")
    others = [x for x in inputs["top"] if x.get("id") != my_id and x.get("market_cap")]
    rank = 1 + sum(1 for x in others if float(x["market_cap"]) > target_mcap)
    passes = [
        x["symbol"].upper()
        for x in sorted(others, key=lambda x: -float(x["market_cap"]))
        if mcap < float(x["market_cap"]) <= target_mcap
    ]

    dilution = None
    if max_supply and circ and max_supply > circ * 1.01:
        dilution = {
            "extra_pct": (max_supply / circ - 1) * 100,
            "price_at_full_supply": target_mcap / max_supply,
            "max_supply": max_supply,
        }

    year = None
    prices = [p[1] for p in inputs.get("prices", []) if p and p[1]]
    if prices:
        year = {"high": max(prices), "low": min(prices)}
        last_at_or_above = None
        for ts, p in reversed(inputs["prices"]):
            if p and target_price and p >= target_price:
                last_at_or_above = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                break
        year["last_at_target"] = last_at_or_above

    return {
        "claim": claim,
        "name": c.get("name", claim.symbol),
        "coin_id": my_id,
        "symbol": c.get("symbol", claim.symbol).upper(),
        "price": price,
        "mcap": mcap,
        "rank_now": c.get("market_cap_rank"),
        "target_price": target_price,
        "target_mcap": target_mcap,
        "multiple": multiple,
        "rank_at_target": rank,
        "passes": passes,
        "dilution": dilution,
        "year": year,
        "ath": c.get("ath"),
    }


# ------------------------------ Formatting -------------------------------
def _usd(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(v) >= div:
            n = v / div
            return f"${n:,.2f}{suf}" if n < 10 else f"${n:,.1f}{suf}".replace(".0" + suf, suf)
    if v >= 100:
        return f"${v:,.0f}"
    if v >= 1:
        return f"${v:,.2f}"
    return f"${v:.6f}".rstrip("0")


def _pct(multiple: float) -> str:
    change = (multiple - 1) * 100
    return f"{change:+,.0f}%"


def format_report(r: Dict) -> str:
    e = lambda s: html.escape(str(s), quote=False)
    lines: List[str] = []
    lines.append(f"🔎 <b>Reality Check: {e(r['symbol'])} → {_usd(r['target_price'])}</b>")
    lines.append(f"<i>Claim: {e(r['claim'].text)}</i>")
    lines.append("")
    lines.append(f"Now: {_usd(r['price'])} · market cap {_usd(r['mcap'])} · rank #{r['rank_now'] or '?'}")
    lines.append(f"Target: {_usd(r['target_price'])} · market cap {_usd(r['target_mcap'])}")
    if r["multiple"]:
        lines.append(f"Move needed: <b>{r['multiple']:,.1f}x</b> ({_pct(r['multiple'])})")

    lines.append("")
    lines.append("<b>What it would mean today</b>")
    if r["rank_at_target"] > 100:
        rank_line = "• It would still be outside today's top 100 by market cap"
    else:
        rank_line = f"• It would be the #{r['rank_at_target']} crypto by market cap"
    if r["passes"]:
        shown = ", ".join(r["passes"][:5]) + (f" and {len(r['passes']) - 5} more" if len(r["passes"]) > 5 else "")
        rank_line += f", passing {shown}"
    lines.append(rank_line + ".")
    lines.append("• Assumes the others stay where they are. If the whole market rises, so do they.")

    d = r["dilution"]
    if d:
        lines.append("")
        lines.append("<b>Coins still to come</b>")
        lines.append(
            f"• Supply can grow ~{d['extra_pct']:.0f}% (max {d['max_supply'] / 1e6:,.0f}M coins)."
        )
        lines.append(f"• At full supply, the same market cap ≈ {_usd(d['price_at_full_supply'])} a coin.")

    y = r["year"]
    lines.append("")
    lines.append("<b>History</b>")
    if y:
        lines.append(f"• Past year range: {_usd(y['low'])} – {_usd(y['high'])}")
        if y["last_at_target"]:
            lines.append(f"• Last at or above the target: {y['last_at_target']:%d %b %Y}")
        else:
            lines.append("• Not reached in the past year.")
    if r["ath"]:
        if r["target_price"] and r["target_price"] > r["ath"]:
            lines.append(f"• Above the all-time high ({_usd(r['ath'])}): new territory.")
        else:
            from_ath = r["ath"] / r["price"] if r["price"] else None
            lines.append(f"• All-time high {_usd(r['ath'])}" + (f" ({from_ath:,.1f}x from today)." if from_ath else "."))

    lines.append("")
    lines.append("Not impossible, not guaranteed. Just the maths behind the claim.")
    lines.append("<i>Data from CoinGecko. Data, not financial advice.</i>")
    return "\n".join(lines)


# ------------------------------ Command ----------------------------------
def handle_check_command(chat_id: str, text: str) -> None:
    from services.telegram_service import send_message

    claim = parse_claim(text)
    if not claim:
        send_message(chat_id, USAGE, parse_mode="HTML")
        return
    try:
        inputs = fetch_inputs(claim.symbol)
    except Exception as e:
        logger.error("Reality check data failed: %s", e)
        send_message(chat_id, "Market data is unavailable right now. Try again in a minute.")
        return
    if not inputs:
        send_message(chat_id, f"I couldn't find {claim.symbol}. Try the ticker, e.g. /check AVAX 100B")
        return

    report = analyse(claim, inputs)
    send_message(chat_id, format_report(report), parse_mode="HTML")

    try:
        from services.hype_ledger import record_check

        record_check(report)
    except Exception as e:  # the ledger must never break the reply
        logger.warning("Hype ledger write failed: %s", e)

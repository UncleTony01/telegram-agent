"""Read-only view of the owner's OKX spot portfolio.

Uses the ``okx`` CLI with the API key stored in ``~/.okx/config.toml`` on the
server. This module only ever *reads* balances; it never places orders.

Public functions:
- get_portfolio()            -> Portfolio dict (cached briefly)
- format_portfolio()         -> text for /portfolio and the market briefs
- position_section(symbol)   -> "Your position" text for /analysis, or None
- check_position_alerts()    -> sends break-even / drawdown alerts when due
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

import config
from utils.logger import get_logger

logger = get_logger(__name__)

MIN_POSITION_USD = 1.0  # ignore dust balances below this value
STABLECOINS = {"USDT", "USDC", "DAI", "FDUSD"}
CACHE_SECONDS = 60
DRAWDOWN_STEP_PCT = 10  # alert each time a coin falls another 10% below your average buy price
STATE_FILE = Path(__file__).resolve().parent.parent / ".portfolio_state.json"

_cache: Dict = {"ts": 0.0, "data": None}
_lock = threading.Lock()


class PortfolioUnavailable(Exception):
    """Raised when balances can't be read (no API key, network error, ...)."""


# ------------------------ Reading balances --------------------------------
def _num(value) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_balance(raw) -> Dict:
    """Turn ``okx account balance`` JSON into a simple portfolio dict."""
    accounts = raw if isinstance(raw, list) else (raw or {}).get("data", [])
    if not accounts:
        raise PortfolioUnavailable("empty balance response")
    account = accounts[0]

    positions: List[Dict] = []
    cash = 0.0
    for d in account.get("details", []):
        ccy = d.get("ccy")
        qty = _num(d.get("eq")) or 0.0
        value = _num(d.get("eqUsd")) or 0.0
        if value < MIN_POSITION_USD:
            continue
        if ccy in STABLECOINS:
            cash += value
            continue
        avg = _num(d.get("openAvgPx")) or _num(d.get("accAvgPx"))
        price = value / qty if qty else None
        pnl = _num(d.get("spotUpl"))
        if pnl is None and avg and price:
            pnl = (price - avg) * qty
        pnl_pct = ((price / avg) - 1) * 100 if (avg and price) else None
        positions.append({
            "symbol": ccy,
            "qty": qty,
            "value": value,
            "price": price,
            "avg_price": avg,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        })

    positions.sort(key=lambda p: p["value"], reverse=True)
    total = _num(account.get("totalEq")) or (cash + sum(p["value"] for p in positions))
    return {"total": total, "cash": cash, "positions": positions, "ts": time.time()}


def get_portfolio(force: bool = False) -> Dict:
    """Return the current portfolio, cached for CACHE_SECONDS."""
    with _lock:
        if not force and _cache["data"] and time.time() - _cache["ts"] < CACHE_SECONDS:
            return _cache["data"]
    from services.okx_service import OKXError, _run_okx

    try:
        data = parse_balance(_run_okx(["account", "balance"]))
    except (OKXError, PortfolioUnavailable) as e:
        raise PortfolioUnavailable(str(e)) from e
    with _lock:
        _cache.update(ts=time.time(), data=data)
    return data


def get_position(symbol: str, portfolio: Optional[Dict] = None) -> Optional[Dict]:
    portfolio = portfolio or get_portfolio()
    for p in portfolio["positions"]:
        if p["symbol"] == symbol.upper():
            return p
    return None


# ------------------------ Formatting --------------------------------------
def _usd(v: Optional[float]) -> str:
    return "n/a" if v is None else f"${v:,.2f}"


def _price(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    return f"${v:,.0f}" if v >= 1000 else f"${v:,.2f}" if v >= 1 else f"${v:.6f}"


def _signed_usd(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    return f"{'+' if v >= 0 else '−'}${abs(v):,.2f}"


def _signed_pct(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    return f"{'+' if v >= 0 else '−'}{abs(v):.1f}%"


def format_portfolio(portfolio: Dict, previous_total: Optional[float] = None) -> str:
    lines = ["💼 Your portfolio"]
    total_line = f"Total: {_usd(portfolio['total'])}"
    if previous_total:
        change = portfolio["total"] - previous_total
        total_line += f" ({_signed_usd(change)} since last brief)"
    lines.append(total_line)
    lines.append("")
    total_pnl = 0.0
    for p in portfolio["positions"]:
        icon = "🟢" if (p["pnl"] or 0) >= 0 else "🔴"
        lines.append(
            f"{icon} {p['symbol']}: {_usd(p['value'])} · {_signed_usd(p['pnl'])} ({_signed_pct(p['pnl_pct'])})"
        )
        total_pnl += p["pnl"] or 0
    if portfolio["cash"]:
        lines.append(f"💵 Cash (USDT): {_usd(portfolio['cash'])}")
    if portfolio["positions"]:
        lines.append("")
        lines.append(f"Overall profit/loss on coins: {_signed_usd(total_pnl)}")
    return "\n".join(lines)


def position_section(symbol: str, support: Optional[float] = None, resistance: Optional[float] = None) -> Optional[str]:
    """Return a 'Your position' block for a coin you hold, else None."""
    try:
        pos = get_position(symbol)
    except PortfolioUnavailable:
        return None
    if not pos or not pos["avg_price"] or not pos["price"]:
        return None
    avg, price = pos["avg_price"], pos["price"]
    lines = [f"📌 Your {pos['symbol']} position", ""]
    lines.append(f"Holding: {pos['qty']:.6g} {pos['symbol']} ({_usd(pos['value'])})")
    lines.append(f"Avg buy price: {_price(avg)} · Now: {_price(price)}")
    lines.append(f"Profit/loss: {_signed_usd(pos['pnl'])} ({_signed_pct(pos['pnl_pct'])})")
    if price < avg:
        lines.append(f"Needs +{(avg / price - 1) * 100:.1f}% to break even")
    else:
        lines.append("✅ In profit")
    if resistance:
        where = "above" if resistance >= avg else "below"
        lines.append(f"Next resistance {_price(resistance)} is {where} your buy price")
    if support:
        lines.append(f"Nearest support {_price(support)} ({_signed_pct((support / price - 1) * 100)} from now)")
    lines.append("")
    lines.append("Not financial advice.")
    return "\n".join(lines)


# ------------------------ Position alerts ---------------------------------
def _read_state() -> Dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def _write_state(state: Dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state))
    except Exception as e:
        logger.warning("Could not save portfolio state: %s", e)


def position_alerts(portfolio: Dict, state: Dict) -> List[str]:
    """Work out which alerts are due and update ``state`` in place.

    - Break-even: the price climbs back to your average buy price.
    - Drawdown: each further DRAWDOWN_STEP_PCT below your average buy price.
    State per coin: {"above": bool, "level": deepest drawdown step alerted}.
    """
    messages = []
    coins = state.setdefault("coins", {})
    for p in portfolio["positions"]:
        if p["pnl_pct"] is None:
            continue
        sym, pct = p["symbol"], p["pnl_pct"]
        s = coins.get(sym)
        level = int(-pct // DRAWDOWN_STEP_PCT) if pct < 0 else 0  # 1 = 10-20% down, 2 = 20-30% down
        if s is None:
            # First time we see this coin: remember where it is, don't alert.
            coins[sym] = {"above": pct >= 0, "level": level}
            continue
        if pct >= 0 and not s.get("above"):
            messages.append(
                f"✅ {sym} is back at your break-even\n\n"
                f"Now {_price(p['price'])} vs your avg buy price {_price(p['avg_price'])} "
                f"({_signed_pct(pct)}).\nNot financial advice."
            )
            s["above"], s["level"] = True, 0
        elif pct < 0:
            s["above"] = False
            if level > s.get("level", 0):
                messages.append(
                    f"⚠️ {sym} is now {_signed_pct(pct)} below your avg buy price\n\n"
                    f"Now {_price(p['price'])} vs avg {_price(p['avg_price'])}. "
                    f"Position: {_usd(p['value'])} ({_signed_usd(p['pnl'])}).\nNot financial advice."
                )
            s["level"] = level
    return messages


def check_position_alerts() -> int:
    """Fetch the portfolio and send any due position alerts. Returns count sent."""
    if not getattr(config, "CHAT_ID", None):
        return 0
    try:
        portfolio = get_portfolio(force=True)
    except PortfolioUnavailable as e:
        logger.info("Portfolio not available for alerts: %s", e)
        return 0
    state = _read_state()
    messages = position_alerts(portfolio, state)
    _write_state(state)
    from services.telegram_service import send_message

    for text in messages:
        send_message(config.CHAT_ID, text)
    return len(messages)


def handle_portfolio_command(chat_id: str) -> None:
    from services.telegram_service import send_message

    try:
        send_message(chat_id, format_portfolio(get_portfolio(force=True)))
    except PortfolioUnavailable:
        send_message(chat_id, "I can't reach your OKX account right now. Please try again in a few minutes.")

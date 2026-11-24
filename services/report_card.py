"""Visual analysis card for Telegram (HTML parse mode).

One organized message per coin:
  header (price, 24h change, 24h range bar) → verdict → momentum →
  price ladder (levels + your avg buy price) → scenarios → plan →
  your position → Uncle Tony's short take.

The card is built from the rule-based Tactical Engine data, so it always works;
the AI only writes the 2–3 sentence "take" at the end and is optional.

Tone rule: calm and factual. No red/green alarm colours, no hype or fear words,
no urgency. Information first; the reader decides.
"""
from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from utils.logger import get_logger

logger = get_logger(__name__)

BAR_CELLS = 10


# ------------------------ Small formatting helpers -----------------------
def esc(value) -> str:
    return html.escape(str(value), quote=False)


def price(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    if v >= 1000:
        return f"${v:,.0f}"
    if v >= 1:
        return f"${v:,.2f}"
    return f"${v:.6f}".rstrip("0")


def signed_pct(v: Optional[float]) -> str:
    if v is None:
        return "n/a"
    return f"{'+' if v >= 0 else '−'}{abs(v):.1f}%"


def bar(percent: Optional[float], cells: int = BAR_CELLS) -> str:
    """▰▰▰▱▱▱▱▱▱▱ style bar for a 0–100 value."""
    p = max(0.0, min(100.0, float(percent or 0)))
    filled = int(round(p / 100 * cells))
    return "▰" * filled + "▱" * (cells - filled)


def range_bar(low: Optional[float], high: Optional[float], now: Optional[float], cells: int = 10) -> Optional[str]:
    """$low ━━━━●━━━━ $high — where today's price sits in its 24h range."""
    if not (low and high and now) or high <= low:
        return None
    pos = int(round((min(max(now, low), high) - low) / (high - low) * (cells - 1)))
    track = "".join("●" if i == pos else "━" for i in range(cells))
    return f"{price(low)} {track} {price(high)}"


def strip_html(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text))


# ------------------------ Labels / emoji ---------------------------------
def action_badge(action: str) -> str:
    a = (action or "WAIT").upper()
    if a in ("BUY", "LONG", "STRONG BUY"):
        return "🔷 Buy setup"
    if a in ("SELL", "SHORT", "STRONG SELL"):
        return "🔶 Sell setup"
    return "⏸️ Wait · no action needed"


def bias_badge(bias: str) -> str:
    b = (bias or "Neutral").lower()
    if "bull" in b:
        return "↗️ leaning up"
    if "bear" in b:
        return "↘️ leaning down"
    return "➡️ neutral"


def risk_badge(level: str) -> str:
    lv = (level or "MODERATE").upper()
    return {"LOW": "low", "MODERATE": "moderate", "MEDIUM": "moderate", "HIGH": "high"}.get(lv, lv.lower())


def rsi_label(rsi: Optional[float]) -> str:
    if rsi is None:
        return "n/a"
    if rsi < 30:
        return "low (oversold)"
    if rsi > 70:
        return "high (overbought)"
    return "mid-range"


def trend_line(p: Optional[float], ema20: Optional[float], ema50: Optional[float]) -> Optional[str]:
    if not (p and ema20 and ema50):
        return None
    if p < ema20 < ema50:
        return f"↘️ Trend: below EMA20 ({price(ema20)}) and EMA50 ({price(ema50)})"
    if p > ema20 > ema50:
        return f"↗️ Trend: above EMA20 ({price(ema20)}) and EMA50 ({price(ema50)})"
    return f"↔️ Trend: mixed · EMA20 {price(ema20)} · EMA50 {price(ema50)}"


# ------------------------ Sections ---------------------------------------
def ladder(now: float, levels: List[Tuple[float, str]]) -> List[str]:
    """Price levels sorted high→low with the current price slotted in."""
    rows = [(lvl, label) for lvl, label in levels if lvl]
    rows.append((now, "📍 <b>Now</b>"))
    rows.sort(key=lambda r: r[0], reverse=True)
    out = []
    for lvl, label in rows:
        if lvl == now and "Now" in label:
            out.append(f"{label}  <b>{price(now)}</b>")
        else:
            out.append(f"{label}  {price(lvl)}  <i>({signed_pct((lvl / now - 1) * 100)})</i>")
    return out


def render_card(report, opportunity=None, position: Optional[Dict] = None,
                take: Optional[str] = None, high_24h: Optional[float] = None,
                low_24h: Optional[float] = None, now: Optional[datetime] = None) -> str:
    """Build the HTML card from a TacticalReport (+ optional extras)."""
    p = report.price
    lines: List[str] = []

    # Header
    change = report.change_24h
    arrow = "▲" if (change or 0) >= 0 else "▼"
    lines.append(f"<b>🪙 {esc(report.symbol)}/USDT</b>")
    head = f"<b>{price(p)}</b>"
    if change is not None:
        head += f"   {arrow} {signed_pct(change)} <i>(24h)</i>"
    lines.append(head)
    rb = range_bar(low_24h, high_24h, p)
    if rb:
        lines.append(f"<code>{rb}</code>")

    # Verdict
    lines += ["", f"<b>⚖️ VERDICT:  {action_badge(report.recommendation)}</b>"]
    lines.append(f"Bias {bias_badge(report.bias)}  ·  Risk {risk_badge(report.risk_level)}")
    lines.append(f"Confidence   <code>{bar(report.confidence)}</code> {report.confidence}%")
    score = getattr(opportunity, "score", None) if opportunity is not None else report.opportunity_score
    if score is not None:
        lines.append(f"Opportunity  <code>{bar(score)}</code> {score}/100")

    # Momentum
    lines += ["", "<b>📊 Momentum</b>"]
    if report.rsi is not None:
        lines.append(f"RSI {report.rsi:.0f}  <code>{bar(report.rsi)}</code>  {rsi_label(report.rsi)}")
    tl = trend_line(p, report.ema20, report.ema50)
    if tl:
        lines.append(tl)

    # Ladder
    if p:
        levels = [
            (report.resistance, "🔸 Resistance"),
            (report.support, "🔹 Support"),
            (report.take_profit_1, "🎯 Target"),
            (report.stop_loss, "🛡️ Stop"),
        ]
        if position and position.get("avg_price"):
            levels.append((position["avg_price"], "🔷 Your avg buy"))
        lines += ["", "<b>🎯 Key levels</b>"] + ladder(p, levels)

    # Scenarios
    scen = [
        ("↘️ Lower", report.bearish_probability),
        ("↗️ Higher", report.bullish_probability),
        ("↔️ Range", report.sideways_probability),
    ]
    scen.sort(key=lambda s: s[1] or 0, reverse=True)
    lines += ["", "<b>🔮 Possible paths</b>"]
    for name, prob in scen:
        lines.append(f"<code>{bar(prob)}</code> {prob}%  {name}")

    # Plan
    lines += ["", "<b>💡 Plan</b>"]
    rec = (report.recommendation or "WAIT").upper()
    if rec in ("BUY", "SELL") and (report.aggressive_entry or report.stop_loss or report.take_profit_1):
        if report.aggressive_entry:
            lines.append(f"Entry {price(report.aggressive_entry)}")
        if report.stop_loss:
            lines.append(f"Stop {price(report.stop_loss)}")
        if report.take_profit_1:
            lines.append(f"Target {price(report.take_profit_1)}")
        if report.risk_reward:
            lines.append(f"Risk/reward 1 : {report.risk_reward:.1f}")
    elif report.resistance and report.support:
        lines.append("No action needed right now.")
        lines.append(f"Levels to watch: above <b>{price(report.resistance)}</b> or below <b>{price(report.support)}</b>.")
    else:
        lines.append("No clear setup. No action needed right now.")

    # Your position
    if position and position.get("avg_price") and p:
        avg = position["avg_price"]
        pnl_pct = (p / avg - 1) * 100
        lines += ["", "<b>📌 Your position</b>"]
        lines.append(f"{position['qty']:.6g} {esc(report.symbol)} ≈ ${position['value']:,.2f}")
        lines.append(f"{signed_pct(pnl_pct)} vs your avg buy {price(avg)}")
        if p < avg:
            lines.append(f"Break-even is +{(avg / p - 1) * 100:.1f}% away")
        lines.append("<i>Unrealized: it only becomes a gain or loss if you sell.</i>")

    # Uncle Tony's take
    if take:
        lines += ["", "<b>🧠 Uncle Tony's take</b>", esc(take.strip())]

    stamp = (now or datetime.now()).strftime("%H:%M")
    lines += ["", f"<i>Updated {stamp} · Stick to your plan · Not financial advice</i>"]
    return "\n".join(lines)


# ------------------------ AI take ----------------------------------------
def _take_prompt(report, position: Optional[Dict]) -> str:
    held = ""
    if position and position.get("avg_price"):
        held = (f"\nThe reader HOLDS this coin: average buy price {price(position['avg_price'])}, "
                f"current price {price(report.price)}.")
    return (
        "You are Uncle Tony, a calm, plain-speaking crypto trading mentor.\n"
        f"Coin: {report.symbol}. Price {price(report.price)}. Recommendation {report.recommendation}. "
        f"Bias {report.bias}. RSI {report.rsi}. Support {price(report.support)}, resistance {price(report.resistance)}. "
        f"Bearish {report.bearish_probability}%, bullish {report.bullish_probability}%, "
        f"sideways {report.sideways_probability}%.{held}\n\n"
        "Write Uncle Tony's take in 2 or 3 short sentences, under 60 words total. "
        "Plain text only: no markdown, no lists, no headings, no emojis.\n"
        "Tone rules: calm, balanced and factual, like a patient mentor. The reader wants to avoid "
        "fear and greed. Never use hype or fear words (crash, dump, moon, explode, panic, FOMO, "
        "bloodbath, knife, squeeze, huge, massive) and never create urgency. Don't tell them to buy "
        "or sell now. Mention what to watch next and remind them that sticking to a plan matters more "
        "than any single move."
    )


def _local_take(report, position: Optional[Dict]) -> str:
    rec = (report.recommendation or "WAIT").upper()
    if rec == "WAIT":
        msg = (f"No clear direction yet. The next useful information is whether price moves above "
               f"{price(report.resistance)} or below {price(report.support)}.")
    elif rec == "BUY":
        msg = (f"The setup is leaning up. If it fits your plan, decide your size and stop level "
               f"in advance rather than reacting to each move.")
    else:
        msg = (f"The setup is leaning down. A calm approach is to watch how price behaves near "
               f"{price(report.support)} before making any decision.")
    if position and position.get("avg_price") and report.price and report.price < position["avg_price"]:
        msg += " Your position is below your buy price; that's normal in a down market and nothing needs to be decided today."
    return msg


def get_take(report, position: Optional[Dict]) -> str:
    """Short AI take, checked by the analysis loop (facts, calm tone, critic).
    Falls back to a rule-based take so it never fails."""
    try:
        from services.analysis_loop import checked_text

        text = checked_text("take", _take_prompt(report, position))
        if text:
            return text
    except Exception as e:
        logger.info("AI take unavailable for %s: %s", report.symbol, e)
    return _local_take(report, position)


# ------------------------ Entry point ------------------------------------
def build_analysis_card(symbol: str, include_position: bool = True) -> str:
    """Fetch data, run the rule-based engines, and return the HTML card."""
    from services.local_narrator import build_tactical_report
    from services.okx_service import get_market_overview
    from services.opportunity_scanner import calculate_opportunity_score

    symbol = symbol.upper()
    overview = get_market_overview(symbol)
    opportunity = None
    try:
        opportunity = calculate_opportunity_score(overview)
        overview["_opportunity_result"] = opportunity
    except Exception as e:
        logger.warning("Opportunity score failed for %s: %s", symbol, e)

    report = build_tactical_report(overview)

    position = None
    if include_position:
        try:
            from services.portfolio_service import get_position

            position = get_position(symbol)
        except Exception:
            position = None  # portfolio is optional

    take = get_take(report, position)
    return render_card(
        report, opportunity, position, take,
        high_24h=overview.get("high_24h_usd"), low_24h=overview.get("low_24h_usd"),
    )

"""
Market Intelligence Engine

Read-only interpreter that converts an AnalysisObject into a compact
MarketIntelligence dataclass for downstream consumption (dashboards, alerts,
briefings).

This module DOES NOT calculate indicators or modify the AnalysisObject.
It only reads existing fields and produces human-friendly, enumerated
assessments plus concise reasoning and a one-line summary.

Usage:
    from core.analysis_object import AnalysisObject
    from services.market_intelligence_engine import generate_market_intelligence

    mi = generate_market_intelligence(analysis)

The module also provides a simple BTC example when executed directly so
it is easy to verify fields are populated.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional

from core.analysis_object import AnalysisObject


# ---------------------------------------------------------------------------
# Market Intelligence dataclass
# ---------------------------------------------------------------------------
@dataclass
class MarketIntelligence:
    market_controller: str
    market_phase: str
    trend_quality: str
    momentum_quality: str
    participation_quality: str
    structure_quality: str
    setup_quality: str
    attention_level: str
    invalidation: str
    reasoning: List[str] = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Helper mapping and safe access utilities
# ---------------------------------------------------------------------------

def _safe(v, default=None):
    return v if v is not None else default


def generate_market_intelligence(analysis: AnalysisObject) -> MarketIntelligence:
    """
    Interpret an AnalysisObject and return a MarketIntelligence instance.

    Rules: read-only. No recalculation of indicators.
    """
    # Shortcuts
    price = analysis.market_data.price
    ema20 = analysis.indicators.ema20
    ema50 = analysis.indicators.ema50
    rsi = analysis.indicators.rsi
    macd_trend = (analysis.indicators.macd_trend or "Neutral").lower()
    macd_hist = analysis.indicators.macd_histogram

    funding = analysis.derivatives.funding_rate
    oi = analysis.derivatives.open_interest_usd
    oi_change = analysis.derivatives.oi_change_24h

    ms = analysis.market_structure
    conf = analysis.confluence
    dec = analysis.decision

    reasoning: List[str] = []

    # ----------------- Market Controller -----------------
    # Prefer explicit long/short participation if available, else confluence + bias
    market_controller = "BALANCED"
    try:
        lsr = analysis.derivatives.long_short_ratio
        if lsr is not None:
            # long_short_ratio >1 => more longs
            if lsr > 1.05:
                market_controller = "BUYERS"
            elif lsr < 0.95:
                market_controller = "SELLERS"
            else:
                market_controller = "BALANCED"
            reasoning.append(f"Long/Short Ratio: {lsr}")
        else:
            # fallback to confluence scores and decision bias
            if conf.bullish_score > conf.bearish_score + 5 or dec.bias.lower().startswith("bull"):
                market_controller = "BUYERS"
            elif conf.bearish_score > conf.bullish_score + 5 or dec.bias.lower().startswith("bear"):
                market_controller = "SELLERS"
            else:
                market_controller = "BALANCED"
            reasoning.append(f"Confluence B:{conf.bullish_score} / S:{conf.bearish_score}")
    except Exception:
        market_controller = "BALANCED"

    # ----------------- Market Phase -----------------
    market_phase = "TREND"
    try:
        if getattr(ms, "in_range", False):
            market_phase = "RANGE"
            reasoning.append("Price inside defined range")
        elif ms.break_of_structure:
            # If a BOS exists, treat as breakout (or reversal if phase indicates accumulation)
            if "Bull" in str(ms.break_of_structure) or "Bear" in str(ms.break_of_structure):
                market_phase = "BREAKOUT"
                reasoning.append(f"Break of structure: {ms.break_of_structure}")
        elif "Accumulation" in str(ms.phase) or "Distribution" in str(ms.phase):
            market_phase = "REVERSAL"
            reasoning.append(f"Phase: {ms.phase}")
        else:
            market_phase = "TREND"
    except Exception:
        market_phase = "TREND"

    # ----------------- Trend Quality -----------------
    tq = "NEUTRAL"
    try:
        ts = (analysis.indicators.trend_strength or "").lower()
        if "very" in ts:
            tq = "VERY STRONG"
        elif "strong" in ts:
            tq = "STRONG"
        elif "weak" in ts:
            tq = "WEAK"
        else:
            tq = "NEUTRAL"
        reasoning.append(f"Trend strength: {analysis.indicators.trend_strength}")
    except Exception:
        tq = "NEUTRAL"

    # ----------------- Momentum Quality -----------------
    mq = "STABLE"
    try:
        if macd_trend == "bullish" or (rsi is not None and rsi >= 65):
            mq = "ACCELERATING"
            reasoning.append("Momentum accelerating (MACD/RSI)")
        elif macd_trend == "bearish" or (rsi is not None and rsi <= 35):
            mq = "WEAKENING"
            reasoning.append("Momentum weakening (MACD/RSI)")
        else:
            mq = "STABLE"
    except Exception:
        mq = "STABLE"

    # ----------------- Participation Quality -----------------
    pq = "NORMAL"
    try:
        vs = getattr(analysis.indicators, "volume_strength", "Normal")
        if str(vs).lower() in ("very high", "high"):
            pq = "HIGH"
            reasoning.append(f"Volume: {vs}")
        elif str(vs).lower() in ("very low", "low"):
            pq = "LOW"
            reasoning.append(f"Volume: {vs}")
        else:
            pq = "NORMAL"
    except Exception:
        pq = "NORMAL"

    # Consider Open Interest participation as well
    try:
        if oi_change is not None:
            if oi_change > 0:
                if pq != "HIGH":
                    reasoning.append(f"OI ↑ {oi_change}")
                    pq = "HIGH"
            elif oi_change < 0:
                if pq != "LOW":
                    reasoning.append(f"OI ↓ {oi_change}")
                    pq = "LOW"
    except Exception:
        pass

    # ----------------- Structure Quality -----------------
    sq = "UNCERTAIN"
    try:
        if ms.break_of_structure and (ms.higher_high or ms.higher_low):
            sq = "HEALTHY"
            reasoning.append("Healthy structure (BOS + higher highs/lows)")
        elif ms.lower_low or ms.lower_high:
            sq = "BROKEN"
            reasoning.append("Broken structure (lower highs/lows)")
        elif ms.in_range:
            sq = "UNCERTAIN"
            reasoning.append("Range-bound structure")
        else:
            sq = "UNCERTAIN"
    except Exception:
        sq = "UNCERTAIN"

    # ----------------- Setup Quality -----------------
    # Use opportunity score (decision.opportunity_score) and confluence.trade_quality
    setup = "C"
    try:
        opp = int(getattr(dec, "opportunity_score", 0) or 0)
        cq = int(getattr(conf, "confidence", 0) or 0)
        # Combine both signals conservatively
        if opp >= 85 and cq >= 80:
            setup = "A+"
        elif opp >= 75 and cq >= 60:
            setup = "A"
        elif opp >= 60:
            setup = "B"
        else:
            setup = "C"
        reasoning.append(f"Opportunity: {opp} / Confidence: {cq}")
    except Exception:
        setup = "C"

    # ----------------- Attention Level -----------------
    attention = "IGNORE"
    try:
        conviction = int(getattr(dec, "conviction_score", 0) or 0)
        if opp >= 80 and conviction >= 65:
            attention = "HIGH PRIORITY"
        elif opp >= 70:
            attention = "WATCHLIST"
        else:
            attention = "IGNORE"
        reasoning.append(f"Conviction: {conviction}")
    except Exception:
        attention = "IGNORE"

    # ----------------- Invalidation -----------------
    inv = "None"
    try:
        if getattr(dec, "stop_loss", None) is not None:
            inv = f"stop_loss: {dec.stop_loss}"
            reasoning.append("Invalidation: stop loss present")
        elif getattr(ms, "bos_level", None) is not None:
            inv = f"bos_level: {ms.bos_level}"
            reasoning.append("Invalidation: break-of-structure level")
        else:
            inv = "None"
    except Exception:
        inv = "None"

    # ----------------- Reasoning (additional concise evidence) -----------------
    # Price vs EMAs
    try:
        if price is not None and ema20 is not None:
            if price > ema20:
                reasoning.append("Price above EMA20")
            else:
                reasoning.append("Price below EMA20")
        if price is not None and ema50 is not None:
            if price > ema50:
                reasoning.append("Price above EMA50")
            else:
                reasoning.append("Price below EMA50")
    except Exception:
        pass

    # MACD evidence
    try:
        if macd_trend == "bullish":
            reasoning.append("MACD bullish")
        elif macd_trend == "bearish":
            reasoning.append("MACD bearish")
    except Exception:
        pass

    # Funding sanity
    try:
        if funding is not None:
            if funding < 0:
                reasoning.append(f"Funding negative ({funding})")
            else:
                reasoning.append(f"Funding positive ({funding})")
    except Exception:
        pass

    # Confluence highlights
    try:
        if conf.bullish_score and conf.bullish_score > conf.bearish_score:
            reasoning.append(f"Bullish confluence: {conf.bullish_score}")
        elif conf.bearish_score and conf.bearish_score > conf.bullish_score:
            reasoning.append(f"Bearish confluence: {conf.bearish_score}")
    except Exception:
        pass

    # Decision summary
    try:
        if dec.recommended_action:
            reasoning.append(f"Recommended: {dec.recommended_action}")
    except Exception:
        pass

    # Deduplicate reasoning and keep concise
    compact = []
    for r in reasoning:
        if r and r not in compact:
            compact.append(r)

    # ----------------- One-line summary -----------------
    try:
        summary = f"{market_controller} control; {pq} participation; setup {setup}; attention={attention}."
    except Exception:
        summary = "Market intelligence generated"

    mi = MarketIntelligence(
        market_controller=_safe(market_controller, "BALANCED"),
        market_phase=_safe(market_phase, "TREND"),
        trend_quality=_safe(tq, "NEUTRAL"),
        momentum_quality=_safe(mq, "STABLE"),
        participation_quality=_safe(pq, "NORMAL"),
        structure_quality=_safe(sq, "UNCERTAIN"),
        setup_quality=_safe(setup, "C"),
        attention_level=_safe(attention, "IGNORE"),
        invalidation=_safe(inv, "None"),
        reasoning=compact,
        summary=summary,
    )

    return mi


# ---------------------------------------------------------------------------
# Quick verification helper (construct a BTC example when run directly)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Minimal BTC example using AnalysisObject structure without calling other engines
    from core.analysis_object import AnalysisObject

    # Build an example AnalysisObject with plausible populated fields
    a = AnalysisObject(symbol="BTC")
    a.market_data.price = 64000.0
    a.indicators.ema20 = 63000.0
    a.indicators.ema50 = 61000.0
    a.indicators.rsi = 68.5
    a.indicators.macd_trend = "Bullish"
    a.indicators.macd_histogram = 12.3
    a.indicators.trend_strength = "Very Strong"
    a.indicators.volume_strength = "High"

    a.derivatives.funding_rate = 0.0005
    a.derivatives.open_interest_usd = 1200000000.0
    a.derivatives.oi_change_24h = 2.5
    a.derivatives.long_short_ratio = 1.12

    a.market_structure.in_range = False
    a.market_structure.break_of_structure = "Bullish BOS"
    a.market_structure.bos_level = 62000.0
    a.market_structure.higher_high = True
    a.market_structure.higher_low = True

    a.confluence.bullish_score = 78
    a.confluence.bearish_score = 22
    a.confluence.confidence = 82
    a.confluence.trade_quality = 4

    a.decision.recommended_action = "WATCH FOR ENTRY"
    a.decision.bias = "Bullish"
    a.decision.opportunity_score = 87
    a.decision.conviction_score = 80
    a.decision.stop_loss = 61800.0

    mi = generate_market_intelligence(a)

    # Print every field and ensure no field is empty
    out = asdict(mi)
    for k, v in out.items():
        if v is None or (isinstance(v, (list, str)) and len(v) == 0):
            print(f"{k}: <EMPTY> -> filling fallback")
        print(f"{k}: {v}")

    # Simple final check
    missing = [k for k, v in out.items() if v is None or (isinstance(v, (list, str)) and len(v) == 0)]
    if not missing:
        print("\nVerification: All fields populated")
    else:
        print("\nVerification: Missing fields:", missing)

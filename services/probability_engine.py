"""Probability & Decision Intelligence Engine for Uncle Tony AI.

This module scores every available technical indicator and converts them into
estimated probabilities for competing market scenarios:
Bullish Continuation, Bearish Breakdown, and Sideways Consolidation.

The engine does not predict the future with certainty. It quantifies the
weight of evidence for each scenario and surfaces the most likely outcome
as a structured ProbabilityResult.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Scenario labels (canonical strings used throughout the module)
SCENARIO_BULLISH  = "Bullish Continuation"
SCENARIO_BEARISH  = "Bearish Breakdown"
SCENARIO_SIDEWAYS = "Sideways Consolidation"


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class ProbabilityResult:
    """Holds market probability estimates, supporting evidence, and
    the recommended action derived from probability thresholds."""

    bullish_probability: int          # 0-100
    bearish_probability: int          # 0-100
    sideways_probability: int         # 0-100
    most_likely: str                  # one of SCENARIO_* constants
    confidence: int                   # 0-100, gap between 1st and 2nd scenario
    reasoning: List[str]              # evidence strings Hermes can use verbatim
    trade_quality: int                # 1-5 star score
    recommended_action: str           # e.g. "BUY", "WAIT FOR BREAKOUT", "NO TRADE"
    risk_reward: Optional[float]      # e.g. 2.3  (means 2.3:1)


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def calculate_market_probability(overview: dict) -> ProbabilityResult:
    """Evaluates market overview data and returns probability estimates.

    Parameters
    ----------
    overview : dict
        The complete dictionary returned by get_market_overview().
        No additional API calls are made inside this function.

    Returns
    -------
    ProbabilityResult
        Bullish / bearish / sideways probabilities (sum = 100%),
        the most likely outcome, confidence, evidence list,
        trade quality score, recommended action, and risk-reward estimate.
    """

    # ── helpers ───────────────────────────────────────────────────────────────

    def _float(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def _lower(val: Any) -> str:
        return str(val).strip().lower() if val is not None else ""

    # ── read inputs ───────────────────────────────────────────────────────────

    price   = _float(overview.get("price_usd") or overview.get("price"))
    ema20   = _float(overview.get("ema20"))
    ema50   = _float(overview.get("ema50"))
    rsi     = _float(overview.get("rsi"))
    high24  = _float(overview.get("high_24h_usd") or overview.get("high_24h"))
    low24   = _float(overview.get("low_24h_usd")  or overview.get("low_24h"))
    funding = _float(overview.get("funding_rate") or overview.get("funding"))

    market_structure = _lower(
        overview.get("market_structure") or overview.get("market_structure_trend")
    )

    # MACD
    macd_signal    = _lower(
        overview.get("macd_signal") or overview.get("macd_trend") or overview.get("macd")
    )
    macd_histogram = _float(overview.get("macd_histogram") or overview.get("macd_hist"))

    # Break of Structure
    bos = _lower(
        overview.get("break_of_structure") or overview.get("bos") or overview.get("market_bos")
    )

    # Confluence (dict or scalar)
    conf_bull: Optional[float] = None
    conf_bear: Optional[float] = None
    conf_val = overview.get("confluence") or overview.get("confluence_score")
    if isinstance(conf_val, dict):
        conf_bull = _float(conf_val.get("bullish") or conf_val.get("Bullish"))
        conf_bear = _float(conf_val.get("bearish") or conf_val.get("Bearish"))
    elif isinstance(conf_val, (int, float, str)):
        c = _float(conf_val)
        if c is not None:
            if price is not None and ema20 is not None and price > ema20:
                conf_bull = c
            else:
                conf_bear = c
    # direct key overrides
    if overview.get("confluence_bullish") is not None:
        conf_bull = _float(overview["confluence_bullish"])
    if overview.get("confluence_bearish") is not None:
        conf_bear = _float(overview["confluence_bearish"])

    # OI change
    oi_increases: Optional[bool] = None
    if "oi_increases" in overview:
        oi_increases = bool(overview["oi_increases"])
    elif "open_interest_increases" in overview:
        oi_increases = bool(overview["open_interest_increases"])
    else:
        oi_change = overview.get("oi_change") or overview.get("open_interest_change")
        if oi_change is not None:
            try:
                oi_increases = float(oi_change) > 0.0
            except (ValueError, TypeError):
                pass

    # ── scoring ───────────────────────────────────────────────────────────────

    bull_sc = 0
    bear_sc = 0
    side_sc = 0
    conf_bonus = 0
    evidence: List[str] = []

    # — EMA Trend
    if price is not None and ema20 is not None:
        if price > ema20:
            bull_sc += 10
            evidence.append("Price above EMA20")
        else:
            bear_sc += 10
            evidence.append("Price has fallen below EMA20")

    if price is not None and ema50 is not None:
        if price > ema50:
            bull_sc += 20
            evidence.append("Price is above the longer-term EMA50")
        else:
            bear_sc += 20
            evidence.append("EMA50 remains overhead as resistance")

    # — RSI
    if rsi is not None:
        if rsi > 60:
            bull_sc += 12
            evidence.append("RSI favors buyers")
        elif rsi >= 55:
            bull_sc += 8
            evidence.append("RSI constructive")
        elif rsi >= 45:
            side_sc += 12
            evidence.append("RSI is in neutral territory")
        elif rsi >= 40:
            bear_sc += 8
            evidence.append("RSI reflects mild bearish pressure")
        else:
            bear_sc += 12
            evidence.append("RSI is in oversold territory")

    # — MACD Signal
    if macd_signal in ("bullish", "buy", "positive"):
        bull_sc += 10
        evidence.append("MACD momentum improving")
    elif macd_signal in ("bearish", "sell", "negative"):
        bear_sc += 10
        evidence.append("MACD momentum weakening")
    elif macd_signal:
        side_sc += 6
        evidence.append("MACD is in neutral momentum")

    # — MACD Histogram
    if macd_histogram is not None:
        if macd_histogram > 0:
            bull_sc += 5
            evidence.append("Positive MACD histogram")
        elif macd_histogram < 0:
            bear_sc += 5
            evidence.append("Negative MACD histogram")

    # — Market Structure
    if market_structure in ("bullish", "bull", "uptrend", "bull trend"):
        bull_sc += 25
        evidence.append("Market structure confirms bullish trend")
    elif market_structure in ("bearish", "bear", "downtrend", "bear trend"):
        bear_sc += 25
        evidence.append("Market structure confirms bearish trend")
    elif market_structure in ("range", "sideways", "consolidation"):
        side_sc += 25
        evidence.append("Range structure")

    # — Break of Structure
    if "bullish" in bos:
        bull_sc += 20
        evidence.append("Bullish break of structure detected")
    elif "bearish" in bos:
        bear_sc += 20
        evidence.append("Bearish break of structure detected")
    elif bos in ("none", ""):
        side_sc += 8

    # — Funding Rate
    if funding is not None:
        if funding >= 0.0003:
            bull_sc += 3
            bear_sc += 4
            evidence.append("Elevated funding rate — crowded longs")
        elif funding > 0.0:
            bull_sc += 3
            side_sc += 3
            evidence.append("Neutral funding")
        elif funding < 0.0:
            bull_sc += 5
            evidence.append("Negative funding — potential short squeeze")
        else:
            side_sc += 3

    # — Open Interest
    if oi_increases is True:
        conf_bonus += 5
        evidence.append("Rising open interest can accelerate current move")

    # — Confluence
    if conf_bull is not None:
        bull_sc += int(conf_bull / 5)
    if conf_bear is not None:
        bear_sc += int(conf_bear / 5)

    # ── normalise to 100 % ────────────────────────────────────────────────────

    total = bull_sc + bear_sc + side_sc
    if total == 0:
        bull_pct = 34
        bear_pct = 33
        side_pct = 33
    else:
        bull_pct = int(round(bull_sc / total * 100))
        bear_pct = int(round(bear_sc / total * 100))
        side_pct = int(round(side_sc / total * 100))

        remainder = 100 - (bull_pct + bear_pct + side_pct)
        if remainder != 0:
            mx = max(bull_pct, bear_pct, side_pct)
            if bull_pct == mx:
                bull_pct += remainder
            elif bear_pct == mx:
                bear_pct += remainder
            else:
                side_pct += remainder

    # ── most likely / confidence ──────────────────────────────────────────────

    pct_map = {
        SCENARIO_BULLISH:  bull_pct,
        SCENARIO_BEARISH:  bear_pct,
        SCENARIO_SIDEWAYS: side_pct,
    }
    most_likely = max(pct_map, key=lambda k: pct_map[k])

    sorted_vals = sorted(pct_map.values(), reverse=True)
    gap = sorted_vals[0] - sorted_vals[1]
    confidence = min(100, gap + conf_bonus)

    # Scale confidence by how much core market data was actually available,
    # so missing inputs cannot produce a falsely certain result.
    core_inputs = (price, ema20, ema50, rsi, funding)
    available = sum(v is not None for v in core_inputs)
    confidence = int(confidence * available / len(core_inputs))

    # ── recommended action ────────────────────────────────────────────────────
    #
    # Converts probabilities into a human decision.

    action = _derive_action(bull_pct, bear_pct, side_pct, most_likely, market_structure)

    # ── trade quality (1-5) ───────────────────────────────────────────────────

    quality = _derive_quality(
        bull_sc=bull_sc,
        bear_sc=bear_sc,
        side_sc=side_sc,
        confidence=confidence,
        market_structure=market_structure,
        bos=bos,
        conf_bull=conf_bull,
        conf_bear=conf_bear,
    )

    # ── risk-reward estimate ──────────────────────────────────────────────────

    risk_reward = _estimate_risk_reward(
        price=price,
        ema20=ema20,
        high24=high24,
        low24=low24,
        action=action,
    )

    return ProbabilityResult(
        bullish_probability=bull_pct,
        bearish_probability=bear_pct,
        sideways_probability=side_pct,
        most_likely=most_likely,
        confidence=confidence,
        reasoning=evidence,
        trade_quality=quality,
        recommended_action=action,
        risk_reward=risk_reward,
    )


# ---------------------------------------------------------------------------
# Helper: recommended action
# ---------------------------------------------------------------------------

def _derive_action(
    bull_pct: int,
    bear_pct: int,
    side_pct: int,
    most_likely: str,
    market_structure: str,
) -> str:
    """Return a decision label from probability percentages."""
    if most_likely == SCENARIO_BULLISH:
        if bull_pct > 70:
            return "BUY"
        elif bull_pct >= 55:
            return "BUY ON BREAKOUT"
        else:
            return "WAIT FOR BREAKOUT"
    elif most_likely == SCENARIO_BEARISH:
        if bear_pct > 60:
            return "SELL"
        else:
            return "CAUTION — BEARISH BIAS"
    else:  # Sideways
        if market_structure in ("range", "sideways", "consolidation"):
            return "WAIT — RANGE BOUND"
        return "NO TRADE"


# ---------------------------------------------------------------------------
# Helper: trade quality
# ---------------------------------------------------------------------------

def _derive_quality(
    bull_sc: int,
    bear_sc: int,
    side_sc: int,
    confidence: int,
    market_structure: str,
    bos: str,
    conf_bull: Optional[float],
    conf_bear: Optional[float],
) -> int:
    """Score trade quality 1-5 based on signal alignment."""
    total = bull_sc + bear_sc + side_sc
    if total == 0:
        return 1

    directional = max(bull_sc, bear_sc)
    directional_pct = int(directional / total * 100) if total else 0

    # Perfect 5: very strong conviction + BOS + high confluence
    bos_bullish  = "bullish" in bos
    bos_bearish  = "bearish" in bos
    bos_detected = bos_bullish or bos_bearish

    high_conf_bull = conf_bull is not None and conf_bull > 85
    high_conf_bear = conf_bear is not None and conf_bear > 85

    if (
        directional_pct > 85
        and confidence > 85
        and bos_detected
        and (high_conf_bull or high_conf_bear)
        and market_structure not in ("range", "sideways", "consolidation")
    ):
        return 5

    # Score between 1 and 4
    score = 2
    if confidence >= 60:
        score += 1
    if directional_pct >= 70:
        score += 1
    if bos_detected:
        score += 1
    if market_structure in ("range", "sideways", "consolidation"):
        score = max(1, score - 1)

    return max(1, min(4, score))


# ---------------------------------------------------------------------------
# Helper: risk-reward estimation
# ---------------------------------------------------------------------------

def _estimate_risk_reward(
    price: Optional[float],
    ema20: Optional[float],
    high24: Optional[float],
    low24: Optional[float],
    action: str,
) -> Optional[float]:
    """Estimate risk-reward ratio from price, EMA20, and 24h range.

    Returns the ratio as a float (e.g. 2.3 means 2.3 : 1) or None if
    there is insufficient data.
    """
    if price is None:
        return None

    if action in ("BUY", "BUY ON BREAKOUT", "WAIT FOR BREAKOUT"):
        # Nearest support: EMA20 or low24, whichever is higher (closer)
        support_candidates = [v for v in (ema20, low24) if v is not None and v < price]
        if not support_candidates:
            return None
        support = max(support_candidates)
        # Nearest resistance: high24 or a 2% projection above price
        resistance = high24 if (high24 is not None and high24 > price) else price * 1.02

        risk   = price - support
        reward = resistance - price

    elif action in ("SELL", "CAUTION — BEARISH BIAS"):
        # Nearest resistance: EMA20 or high24, whichever is lower (closer)
        resistance_candidates = [v for v in (ema20, high24) if v is not None and v > price]
        if not resistance_candidates:
            return None
        resistance = min(resistance_candidates)
        # Nearest support: low24 or a 2% projection below price
        support = low24 if (low24 is not None and low24 < price) else price * 0.98

        risk   = resistance - price
        reward = price - support

    else:
        return None

    if risk <= 0:
        return None

    return round(reward / risk, 2)

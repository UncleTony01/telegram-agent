"""Trade Decision Engine service for Uncle Tony AI.

This module evaluates all available technical indicators and outputs a structured
TradeDecision dataclass.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class TradeDecision:
    """Dataclass representing a trade decision and its technical parameters."""
    market_bias: str
    recommended_action: str
    confidence: int
    trade_quality: int
    entry_type: str
    aggressive_entry: Optional[float]
    conservative_entry: Optional[float]
    stop_loss: Optional[float]
    take_profit_1: Optional[float]
    take_profit_2: Optional[float]
    risk_reward: Optional[float]
    reason: str


def generate_trade_decision(overview: dict) -> TradeDecision:
    """Generates a professional TradeDecision based on market overview data.

    Parameters
    ----------
    overview : dict
        The complete dictionary returned by get_market_overview().

    Returns
    -------
    TradeDecision
        A structured object containing the trade decision parameters.
    """
    def safe_float(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    # Read necessary keys
    price = safe_float(overview.get("price_usd") or overview.get("price"))
    ema20 = safe_float(overview.get("ema20"))
    ema50 = safe_float(overview.get("ema50"))
    rsi = safe_float(overview.get("rsi"))
    macd = overview.get("macd")
    market_structure = overview.get("market_structure") or overview.get("market_structure_trend")
    funding = safe_float(overview.get("funding_rate") or overview.get("funding"))
    oi = safe_float(overview.get("open_interest_usd") or overview.get("open_interest") or overview.get("oi"))
    high_24h = safe_float(overview.get("high_24h_usd") or overview.get("high_24h"))
    low_24h = safe_float(overview.get("low_24h_usd") or overview.get("low_24h"))

    # Determine Confluence values
    confluence_bullish = None
    confluence_bearish = None

    conf_val = overview.get("confluence") or overview.get("confluence_score")
    if isinstance(conf_val, dict):
        confluence_bullish = safe_float(conf_val.get("bullish") or conf_val.get("Bullish"))
        confluence_bearish = safe_float(conf_val.get("bearish") or conf_val.get("Bearish"))
    elif isinstance(conf_val, (int, float, str)):
        # If confluence is a single number, assign it based on price vs EMA20
        c_num = safe_float(conf_val)
        if c_num is not None:
            if price is not None and ema20 is not None:
                if price > ema20:
                    confluence_bullish = c_num
                else:
                    confluence_bearish = c_num
            else:
                confluence_bullish = c_num
                confluence_bearish = c_num

    # Direct override checks
    if overview.get("confluence_bullish") is not None:
        confluence_bullish = safe_float(overview["confluence_bullish"])
    if overview.get("confluence_bearish") is not None:
        confluence_bearish = safe_float(overview["confluence_bearish"])

    # Core Decisions
    action = "WAIT"
    bias = "Neutral"

    # Rule 1: BUY
    # price > EMA20 AND price > EMA50 AND RSI > 55 AND Confluence Bullish > 70
    if (
        price is not None
        and ema20 is not None
        and ema50 is not None
        and rsi is not None
        and price > ema20
        and price > ema50
        and rsi > 55
        and confluence_bullish is not None
        and confluence_bullish > 70
    ):
        action = "BUY"
        bias = "Bullish"

    # Rule 3: SELL
    # price < EMA20 AND price < EMA50 AND RSI < 45 AND Confluence Bearish > 70
    elif (
        price is not None
        and ema20 is not None
        and ema50 is not None
        and rsi is not None
        and price < ema20
        and price < ema50
        and rsi < 45
        and confluence_bearish is not None
        and confluence_bearish > 70
    ):
        action = "SELL"
        bias = "Bearish"

    # Rule 2: WAIT (explicit check that overrides or confirms WAIT state)
    # price between EMA20 and EMA50 OR Market Structure == Range
    # Note: check if price is between EMA20 and EMA50 (inclusive)
    is_between = False
    if price is not None and ema20 is not None and ema50 is not None:
        is_between = min(ema20, ema50) <= price <= max(ema20, ema50)

    is_structure_range = False
    if market_structure is not None:
        is_structure_range = str(market_structure).strip().lower() in ["range", "sideways", "consolidation"]

    if is_between or is_structure_range:
        action = "WAIT"
        bias = "Neutral"

    # Entries, exits, and targets
    aggressive_entry = None
    conservative_entry = None
    stop_loss = None
    take_profit_1 = None
    take_profit_2 = None
    risk_reward = None
    entry_type = "n/a"

    if action == "BUY":
        entry_type = "BUY"
        aggressive_entry = ema20
        if high_24h is not None:
            # 24h High + 0.1% breakout confirmation
            conservative_entry = high_24h * 1.001
        else:
            conservative_entry = price * 1.015 if price is not None else None

        if ema20 is not None:
            stop_loss = ema20 * 0.99
        elif price is not None:
            stop_loss = price * 0.98

        if high_24h is not None and price is not None and high_24h > price:
            take_profit_1 = high_24h
            take_profit_2 = high_24h * 1.025
        elif price is not None:
            take_profit_1 = price * 1.02
            take_profit_2 = price * 1.05

    elif action == "SELL":
        entry_type = "SELL"
        # Aggressive entry is EMA20 rejection
        aggressive_entry = ema20 * 0.999 if ema20 is not None else price
        if low_24h is not None:
            # 24h Low - 0.1% breakdown confirmation
            conservative_entry = low_24h * 0.999
        else:
            conservative_entry = price * 0.985 if price is not None else None

        if ema20 is not None:
            stop_loss = ema20 * 1.01
        elif price is not None:
            stop_loss = price * 1.02

        if low_24h is not None and price is not None and low_24h < price:
            take_profit_1 = low_24h
            take_profit_2 = low_24h * 0.975
        elif price is not None:
            take_profit_1 = price * 0.98
            take_profit_2 = price * 0.95

    # Compute risk reward (rounded to 2 decimals)
    if action in ["BUY", "SELL"] and aggressive_entry is not None and stop_loss is not None and take_profit_1 is not None:
        risk = abs(aggressive_entry - stop_loss)
        reward = abs(take_profit_1 - aggressive_entry)
        if risk > 0:
            risk_reward = round(reward / risk, 2)

    # Confidence Logic
    confidence = 50
    if action == "BUY" and confluence_bullish is not None:
        confidence = int(confluence_bullish)
    elif action == "SELL" and confluence_bearish is not None:
        confidence = int(confluence_bearish)
    elif action == "WAIT":
        # Default or evaluate relative closeness
        confidence = 50
    # Ensure confidence is bounded between 0 and 100
    confidence = max(0, min(100, confidence))

    # Reasons & Rules 4, 5, 6
    reasons = []

    # General Reasons
    if action == "BUY":
        reasons.append("Price is above both EMAs.")
        if rsi is not None and rsi > 55:
            reasons.append("RSI supports continuation.")
        if market_structure and str(market_structure).lower() == "bullish":
            reasons.append("Market structure confirms trend.")
        if confluence_bullish is not None and confluence_bullish > 70:
            reasons.append("Confluence favors buyers.")
    elif action == "SELL":
        reasons.append("Price is below both EMAs.")
        if rsi is not None and rsi < 45:
            reasons.append("RSI supports downward momentum.")
        if market_structure and str(market_structure).lower() == "bearish":
            reasons.append("Market structure confirms trend.")
        if confluence_bearish is not None and confluence_bearish > 70:
            reasons.append("Confluence favors sellers.")
    else:
        reasons.append("Price is consolidating or trend direction is unclear.")
        if is_structure_range:
            reasons.append("Market structure confirms range-bound behavior.")

    # Rule 4: Funding extremely positive AND Price near resistance
    # E.g. funding_rate >= 0.0003, and price is within 1.5% of 24h High
    funding_extremely_positive = funding is not None and funding >= 0.0003
    price_near_resistance = False
    if price is not None and high_24h is not None and high_24h > 0:
        price_near_resistance = (high_24h - price) / high_24h <= 0.015

    if funding_extremely_positive and price_near_resistance:
        reasons.append("Late longs becoming crowded.")

    # Rule 5: Funding negative AND Bullish trend
    # E.g. funding < 0 and price above both EMAs
    funding_negative = funding is not None and funding < 0.0
    bullish_trend = (bias == "Bullish") or (price is not None and ema20 is not None and ema50 is not None and price > ema20 and price > ema50)

    if funding_negative and bullish_trend:
        reasons.append("Potential short squeeze.")

    # Rule 6: Open Interest increases AND Breakout detected
    oi_increases = False
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

    breakout_detected = False
    if "breakout_detected" in overview:
        breakout_detected = bool(overview["breakout_detected"])
    elif price is not None and high_24h is not None:
        breakout_detected = price >= (high_24h * 0.998)

    if oi_increases and breakout_detected:
        reasons.append("Breakout supported by derivatives participation.")

    reason = "\n".join(reasons)

    # Trade Quality Scoring (1 to 5)
    bullish_score = safe_float(overview.get("bullish_score") or confluence_bullish)
    bos_detected = bool(overview.get("break_of_structure") or overview.get("bos") or overview.get("break_of_structure_detected"))

    if (
        bullish_score is not None and bullish_score > 85
        and confidence > 85
        and not is_structure_range
        and bos_detected
    ):
        trade_quality = 5
    else:
        # Logical fallback scoring between 1 and 4
        score = 3
        if confidence > 80:
            score += 1
        if confidence < 50:
            score -= 1

        if action == "BUY" and confluence_bullish is not None and confluence_bullish > 80:
            score += 1
        elif action == "SELL" and confluence_bearish is not None and confluence_bearish > 80:
            score += 1

        if is_structure_range:
            score -= 1

        trade_quality = max(1, min(4, score))

    return TradeDecision(
        market_bias=bias,
        recommended_action=action,
        confidence=confidence,
        trade_quality=trade_quality,
        entry_type=entry_type,
        aggressive_entry=aggressive_entry,
        conservative_entry=conservative_entry,
        stop_loss=stop_loss,
        take_profit_1=take_profit_1,
        take_profit_2=take_profit_2,
        risk_reward=risk_reward,
        reason=reason
    )

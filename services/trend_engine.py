"""Trend Engine service for interpreting market trends.

This module analyzes technical indicators like EMAs, RSI, and market structure
to determine market trend, strength, bias, and a reasoning explanation.
"""

from typing import Any, Dict


def _parse_float(value: Any) -> float:
    """Safely cast a value to float, raising ValueError if not possible."""
    if value is None:
        raise ValueError("Value is None")
    return float(value)


def analyze_trend(market_data: dict) -> dict:
    """Interprets the market trend using existing market data.

    Parameters
    ----------
    market_data : dict
        A dictionary containing market overview data.
        Expected keys:
            - price_usd: float/int/str (Required)
            - ema20: float/int/str (Required)
            - ema50: float/int/str (Required)
            - rsi: float/int/str (Required)
            - market_structure_trend: str (Required)

    Returns
    -------
    dict
        A dictionary containing the following keys:
            - trend: str (e.g., 'Strong Bullish', 'Bullish', 'Recovery',
              'Neutral', 'Sideways', 'Distribution', 'Bearish', 'Strong Bearish')
            - strength: str ('Very Strong', 'Strong', 'Moderate', 'Weak')
            - bias: str ('Bullish', 'Neutral', 'Bearish')
            - reason: str (brief description of the analysis reasoning)
        If any indicators are missing or invalid, returns "Unknown" for indicators
        and a default reason.
    """
    default_unknown = {
        "trend": "Unknown",
        "strength": "Unknown",
        "bias": "Unknown",
        "reason": "Missing or incomplete market indicators for trend analysis."
    }

    if not isinstance(market_data, dict):
        return {
            "trend": "Unknown",
            "strength": "Unknown",
            "bias": "Unknown",
            "reason": "Market data is not a dictionary."
        }

    # Extract required inputs
    price_val = market_data.get("price_usd")
    ema20_val = market_data.get("ema20")
    ema50_val = market_data.get("ema50")
    rsi_val = market_data.get("rsi")
    structure_val = market_data.get("market_structure_trend")

    # Check for missing values
    if (
        price_val is None
        or ema20_val is None
        or ema50_val is None
        or rsi_val is None
        or structure_val is None
    ):
        return default_unknown

    try:
        price = _parse_float(price_val)
        ema20 = _parse_float(ema20_val)
        ema50 = _parse_float(ema50_val)
        rsi = _parse_float(rsi_val)
    except (ValueError, TypeError):
        return {
            "trend": "Unknown",
            "strength": "Unknown",
            "bias": "Unknown",
            "reason": "Invalid numerical values in market indicators."
        }

    struct_str = str(structure_val).strip().lower()

    # Evaluation
    # 1. Strong Bullish: price > EMA20, price > EMA50, RSI > 60, Market Structure = Bullish
    if price > ema20 and price > ema50 and rsi > 60 and struct_str == "bullish":
        return {
            "trend": "Strong Bullish",
            "strength": "Very Strong",
            "bias": "Bullish",
            "reason": "Price is above both EMAs with strong RSI and bullish structure."
        }

    # 2. Bullish (general case where price > both EMAs)
    if price > ema20 and price > ema50:
        strength = "Strong" if rsi >= 50 else "Moderate"
        return {
            "trend": "Bullish",
            "strength": strength,
            "bias": "Bullish",
            "reason": f"Price is above both EMAs showing upward momentum with RSI at {rsi:.1f}."
        }

    # 3. Recovery: price > EMA20, price < EMA50, RSI 50-60
    if price > ema20 and price < ema50 and (50 <= rsi <= 60):
        return {
            "trend": "Recovery",
            "strength": "Moderate",
            "bias": "Bullish",
            "reason": "Price has recovered above EMA20 but remains below EMA50, supported by stable RSI."
        }

    # 4. Neutral: price between EMA20 and EMA50 (either order)
    if (ema20 <= price <= ema50) or (ema50 <= price <= ema20):
        return {
            "trend": "Neutral",
            "strength": "Weak",
            "bias": "Neutral",
            "reason": "Price is consolidating between the EMA20 and EMA50 indicators."
        }

    # 5. Bearish / Strong Bearish
    # Bearish: price below EMA20, price below EMA50, RSI below 45
    if price < ema20 and price < ema50 and rsi < 45:
        if rsi < 35 and struct_str == "bearish":
            return {
                "trend": "Strong Bearish",
                "strength": "Very Strong",
                "bias": "Bearish",
                "reason": "Price is below both EMAs with very weak RSI and bearish structure."
            }
        return {
            "trend": "Bearish",
            "strength": "Strong",
            "bias": "Bearish",
            "reason": "Price is below both EMAs with RSI below 45, indicating bearish momentum."
        }

    # General Bearish (below both EMAs)
    if price < ema20 and price < ema50:
        return {
            "trend": "Bearish",
            "strength": "Moderate",
            "bias": "Bearish",
            "reason": "Price is trading below both EMAs, indicating downward momentum."
        }

    # 6. Distribution: price below EMA20 but above EMA50, RSI < 50
    if price < ema20 and price > ema50 and rsi < 50:
        return {
            "trend": "Distribution",
            "strength": "Moderate",
            "bias": "Bearish",
            "reason": "Price is slipping below EMA20 but remains above EMA50, with bearish indicators."
        }

    # 7. Sideways (flat or range bound)
    if struct_str == "sideways" or (45 <= rsi <= 55):
        return {
            "trend": "Sideways",
            "strength": "Weak",
            "bias": "Neutral",
            "reason": "Market structure or RSI indicates sideways consolidation."
        }

    # 8. Graceful Fallback
    return {
        "trend": "Neutral",
        "strength": "Weak",
        "bias": "Neutral",
        "reason": "Market indicators are mixed and do not show a clear trend."
    }

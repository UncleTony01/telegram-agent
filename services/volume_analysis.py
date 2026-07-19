"""Volume Analysis Engine service for Uncle Tony AI.

This module evaluates whether current market volume confirms or weakens
the current price action by comparing it to historical volume averages.
"""

from typing import Any, Dict, List, Optional


def analyze_volume(
    current_volume: float,
    historical_volumes: List[float],
    price_change_percent: float = 0.0
) -> dict:
    """Evaluates whether current volume confirms or weakens current price action.

    Parameters
    ----------
    current_volume : float
        The volume in the current period.
    historical_volumes : list of float
        Historical volume values.
    price_change_percent : float, optional
        The price change percentage in the current period (default is 0.0).

    Returns
    -------
    dict
        A dictionary containing:
            - current_volume: float
            - average_volume: float
            - volume_ratio: float
            - volume_change_percent: float
            - strength: str ('Very Low', 'Low', 'Normal', 'High', 'Very High')
            - confirmation: str ('Strong Bullish Confirmation', 'Bullish Confirmation',
              'Neutral', 'Weak Breakout', 'Distribution Warning', 'Capitulation')
            - summary: str
    """
    # Safe float conversion helpers
    def safe_float(val: Any) -> float:
        if val is None:
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    curr_vol = safe_float(current_volume)
    price_change = safe_float(price_change_percent)

    # Return defaults if historical_volumes is missing or empty
    if not historical_volumes:
        return {
            "current_volume": curr_vol,
            "average_volume": 0.0,
            "volume_ratio": 0.0,
            "volume_change_percent": 0.0,
            "strength": "Normal",
            "confirmation": "Neutral",
            "summary": "Insufficient volume history to perform average comparison."
        }

    # Extract valid historical volume numbers
    valid_history = []
    for v in historical_volumes:
        try:
            if v is not None:
                valid_history.append(float(v))
        except (ValueError, TypeError):
            continue

    if not valid_history:
        return {
            "current_volume": curr_vol,
            "average_volume": 0.0,
            "volume_ratio": 0.0,
            "volume_change_percent": 0.0,
            "strength": "Normal",
            "confirmation": "Neutral",
            "summary": "No valid numerical values in historical volumes."
        }

    # Slice the last 20 periods
    recent_history = valid_history[-20:]
    avg_vol = sum(recent_history) / len(recent_history)

    # Calculate metrics
    if avg_vol == 0.0:
        ratio = 0.0
        pct_change = 0.0
    else:
        ratio = curr_vol / avg_vol
        pct_change = ((curr_vol - avg_vol) / avg_vol) * 100.0

    # Classify volume strength
    if ratio < 0.60:
        strength = "Very Low"
    elif ratio < 0.85:
        strength = "Low"
    elif ratio < 1.15:
        strength = "Normal"
    elif ratio <= 1.50:
        strength = "High"
    else:
        strength = "Very High"

    # Determine confirmation status
    confirmation = "Neutral"
    if price_change > 0.0:
        if strength in ["High", "Very High"]:
            confirmation = "Strong Bullish Confirmation"
        elif strength == "Normal":
            confirmation = "Bullish Confirmation"
        elif strength in ["Low", "Very Low"]:
            confirmation = "Weak Breakout"
    elif price_change < 0.0:
        if strength == "Very High":
            confirmation = "Capitulation"
        elif strength == "High":
            confirmation = "Distribution Warning"

    # Generate a natural-language summary
    abs_pct = abs(pct_change)
    above_below_phrase = "above the 20-period average" if pct_change >= 0 else "below average"
    summary_base = f"Today's volume is {abs_pct:.0f}% {above_below_phrase}."

    if confirmation == "Strong Bullish Confirmation":
        explanation = " Buyers are participating in the move, increasing confidence in the breakout."
    elif confirmation == "Weak Breakout":
        explanation = " Price is moving, but participation is weak. Breakout reliability is reduced."
    elif confirmation == "Capitulation":
        explanation = " Heavy selling volume indicates potential capitulation and seller exhaustion."
    elif confirmation == "Distribution Warning":
        explanation = " Increased volume on a downward move signals institutional distribution or selling pressure."
    elif confirmation == "Bullish Confirmation":
        explanation = " Price is rising on normal volume, showing steady upward support."
    else:
        # Neutral cases
        if pct_change >= 0:
            explanation = " Volume is slightly elevated or normal, indicating standard market participation."
        else:
            explanation = " Volume is below average, suggesting consolidation or lack of interest from market participants."

    summary = summary_base + explanation

    return {
        "current_volume": curr_vol,
        "average_volume": avg_vol,
        "volume_ratio": ratio,
        "volume_change_percent": pct_change,
        "strength": strength,
        "confirmation": confirmation,
        "summary": summary
    }

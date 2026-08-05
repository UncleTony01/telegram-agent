"""Decision Engine for Uncle Tony Tactical Engine.

This module provides weighted scoring for trading decisions, replacing
static confidence values with a dynamic, multi-factor scoring system.

Categories (each 0-20 points, total 100):
- Trend Score: EMA alignment, price position relative to EMAs
- Momentum Score: RSI, MACD trend and histogram
- Market Structure Score: Trend structure, break of structure
- Derivatives Score: Funding rate, open interest behavior
- Risk Score: Position relative to support/resistance, volatility

Output:
- Total score determines recommendation: STRONG BUY to STRONG SELL
- Each component's contribution is tracked for explainability
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ============================================================================
# Score Result Dataclass
# ============================================================================

@dataclass
class TradeScore:
    """Holds the complete trade scoring breakdown."""
    # Individual scores (each 0-20)
    trend_score: int = 0
    momentum_score: int = 0
    structure_score: int = 0
    derivatives_score: int = 0
    risk_score: int = 0
    
    # Total (0-100)
    total_score: int = 0
    
    # Recommendation derived from score
    recommendation: str = "WAIT"
    
    # Detailed reasoning
    reason: str = ""
    
    # Component details for explainability
    trend_details: List[str] = field(default_factory=list)
    momentum_details: List[str] = field(default_factory=list)
    structure_details: List[str] = field(default_factory=list)
    derivatives_details: List[str] = field(default_factory=list)
    risk_details: List[str] = field(default_factory=list)


# ============================================================================
# Helper Functions
# ============================================================================

def _float(val: Any) -> Optional[float]:
    """Safely convert value to float."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _get_attr(obj: Any, attr: str, default: Any = None) -> Any:
    """Get attribute from object or dict."""
    if hasattr(obj, attr):
        return getattr(obj, attr)
    elif isinstance(obj, dict):
        return obj.get(attr, default)
    return default


# ============================================================================
# Trend Score Calculation (0-20)
# ============================================================================

def calculate_trend_score(data: Any) -> tuple:
    """
    Calculate trend score based on EMA alignment.
    
    Scoring:
    - Price > EMA20: +5
    - Price > EMA50: +10
    - EMA20 > EMA50: +5
    
    Bearish reverses the scoring.
    
    Returns: (score, details_list)
    """
    score = 0
    details = []
    
    # Extract price and EMAs
    if hasattr(data, 'market_data') and hasattr(data, 'indicators'):
        # AnalysisObject format
        price = _float(data.market_data.price)
        ema20 = _float(data.indicators.ema20)
        ema50 = _float(data.indicators.ema50)
    else:
        # Dict format
        price = _float(_get_attr(data, 'price', _get_attr(data, 'price_usd')))
        ema20 = _float(_get_attr(data, 'ema20'))
        ema50 = _float(_get_attr(data, 'ema50'))
    
    # Price > EMA20 (+5)
    if price is not None and ema20 is not None:
        if price > ema20:
            score += 5
            details.append(f"Price above EMA20 (+5)")
        else:
            details.append(f"Price below EMA20")
    
    # Price > EMA50 (+10)
    if price is not None and ema50 is not None:
        if price > ema50:
            score += 10
            details.append(f"Price above EMA50 (+10)")
        else:
            details.append(f"Price below EMA50")
    
    # EMA20 > EMA50 (+5)
    if ema20 is not None and ema50 is not None:
        if ema20 > ema50:
            score += 5
            details.append(f"EMA20 > EMA50 (+5)")
        else:
            details.append(f"EMA20 < EMA50")
    
    # For bearish scenarios, reverse the score
    # If price < EMA20 < EMA50, that's bearish trend = high score for shorts
    if price is not None and ema20 is not None and ema50 is not None:
        if price < ema20 < ema50:
            # Bearish trend - reverse for short bias
            # We keep the score high but mark it as bearish
            pass  # Score stays as-is for now, interpretation handles bias
    
    return score, details


# ============================================================================
# Momentum Score Calculation (0-20)
# ============================================================================

def calculate_momentum_score(data: Any) -> tuple:
    """
    Calculate momentum score based on RSI and MACD.
    
    RSI Scoring:
    - 50-60: +8 (healthy bullish)
    - 60-70: +12 (strong momentum)
    - 45-50: +4 (neutral)
    - below 40: -5 (oversold/weak)
    - above 70: -5 (overbought)
    
    MACD Scoring:
    - Bullish: +8
    - Bearish: -8
    - Positive histogram: +4
    
    Returns: (score, details_list)
    """
    score = 0
    details = []
    
    # Extract RSI and MACD
    if hasattr(data, 'indicators'):
        # AnalysisObject format
        rsi = _float(data.indicators.rsi)
        macd_trend = data.indicators.macd_trend
        macd_histogram = _float(data.indicators.macd_histogram)
    else:
        # Dict format
        rsi = _float(_get_attr(data, 'rsi'))
        macd_trend = _get_attr(data, 'macd_trend', 'Neutral')
        macd_histogram = _float(_get_attr(data, 'macd_histogram'))
    
    # RSI scoring
    if rsi is not None:
        if 60 <= rsi <= 70:
            score += 12
            details.append(f"RSI {rsi:.1f} - Strong momentum (+12)")
        elif 50 <= rsi < 60:
            score += 8
            details.append(f"RSI {rsi:.1f} - Healthy bullish (+8)")
        elif 45 <= rsi < 50:
            score += 4
            details.append(f"RSI {rsi:.1f} - Neutral (+4)")
        elif rsi < 40:
            score -= 5
            details.append(f"RSI {rsi:.1f} - Oversold/weak (-5)")
        elif rsi > 70:
            score -= 5
            details.append(f"RSI {rsi:.1f} - Overbought (-5)")
        else:
            details.append(f"RSI {rsi:.1f}")
    
    # MACD trend scoring
    macd_trend_str = str(macd_trend).lower() if macd_trend else 'neutral'
    if 'bullish' in macd_trend_str:
        score += 8
        details.append(f"MACD Bullish (+8)")
    elif 'bearish' in macd_trend_str:
        score -= 8
        details.append(f"MACD Bearish (-8)")
    else:
        details.append(f"MACD Neutral")
    
    # MACD histogram scoring
    if macd_histogram is not None:
        if macd_histogram > 0:
            score += 4
            details.append(f"MACD Histogram positive (+4)")
        elif macd_histogram < 0:
            details.append(f"MACD Histogram negative")
    
    return score, details


# ============================================================================
# Market Structure Score Calculation (0-20)
# ============================================================================

def calculate_structure_score(data: Any) -> tuple:
    """
    Calculate market structure score.
    
    Scoring:
    - Bullish Trend: +20
    - Range: +10
    - Bearish Trend: 0
    - Break of Structure Bullish: +5
    - Break of Structure Bearish: -5
    
    Returns: (score, details_list)
    """
    score = 0
    details = []
    
    # Extract market structure
    if hasattr(data, 'market_structure'):
        # AnalysisObject format
        trend = data.market_structure.trend
        bos = data.market_structure.break_of_structure
    else:
        # Dict format
        trend = _get_attr(data, 'market_structure', _get_attr(data, 'trend', 'Neutral'))
        bos = _get_attr(data, 'break_of_structure')
    
    # Trend scoring
    trend_str = str(trend).lower() if trend else 'neutral'
    if 'bullish' in trend_str:
        score += 20
        details.append(f"Bullish market structure (+20)")
    elif 'range' in trend_str or 'sideways' in trend_str:
        score += 10
        details.append(f"Range-bound structure (+10)")
    elif 'bearish' in trend_str:
        score += 0
        details.append(f"Bearish market structure (0)")
    else:
        score += 10
        details.append(f"Neutral structure (+10)")
    
    # Break of Structure scoring
    if bos:
        bos_str = str(bos).lower()
        if 'bullish' in bos_str:
            score += 5
            details.append(f"Bullish Break of Structure (+5)")
        elif 'bearish' in bos_str:
            score -= 5
            details.append(f"Bearish Break of Structure (-5)")
    
    return score, details


# ============================================================================
# Derivatives Score Calculation (0-20)
# ============================================================================

def calculate_derivatives_score(data: Any) -> tuple:
    """
    Calculate derivatives score based on funding and open interest.
    
    Funding Rate Scoring:
    - Healthy Positive (0.0001-0.0003): +5
    - Neutral (0.0-0.0001): +4
    - Extreme Positive (>0.0003): -5
    - Extreme Negative (<-0.0001): -5
    
    Open Interest Scoring:
    - Increasing with price: +8
    - Increasing while price falls: -8
    - Stable: +4
    
    Returns: (score, details_list)
    """
    score = 0
    details = []
    
    # Extract derivatives data
    if hasattr(data, 'derivatives'):
        # AnalysisObject format
        funding = _float(data.derivatives.funding_rate)
        oi = _float(data.derivatives.open_interest_usd)
        oi_change = _float(data.derivatives.oi_change_24h)
    else:
        # Dict format
        funding = _float(_get_attr(data, 'funding_rate'))
        oi = _float(_get_attr(data, 'open_interest_usd'))
        oi_change = _float(_get_attr(data, 'oi_change_24h', _get_attr(data, 'oi_change')))
    
    # Also check price for OI divergence
    if hasattr(data, 'market_data'):
        price = _float(data.market_data.price)
        change_24h = _float(data.market_data.change_24h)
    else:
        price = _float(_get_attr(data, 'price', _get_attr(data, 'price_usd')))
        change_24h = _float(_get_attr(data, 'change_24h'))
    
    # Funding rate scoring
    if funding is not None:
        if 0.0001 <= funding <= 0.0003:
            score += 5
            details.append(f"Funding healthy positive (+5)")
        elif 0.0 <= funding < 0.0001:
            score += 4
            details.append(f"Funding neutral (+4)")
        elif funding > 0.0003:
            score -= 5
            details.append(f"Funding extreme positive (-5)")
        elif funding < -0.0001:
            score -= 5
            details.append(f"Funding extreme negative (-5)")
        else:
            score += 4
            details.append(f"Funding normal (+4)")
    
    # Open Interest scoring
    if oi_change is not None:
        if oi_change > 0:
            # OI increasing
            if change_24h is not None and change_24h > 0:
                score += 8
                details.append(f"OI increasing with price (+8)")
            elif change_24h is not None and change_24h < 0:
                score -= 8
                details.append(f"OI increasing while price falls (-8)")
            else:
                score += 4
                details.append(f"OI increasing (+4)")
        else:
            score += 4
            details.append(f"OI stable (+4)")
    elif oi is not None:
        # OI present but no change data
        score += 4
        details.append(f"OI present (+4)")
    
    return score, details


# ============================================================================
# Risk Score Calculation (0-20)
# ============================================================================

def calculate_risk_score(data: Any) -> tuple:
    """
    Calculate risk score based on price position and volatility.
    
    Position Scoring:
    - Price close to resistance: -8
    - Price close to support: +4
    - Inside middle of range: 0
    
    Volatility Scoring:
    - High volatility: -5
    - Normal volatility: 0
    
    Returns: (score, details_list)
    """
    score = 10  # Start at neutral
    details = []
    
    # Extract data
    if hasattr(data, 'market_data') and hasattr(data, 'market_structure'):
        # AnalysisObject format
        price = _float(data.market_data.price)
        high_24h = _float(data.market_data.high_24h)
        low_24h = _float(data.market_data.low_24h)
        support = _float(data.market_structure.nearest_support)
        resistance = _float(data.market_structure.nearest_resistance)
        atr = _float(data.indicators.atr) if hasattr(data, 'indicators') else None
    else:
        # Dict format
        price = _float(_get_attr(data, 'price', _get_attr(data, 'price_usd')))
        high_24h = _float(_get_attr(data, 'high_24h', _get_attr(data, 'high_24h_usd')))
        low_24h = _float(_get_attr(data, 'low_24h', _get_attr(data, 'low_24h_usd')))
        support = _float(_get_attr(data, 'nearest_support', _get_attr(data, 'support')))
        resistance = _float(_get_attr(data, 'nearest_resistance', _get_attr(data, 'resistance')))
        atr = _float(_get_attr(data, 'atr'))
    
    # Calculate distance to support/resistance
    if price is not None:
        # Check proximity to resistance
        if resistance is not None and resistance > 0:
            distance_to_resistance = (resistance - price) / price * 100
            if distance_to_resistance < 2.0:
                score -= 8
                details.append(f"Price near resistance (-8)")
            elif distance_to_resistance < 5.0:
                score -= 3
                details.append(f"Resistance nearby (-3)")
        
        # Check proximity to support
        if support is not None and support > 0:
            distance_to_support = (price - support) / price * 100
            if distance_to_support < 2.0:
                score += 4
                details.append(f"Price near support (+4)")
            elif distance_to_support < 5.0:
                score += 2
                details.append(f"Support nearby (+2)")
        
        # Check position in range
        if high_24h is not None and low_24h is not None and high_24h > low_24h:
            range_width = high_24h - low_24h
            range_position = (price - low_24h) / range_width  # 0-1, 0.5 = middle
            
            if 0.4 <= range_position <= 0.6:
                details.append(f"Price in middle of range")
            elif range_position > 0.8:
                details.append(f"Price near top of range")
            elif range_position < 0.2:
                details.append(f"Price near bottom of range")
    
    # Volatility check via ATR or range
    if atr is not None and price is not None and price > 0:
        atr_pct = (atr / price) * 100
        if atr_pct > 5.0:
            score -= 5
            details.append(f"High volatility (-5)")
        elif atr_pct > 3.0:
            score -= 2
            details.append(f"Elevated volatility (-2)")
    elif high_24h is not None and low_24h is not None and low_24h > 0:
        range_pct = (high_24h - low_24h) / low_24h * 100
        if range_pct > 10.0:
            score -= 5
            details.append(f"High 24h volatility (-5)")
        elif range_pct > 5.0:
            score -= 2
            details.append(f"Elevated 24h volatility (-2)")
    
    # Ensure score stays in bounds
    score = max(0, min(20, score))
    
    if not details:
        details.append(f"Normal risk conditions")
    
    return score, details


# ============================================================================
# Interpret Trade Score
# ============================================================================

def interpret_trade_score(total_score: int) -> str:
    """
    Convert total score to recommendation.
    
    Scoring:
    - 90-100: STRONG BUY
    - 75-89: BUY
    - 60-74: WATCHLIST
    - 40-59: WAIT
    - 20-39: SELL
    - 0-19: STRONG SELL
    """
    if total_score >= 90:
        return "STRONG BUY"
    elif total_score >= 75:
        return "BUY"
    elif total_score >= 60:
        return "WATCHLIST"
    elif total_score >= 40:
        return "WAIT"
    elif total_score >= 20:
        return "SELL"
    else:
        return "STRONG SELL"


def generate_score_reason(score: TradeScore) -> str:
    """Generate human-readable reason for the recommendation."""
    reasons = []
    
    # Trend analysis
    if score.trend_score >= 15:
        reasons.append("Strong trend alignment")
    elif score.trend_score >= 10:
        reasons.append("Price above EMA20 but below EMA50")
    elif score.trend_score < 5:
        reasons.append("Poor EMA alignment")
    
    # Momentum analysis
    if score.momentum_score >= 15:
        reasons.append("Strong momentum")
    elif score.momentum_score >= 8:
        reasons.append("RSI constructive")
    elif score.momentum_score < 5:
        reasons.append("Weak momentum")
    
    # Structure analysis
    if score.structure_score >= 15:
        reasons.append("Bullish market structure")
    elif score.structure_score >= 10:
        reasons.append("Market still range-bound")
    elif score.structure_score < 10:
        reasons.append("Bearish structure")
    
    # Risk analysis
    if score.risk_score >= 15:
        reasons.append("Favorable risk positioning")
    elif score.risk_score < 10:
        reasons.append("Risk elevated near resistance")
    
    return ". ".join(reasons) + "."


# ============================================================================
# Main Entry Point
# ============================================================================

def calculate_trade_decision(data: Any) -> TradeScore:
    """
    Calculate complete trade decision with weighted scoring.
    
    This is the main entry point for the Decision Engine.
    
    Parameters
    ----------
    data : Any
        Market data in one of these formats:
        - AnalysisObject (preferred)
        - Dict with price, ema20, ema50, rsi, macd, etc.
        - Market overview dict from okx_service
    
    Returns
    -------
    TradeScore
        Complete scoring breakdown and recommendation
    """
    # Calculate individual scores
    trend_score, trend_details = calculate_trend_score(data)
    momentum_score, momentum_details = calculate_momentum_score(data)
    structure_score, structure_details = calculate_structure_score(data)
    derivatives_score, derivatives_details = calculate_derivatives_score(data)
    risk_score, risk_details = calculate_risk_score(data)
    
    # Calculate total (0-100)
    total = trend_score + momentum_score + structure_score + derivatives_score + risk_score
    
    # Get recommendation
    recommendation = interpret_trade_score(total)
    
    # Create result
    result = TradeScore(
        trend_score=trend_score,
        momentum_score=momentum_score,
        structure_score=structure_score,
        derivatives_score=derivatives_score,
        risk_score=risk_score,
        total_score=total,
        recommendation=recommendation,
        trend_details=trend_details,
        momentum_details=momentum_details,
        structure_details=structure_details,
        derivatives_details=derivatives_details,
        risk_details=risk_details,
    )
    
    # Generate reason
    result.reason = generate_score_reason(result)
    
    return result


def format_score_breakdown(score: TradeScore) -> str:
    """
    Format the score breakdown for display.
    
    Returns a formatted string showing the scoring breakdown.
    """
    lines = [
        "=" * 40,
        "TRADE DECISION SCORE",
        "=" * 40,
        "",
        f"Trend ............. {score.trend_score:2d}/20",
        f"Momentum .......... {score.momentum_score:2d}/20",
        f"Structure ......... {score.structure_score:2d}/20",
        f"Derivatives ....... {score.derivatives_score:2d}/20",
        f"Risk .............. {score.risk_score:2d}/20",
        "-" * 40,
        f"TOTAL ............. {score.total_score:3d}/100",
        "",
        f"Recommendation: {score.recommendation}",
        "",
        "Reason:",
        f"  {score.reason}",
        "",
    ]
    
    # Add details for each component
    if score.trend_details:
        lines.append("Trend Details:")
        for detail in score.trend_details:
            lines.append(f"  • {detail}")
        lines.append("")
    
    if score.momentum_details:
        lines.append("Momentum Details:")
        for detail in score.momentum_details:
            lines.append(f"  • {detail}")
        lines.append("")
    
    if score.structure_details:
        lines.append("Structure Details:")
        for detail in score.structure_details:
            lines.append(f"  • {detail}")
        lines.append("")
    
    if score.derivatives_details:
        lines.append("Derivatives Details:")
        for detail in score.derivatives_details:
            lines.append(f"  • {detail}")
        lines.append("")
    
    if score.risk_details:
        lines.append("Risk Details:")
        for detail in score.risk_details:
            lines.append(f"  • {detail}")
        lines.append("")
    
    lines.append("=" * 40)
    
    return "\n".join(lines)


# ============================================================================
# Integration Helper
# ============================================================================

def update_decision_with_score(decision_data: Any, score: TradeScore) -> None:
    """
    Update DecisionData with TradeScore values.
    
    This integrates the new scoring into the existing decision pipeline.
    
    Parameters
    ----------
    decision_data : DecisionData or dict
        Decision data to update
    score : TradeScore
        Calculated trade score
    """
    if hasattr(decision_data, 'conviction_score'):
        # DecisionData dataclass
        decision_data.conviction_score = score.total_score
        decision_data.recommended_action = score.recommendation
        decision_data.reasoning = score.reason
    elif isinstance(decision_data, dict):
        # Dict format
        decision_data['conviction_score'] = score.total_score
        decision_data['recommended_action'] = score.recommendation
        decision_data['reasoning'] = score.reason


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    # Test with sample data
    test_data = {
        'price_usd': 45000.0,
        'ema20': 44000.0,
        'ema50': 42000.0,
        'rsi': 58.0,
        'macd_trend': 'Bullish',
        'macd_histogram': 50.0,
        'market_structure': 'Bullish',
        'funding_rate': 0.00015,
        'open_interest_usd': 1000000000,
        'oi_change_24h': 5.0,
        'change_24h': 2.5,
        'high_24h_usd': 45500.0,
        'low_24h_usd': 44000.0,
        'nearest_resistance': 46000.0,
        'nearest_support': 44000.0,
    }
    
    score = calculate_trade_decision(test_data)
    print(format_score_breakdown(score))

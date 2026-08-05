"""Opportunity Scanner for Uncle Tony Tactical Engine.

This module evaluates analyzed assets and assigns Opportunity Scores (0-100)
based on weighted technical and market factors.

The scanner classifies assets into:
- Strong Long Opportunity
- Watchlist Long
- Neutral
- Watchlist Short
- Strong Short Opportunity

Design Principles:
- Reusable service (no Telegram dependencies)
- Modular scoring (easy to add new factors)
- Graceful handling of missing data
- Unit-testable
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


# ============================================================================
# Enums and Constants
# ============================================================================

class OpportunityClassification(str, Enum):
    """Classification categories for trading opportunities."""
    STRONG_LONG = "Strong Long Opportunity"
    WATCHLIST_LONG = "Watchlist Long"
    NEUTRAL = "Neutral"
    WATCHLIST_SHORT = "Watchlist Short"
    STRONG_SHORT = "Strong Short Opportunity"


class Priority(str, Enum):
    """Priority levels for opportunities."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


# Weighting factors (can be adjusted)
DEFAULT_WEIGHTS = {
    'trend_alignment': 0.15,      # EMA relationship, price position
    'market_structure': 0.15,     # Trend structure, BOS
    'ema_relationship': 0.10,     # EMA crossover, alignment
    'rsi_position': 0.10,         # RSI zone
    'macd_bias': 0.10,            # MACD trend
    'funding_quality': 0.05,      # Funding rate health
    'open_interest': 0.05,        # OI behavior
    'probability': 0.10,          # Probability engine output
    'confluence': 0.10,           # Confluence score
    'risk_reward': 0.10,          # R/R estimate
}

# Classification thresholds
CLASSIFICATION_THRESHOLDS = {
    OpportunityClassification.STRONG_LONG: 80,
    OpportunityClassification.WATCHLIST_LONG: 65,
    OpportunityClassification.NEUTRAL: 40,
    OpportunityClassification.WATCHLIST_SHORT: 25,
    OpportunityClassification.STRONG_SHORT: 0,
}


# ============================================================================
# Opportunity Result Dataclass
# ============================================================================

@dataclass
class OpportunityResult:
    """Holds the complete opportunity analysis for an asset."""
    symbol: str
    score: int  # 0-100
    classification: str
    priority: str
    confidence: int  # 0-100
    reasons: List[str] = field(default_factory=list)
    
    # Detailed breakdown
    trend_score: int = 0
    structure_score: int = 0
    momentum_score: int = 0
    derivatives_score: int = 0
    probability_score: int = 0
    confluence_score: int = 0
    risk_reward_score: int = 0
    
    # Raw factor scores (for debugging)
    factor_scores: Dict[str, float] = field(default_factory=dict)
    
    # Trading parameters (optional)
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None


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


def _get_nested(obj: Any, *attrs, default=None) -> Any:
    """Get nested attribute from object or dict."""
    current = obj
    for attr in attrs:
        if current is None:
            return default
        current = _get_attr(current, attr, default)
    return current if current is not None else default


# ============================================================================
# Factor Scoring Functions
# ============================================================================

def score_trend_alignment(data: Any) -> tuple:
    """
    Score trend alignment (0-100).
    
    Factors:
    - Price position relative to EMA20/EMA50
    - Trend direction
    
    Returns: (score, reason_list)
    """
    reasons = []
    score = 50  # Start neutral
    
    # Extract price and EMAs
    price = _float(_get_nested(data, 'market_data', 'price', default=_get_attr(data, 'price_usd')))
    ema20 = _float(_get_nested(data, 'indicators', 'ema20', default=_get_attr(data, 'ema20')))
    ema50 = _float(_get_nested(data, 'indicators', 'ema50', default=_get_attr(data, 'ema50')))
    trend = _get_nested(data, 'indicators', 'trend', default=_get_attr(data, 'trend', 'Neutral'))
    
    if price is None:
        return 50, ["Price data unavailable"]
    
    # Price above EMA20
    if ema20 is not None:
        if price > ema20:
            score += 15
            reasons.append("Above EMA20")
        else:
            score -= 15
            reasons.append("Below EMA20")
    
    # Price above EMA50
    if ema50 is not None:
        if price > ema50:
            score += 20
            reasons.append("Above EMA50")
        else:
            score -= 20
            reasons.append("Below EMA50")
    
    # EMA alignment
    if ema20 is not None and ema50 is not None:
        if ema20 > ema50:
            score += 15
            reasons.append("Bullish EMA alignment")
        else:
            score -= 15
            reasons.append("Bearish EMA alignment")
    
    # Trend strength
    trend_str = str(trend).lower() if trend else 'neutral'
    if 'strong' in trend_str and 'bullish' in trend_str:
        score += 20
        reasons.append("Strong bullish trend")
    elif 'bullish' in trend_str:
        score += 10
        reasons.append("Bullish trend")
    elif 'strong' in trend_str and 'bearish' in trend_str:
        score -= 20
        reasons.append("Strong bearish trend")
    elif 'bearish' in trend_str:
        score -= 10
        reasons.append("Bearish trend")
    
    # Reconcile potentially contradictory EMA reasons for clearer human-readable output
    # e.g., avoid showing both "Below EMA20" and "Bullish EMA alignment" which can be confusing.
    try:
        if "Below EMA20" in reasons and "Bullish EMA alignment" in reasons:
            # Remove the two separate reasons and replace with a combined, consistent message
            reasons = [r for r in reasons if r not in ("Below EMA20", "Bullish EMA alignment")]
            reasons.append("Bullish EMA alignment but price below EMA20 (weakness)")
        if "Above EMA20" in reasons and "Bearish EMA alignment" in reasons:
            reasons = [r for r in reasons if r not in ("Above EMA20", "Bearish EMA alignment")]
            reasons.append("Bearish EMA alignment but price above EMA20 (weakness)")
    except Exception:
        # Keep original reasons if reconciliation fails for any reason
        pass
    
    return max(0, min(100, score)), reasons


def score_market_structure(data: Any) -> tuple:
    """
    Score market structure (0-100).
    
    Factors:
    - Market structure trend
    - Break of Structure
    
    Returns: (score, reason_list)
    """
    reasons = []
    score = 50
    
    # Extract structure
    structure = _get_nested(data, 'market_structure', 'trend', default=_get_attr(data, 'market_structure'))
    bos = _get_nested(data, 'market_structure', 'break_of_structure', default=_get_attr(data, 'break_of_structure'))
    market_state = _get_nested(data, 'market_structure', 'market_state', default=_get_attr(data, 'market_state'))
    
    # Structure trend
    structure_str = str(structure).lower() if structure else ''
    if 'bullish' in structure_str:
        score += 30
        reasons.append("Bullish structure")
    elif 'bearish' in structure_str:
        score -= 30
        reasons.append("Bearish structure")
    elif 'range' in structure_str or 'sideways' in structure_str:
        reasons.append("Range-bound")
    
    # Market state (from Market Intelligence)
    if market_state:
        state_str = str(market_state).lower()
        if 'strong uptrend' in state_str or 'healthy uptrend' in state_str:
            score += 20
            reasons.append("Market structure improving")
        elif 'strong downtrend' in state_str or 'weak downtrend' in state_str:
            score -= 20
            reasons.append("Market structure deteriorating")
        elif 'accumulation' in state_str:
            score += 10
            reasons.append("Accumulation phase")
        elif 'distribution' in state_str:
            score -= 10
            reasons.append("Distribution phase")
    
    # Break of Structure
    if bos:
        bos_str = str(bos).lower()
        if 'bullish' in bos_str:
            score += 15
            reasons.append("Bullish BOS")
        elif 'bearish' in bos_str:
            score -= 15
            reasons.append("Bearish BOS")
    
    return max(0, min(100, score)), reasons


def score_ema_relationship(data: Any) -> tuple:
    """
    Score EMA relationship (0-100).
    
    Factors:
    - EMA crossover
    - Distance between EMAs
    
    Returns: (score, reason_list)
    """
    reasons = []
    score = 50
    
    ema20 = _float(_get_nested(data, 'indicators', 'ema20', default=_get_attr(data, 'ema20')))
    ema50 = _float(_get_nested(data, 'indicators', 'ema50', default=_get_attr(data, 'ema50')))
    
    if ema20 is None or ema50 is None:
        return 50, ["EMA data unavailable"]
    
    # EMA crossover
    if ema20 > ema50:
        score += 30
        # Check gap for trend strength
        gap_pct = abs(ema20 - ema50) / ema50 * 100
        if gap_pct > 2.0:
            score += 20
            reasons.append("Wide bullish EMA gap")
        else:
            reasons.append("Bullish EMA crossover")
    elif ema20 < ema50:
        score -= 30
        gap_pct = abs(ema20 - ema50) / ema50 * 100
        if gap_pct > 2.0:
            score -= 20
            reasons.append("Wide bearish EMA gap")
        else:
            reasons.append("Bearish EMA crossover")
    else:
        reasons.append("EMAs converging")
    
    return max(0, min(100, score)), reasons


def score_rsi_position(data: Any) -> tuple:
    """
    Score RSI position (0-100).
    
    Zones:
    - 50-60: Healthy bullish
    - 60-70: Strong momentum
    - 70+: Overbought
    - 40-50: Neutral
    - 30-40: Weak
    - <30: Oversold
    
    Returns: (score, reason_list)
    """
    reasons = []
    score = 50
    
    rsi = _float(_get_nested(data, 'indicators', 'rsi', default=_get_attr(data, 'rsi')))
    
    if rsi is None:
        return 50, ["RSI data unavailable"]
    
    if 60 <= rsi <= 70:
        score += 35
        reasons.append(f"RSI strong momentum ({rsi:.1f})")
    elif 50 <= rsi < 60:
        score += 20
        reasons.append(f"RSI healthy bullish ({rsi:.1f})")
    elif 40 <= rsi < 50:
        score += 5
        reasons.append(f"RSI neutral ({rsi:.1f})")
    elif 30 <= rsi < 40:
        score -= 10
        reasons.append(f"RSI weak ({rsi:.1f})")
    elif rsi < 30:
        score -= 5  # Oversold can be reversal opportunity
        reasons.append(f"RSI oversold ({rsi:.1f})")
    elif rsi > 70:
        score -= 10  # Overbought warning
        reasons.append(f"RSI overbought ({rsi:.1f})")
    else:
        reasons.append(f"RSI {rsi:.1f}")
    
    return max(0, min(100, score)), reasons


def score_macd_bias(data: Any) -> tuple:
    """
    Score MACD bias (0-100).
    
    Factors:
    - MACD trend
    - Histogram direction
    
    Returns: (score, reason_list)
    """
    reasons = []
    score = 50
    
    macd_trend = _get_nested(data, 'indicators', 'macd_trend', default=_get_attr(data, 'macd_trend'))
    macd_histogram = _float(_get_nested(data, 'indicators', 'macd_histogram', default=_get_attr(data, 'macd_histogram')))
    
    # MACD trend
    trend_str = str(macd_trend).lower() if macd_trend else 'neutral'
    if 'bullish' in trend_str:
        score += 30
        reasons.append("MACD Bullish")
    elif 'bearish' in trend_str:
        score -= 30
        reasons.append("MACD Bearish")
    else:
        reasons.append("MACD Neutral")
    
    # Histogram
    if macd_histogram is not None:
        if macd_histogram > 0:
            score += 20
            reasons.append("Positive histogram")
        elif macd_histogram < 0:
            score -= 20
            reasons.append("Negative histogram")
    
    return max(0, min(100, score)), reasons


def score_funding_quality(data: Any) -> tuple:
    """
    Score funding rate quality (0-100).
    
    Categories:
    - Negative: Bullish (squeeze potential)
    - 0-0.01%: Neutral/healthy
    - 0.01-0.03%: Elevated
    - >0.03%: Extreme (crowded)
    
    Returns: (score, reason_list)
    """
    reasons = []
    score = 50
    
    funding = _float(_get_nested(data, 'derivatives', 'funding_rate', default=_get_attr(data, 'funding_rate')))
    
    if funding is None:
        return 50, ["Funding data unavailable"]
    
    funding_pct = funding * 100  # Convert to percentage
    
    if funding < 0:
        score += 30
        reasons.append("Negative funding (squeeze potential)")
    elif funding < 0.0001:
        score += 20
        reasons.append("Funding neutral")
    elif funding < 0.0003:
        score += 10
        reasons.append("Funding slightly elevated")
    else:
        score -= 20
        reasons.append("Funding extreme (crowded)")
    
    return max(0, min(100, score)), reasons


def score_open_interest(data: Any) -> tuple:
    """
    Score open interest behavior (0-100).
    
    Factors:
    - OI increasing with price = bullish
    - OI decreasing with price = bearish
    - OI diverging from price = warning
    
    Returns: (score, reason_list)
    """
    reasons = []
    score = 50
    
    oi_change = _float(_get_nested(data, 'derivatives', 'oi_change_24h', default=_get_attr(data, 'oi_change_24h', default=_get_attr(data, 'oi_change'))))
    price_change = _float(_get_nested(data, 'market_data', 'change_24h', default=_get_attr(data, 'change_24h')))
    
    if oi_change is None:
        return 50, ["OI data unavailable"]
    
    # OI increasing
    if oi_change > 0:
        if price_change is not None and price_change > 0:
            score += 30
            reasons.append("OI rising with price")
        elif price_change is not None and price_change < 0:
            score -= 20
            reasons.append("OI rising on decline (short buildup)")
        else:
            score += 15
            reasons.append("OI increasing")
    elif oi_change < 0:
        if price_change is not None and price_change < 0:
            score -= 20
            reasons.append("OI falling with price (long unwind)")
        else:
            score -= 10
            reasons.append("OI decreasing")
    else:
        reasons.append("OI stable")
    
    return max(0, min(100, score)), reasons


def score_probability_engine(data: Any) -> tuple:
    """
    Score probability engine output (0-100).
    
    Factors:
    - Bullish probability
    - Bearish probability
    - Most likely scenario
    
    Returns: (score, reason_list)
    """
    reasons = []
    score = 50
    
    # Get probability data
    prob = _get_attr(data, 'probability')
    
    # Fallbacks: some pipeline runs store probability-like outputs in confluence or decision
    if prob is None:
        conf = _get_attr(data, 'confluence')
        dec = _get_attr(data, 'decision')
        if conf is not None:
            # Build a best-effort probability dict from confluence/decision outputs
            bullish = _get_attr(conf, 'bullish_score', _get_attr(conf, 'bullish', None))
            bearish = _get_attr(conf, 'bearish_score', _get_attr(conf, 'bearish', None))
            neutral = _get_attr(conf, 'neutral_score', _get_attr(conf, 'neutral', None))
            most = None
            # If decision exposes most_likely_scenario, use it
            if dec is not None:
                most = _get_attr(dec, 'most_likely_scenario', None)
            # Derive most likely if not explicitly present
            try:
                b = float(bullish) if bullish is not None else 0
                br = float(bearish) if bearish is not None else 0
                n = float(neutral) if neutral is not None else 0
                if b >= br and b >= n:
                    most = most or 'Bullish'
                elif br >= b and br >= n:
                    most = most or 'Bearish'
                else:
                    most = most or 'Sideways'
            except Exception:
                most = most or 'Sideways'
            prob = {
                'bullish_probability': bullish if bullish is not None else 33,
                'bearish_probability': bearish if bearish is not None else 33,
                'sideways_probability': neutral if neutral is not None else 34,
                'most_likely': most,
            }
    
    if prob is None:
        return 50, ["Probability data unavailable"]
    
    bullish_prob = _get_attr(prob, 'bullish_probability', 33)
    bearish_prob = _get_attr(prob, 'bearish_probability', 33)
    sideways_prob = _get_attr(prob, 'sideways_probability', 34)
    most_likely = _get_attr(prob, 'most_likely', 'Sideways')
    
    # Score based on most likely scenario
    most_likely_str = str(most_likely).lower()
    
    if 'bullish' in most_likely_str:
        score = bullish_prob
        reasons.append(f"Bullish scenario {bullish_prob}%")
    elif 'bearish' in most_likely_str:
        score = 100 - bearish_prob  # Invert for short opportunity
        reasons.append(f"Bearish scenario {bearish_prob}%")
    else:
        score = 50
        reasons.append(f"Sideways scenario {sideways_prob}%")
    
    return max(0, min(100, score)), reasons


def score_confluence(data: Any) -> tuple:
    """
    Score confluence (0-100).
    
    Factors:
    - Bullish vs bearish score
    - Confidence level
    
    Returns: (score, reason_list)
    """
    reasons = []
    score = 50
    
    # Get confluence data
    conf = _get_attr(data, 'confluence')
    
    if conf is None:
        return 50, ["Confluence data unavailable"]
    
    bullish_score = _get_attr(conf, 'bullish_score', _get_attr(conf, 'bullish', 0))
    bearish_score = _get_attr(conf, 'bearish_score', _get_attr(conf, 'bearish', 0))
    confidence = _get_attr(conf, 'confidence', 50)
    
    # Calculate net bias
    if isinstance(bullish_score, (int, float)) and isinstance(bearish_score, (int, float)):
        net = bullish_score - bearish_score
        if net > 20:
            score = 70 + int(confidence * 0.3)
            reasons.append(f"Strong bullish confluence")
        elif net > 0:
            score = 55 + int(confidence * 0.3)
            reasons.append(f"Bullish confluence")
        elif net < -20:
            score = 30 - int(confidence * 0.3)
            reasons.append(f"Strong bearish confluence")
        elif net < 0:
            score = 45 - int(confidence * 0.3)
            reasons.append(f"Bearish confluence")
        else:
            score = 50
            reasons.append(f"Neutral confluence")
    else:
        score = confidence
        reasons.append(f"Confluence: {confidence}")
    
    return max(0, min(100, score)), reasons


def score_risk_reward(data: Any) -> tuple:
    """
    Score risk/reward estimate (0-100).
    
    Factors:
    - R/R ratio
    - Position relative to support/resistance
    
    Returns: (score, reason_list)
    """
    reasons = []
    score = 50
    
    # Get R/R from decision
    rr = _float(_get_nested(data, 'decision', 'risk_reward_ratio', default=_get_attr(data, 'risk_reward')))
    
    # Get position relative to S/R
    price = _float(_get_nested(data, 'market_data', 'price', default=_get_attr(data, 'price_usd')))
    support = _float(_get_nested(data, 'market_structure', 'nearest_support', default=_get_attr(data, 'nearest_support', default=_get_attr(data, 'support'))))
    resistance = _float(_get_nested(data, 'market_structure', 'nearest_resistance', default=_get_attr(data, 'nearest_resistance', default=_get_attr(data, 'resistance'))))
    
    # Risk/reward scoring
    if rr is not None:
        if rr >= 3.0:
            score += 40
            reasons.append(f"Excellent R/R ({rr:.1f}:1)")
        elif rr >= 2.0:
            score += 25
            reasons.append(f"Good R/R ({rr:.1f}:1)")
        elif rr >= 1.5:
            score += 10
            reasons.append(f"Moderate R/R ({rr:.1f}:1)")
        elif rr < 1.0:
            score -= 20
            reasons.append(f"Poor R/R ({rr:.1f}:1)")
        else:
            reasons.append(f"R/R {rr:.1f}:1")
    
    # Position scoring
    if price is not None:
        if support is not None and resistance is not None:
            range_width = resistance - support
            if range_width > 0:
                position = (price - support) / range_width
                if position < 0.3:
                    score += 15
                    reasons.append("Near support (good for long)")
                elif position > 0.7:
                    score -= 15
                    reasons.append("Near resistance (good for short)")
    
    return max(0, min(100, score)), reasons


# ============================================================================
# Main Scoring Function
# ============================================================================

def calculate_opportunity_score(data: Any, weights: Dict[str, float] = None) -> OpportunityResult:
    """
    Calculate complete opportunity score for an asset.
    
    This is the main entry point for the Opportunity Scanner.
    
    Parameters
    ----------
    data : Any
        Market data in one of these formats:
        - AnalysisObject (preferred)
        - Dict with market overview
        - Decision output from Tactical Engine
    weights : Dict[str, float], optional
        Custom weighting factors. Uses DEFAULT_WEIGHTS if not provided.
    
    Returns
    -------
    OpportunityResult
        Complete opportunity analysis with score, classification, and reasons
    """
    # Use default weights if not provided
    if weights is None:
        weights = DEFAULT_WEIGHTS
    
    # Extract symbol (prefer explicit market_data.symbol when available and non-empty)
    symbol = _get_attr(data, 'symbol', 'UNKNOWN')
    if hasattr(data, 'market_data'):
        md_sym = _get_attr(data.market_data, 'symbol', None)
        if md_sym:
            symbol = md_sym
    
    # Calculate all factor scores
    factor_results = {}
    
    factor_results['trend_alignment'] = score_trend_alignment(data)
    factor_results['market_structure'] = score_market_structure(data)
    factor_results['ema_relationship'] = score_ema_relationship(data)
    factor_results['rsi_position'] = score_rsi_position(data)
    factor_results['macd_bias'] = score_macd_bias(data)
    factor_results['funding_quality'] = score_funding_quality(data)
    factor_results['open_interest'] = score_open_interest(data)
    factor_results['probability'] = score_probability_engine(data)
    factor_results['confluence'] = score_confluence(data)
    factor_results['risk_reward'] = score_risk_reward(data)
    
    # Calculate weighted total
    total_score = 0
    factor_scores = {}
    all_reasons = []
    
    for factor_name, (score, reasons) in factor_results.items():
        weight = weights.get(factor_name, 0.1)
        weighted_score = score * weight
        total_score += weighted_score
        factor_scores[factor_name] = score
        all_reasons.extend(reasons)
    
    total_score = int(round(total_score))
    
    # Calculate component scores for breakdown
    trend_score = int((factor_scores.get('trend_alignment', 50) + factor_scores.get('ema_relationship', 50)) / 2)
    structure_score = int(factor_scores.get('market_structure', 50))
    momentum_score = int((factor_scores.get('rsi_position', 50) + factor_scores.get('macd_bias', 50)) / 2)
    derivatives_score = int((factor_scores.get('funding_quality', 50) + factor_scores.get('open_interest', 50)) / 2)
    probability_score = int(factor_scores.get('probability', 50))
    confluence_score = int(factor_scores.get('confluence', 50))
    rr_score = int(factor_scores.get('risk_reward', 50))
    
    # Calculate confidence (how reliable is the score)
    confidence = calculate_confidence(data, factor_scores)
    
    # Classify
    classification, priority = classify_opportunity(total_score, factor_scores)
    
    # Get trading parameters if available
    entry_price = _float(_get_nested(data, 'decision', 'aggressive_entry', default=_get_attr(data, 'aggressive_entry')))
    stop_loss = _float(_get_nested(data, 'decision', 'stop_loss', default=_get_attr(data, 'stop_loss')))
    take_profit = _float(_get_nested(data, 'decision', 'take_profit_1', default=_get_attr(data, 'take_profit_1')))
    risk_reward = _float(_get_nested(data, 'decision', 'risk_reward_ratio', default=_get_attr(data, 'risk_reward')))
    
    return OpportunityResult(
        symbol=symbol,
        score=total_score,
        classification=classification,
        priority=priority,
        confidence=confidence,
        reasons=all_reasons,
        trend_score=trend_score,
        structure_score=structure_score,
        momentum_score=momentum_score,
        derivatives_score=derivatives_score,
        probability_score=probability_score,
        confluence_score=confluence_score,
        risk_reward_score=rr_score,
        factor_scores=factor_scores,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk_reward_ratio=risk_reward,
    )


def calculate_confidence(data: Any, factor_scores: Dict[str, float]) -> int:
    """
    Calculate confidence level based on data availability and agreement.
    
    Higher confidence when:
    - More data available
    - Factors agree with each other
    """
    confidence = 50
    
    # Count available data
    available_factors = len([s for s in factor_scores.values() if s != 50])
    confidence += available_factors * 3  # +3 per factor with data
    
    # Check factor agreement
    scores = list(factor_scores.values())
    if scores:
        avg = sum(scores) / len(scores)
        variance = sum((s - avg) ** 2 for s in scores) / len(scores)
        
        # Low variance = high agreement = higher confidence
        if variance < 100:
            confidence += 20
        elif variance < 400:
            confidence += 10
        elif variance > 1000:
            confidence -= 20
    
    return max(0, min(100, confidence))


def classify_opportunity(total_score: int, factor_scores: Dict[str, float]) -> tuple:
    """
    Classify opportunity based on total score and factor agreement.
    
    Returns: (classification, priority)
    """
    # Determine base classification from score
    if total_score >= CLASSIFICATION_THRESHOLDS[OpportunityClassification.STRONG_LONG]:
        base_class = OpportunityClassification.STRONG_LONG
    elif total_score >= CLASSIFICATION_THRESHOLDS[OpportunityClassification.WATCHLIST_LONG]:
        base_class = OpportunityClassification.WATCHLIST_LONG
    elif total_score >= CLASSIFICATION_THRESHOLDS[OpportunityClassification.NEUTRAL]:
        base_class = OpportunityClassification.NEUTRAL
    elif total_score >= CLASSIFICATION_THRESHOLDS[OpportunityClassification.WATCHLIST_SHORT]:
        base_class = OpportunityClassification.WATCHLIST_SHORT
    else:
        base_class = OpportunityClassification.STRONG_SHORT
    
    # Determine priority based on score magnitude
    if total_score >= 80 or total_score <= 20:
        priority = Priority.HIGH
    elif total_score >= 65 or total_score <= 35:
        priority = Priority.MEDIUM
    else:
        priority = Priority.LOW
    
    return base_class.value, priority.value


# ============================================================================
# Formatting Functions
# ============================================================================

def format_opportunity_report(result: OpportunityResult) -> str:
    """
    Format opportunity result for display.
    
    Returns a formatted string suitable for terminal output or logging.
    """
    lines = [
        "=" * 50,
        f"OPPORTUNITY SCAN: {result.symbol}",
        "=" * 50,
        "",
        f"Score:           {result.score}/100",
        f"Classification:  {result.classification}",
        f"Priority:        {result.priority}",
        f"Confidence:      {result.confidence}%",
        "",
        "Component Scores:",
        f"  Trend:         {result.trend_score}/100",
        f"  Structure:     {result.structure_score}/100",
        f"  Momentum:      {result.momentum_score}/100",
        f"  Derivatives:   {result.derivatives_score}/100",
        f"  Probability:   {result.probability_score}/100",
        f"  Confluence:    {result.confluence_score}/100",
        f"  Risk/Reward:   {result.risk_reward_score}/100",
        "",
        "Reasons:",
    ]
    
    for reason in result.reasons[:10]:  # Limit to 10 reasons
        lines.append(f"  • {reason}")
    
    if result.entry_price or result.stop_loss or result.take_profit:
        lines.extend([
            "",
            "Trading Parameters:",
        ])
        if result.entry_price:
            lines.append(f"  Entry:         ${result.entry_price:,.2f}")
        if result.stop_loss:
            lines.append(f"  Stop Loss:     ${result.stop_loss:,.2f}")
        if result.take_profit:
            lines.append(f"  Take Profit:   ${result.take_profit:,.2f}")
        if result.risk_reward_ratio:
            lines.append(f"  R/R Ratio:     {result.risk_reward_ratio:.2f}:1")
    
    lines.extend([
        "",
        "=" * 50,
    ])
    
    return "\n".join(lines)


# ============================================================================
# Batch Scanner
# ============================================================================

def scan_multiple_assets(assets_data: List[Any], weights: Dict[str, float] = None) -> List[OpportunityResult]:
    """
    Scan multiple assets and return sorted results.
    
    Results are sorted by score (highest first).
    
    Parameters
    ----------
    assets_data : List[Any]
        List of market data for each asset
    weights : Dict[str, float], optional
        Custom weighting factors
    
    Returns
    -------
    List[OpportunityResult]
        Sorted list of opportunity results
    """
    results = []
    
    for data in assets_data:
        try:
            result = calculate_opportunity_score(data, weights)
            results.append(result)
        except Exception as e:
            # Log error but continue with other assets
            symbol = _get_attr(data, 'symbol', 'UNKNOWN')
            print(f"Error scanning {symbol}: {e}")
    
    # Sort by score (highest first)
    results.sort(key=lambda x: x.score, reverse=True)
    
    return results


def filter_opportunities(
    results: List[OpportunityResult],
    min_score: int = 0,
    max_score: int = 100,
    classifications: List[str] = None,
    min_confidence: int = 0,
) -> List[OpportunityResult]:
    """
    Filter opportunity results by criteria.
    
    Parameters
    ----------
    results : List[OpportunityResult]
        List of results to filter
    min_score : int
        Minimum score threshold
    max_score : int
        Maximum score threshold
    classifications : List[str], optional
        List of classifications to include
    min_confidence : int
        Minimum confidence threshold
    
    Returns
    -------
    List[OpportunityResult]
        Filtered results
    """
    filtered = results
    
    if min_score > 0:
        filtered = [r for r in filtered if r.score >= min_score]
    
    if max_score < 100:
        filtered = [r for r in filtered if r.score <= max_score]
    
    if classifications:
        filtered = [r for r in filtered if r.classification in classifications]
    
    if min_confidence > 0:
        filtered = [r for r in filtered if r.confidence >= min_confidence]
    
    return filtered


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    # Test with sample data (bullish setup)
    test_data_bullish = {
        'symbol': 'BTC',
        'price_usd': 45000.0,
        'ema20': 44000.0,
        'ema50': 42000.0,
        'rsi': 58.0,
        'macd_trend': 'Bullish',
        'macd_histogram': 50.0,
        'market_structure': 'Bullish',
        'market_state': 'Healthy Uptrend',
        'funding_rate': 0.00015,
        'open_interest_usd': 1000000000,
        'oi_change_24h': 5.0,
        'change_24h': 2.5,
        'high_24h_usd': 45500.0,
        'low_24h_usd': 44000.0,
        'nearest_resistance': 46000.0,
        'nearest_support': 44000.0,
        'risk_reward': 2.5,
    }
    
    # Test with sample data (bearish setup)
    test_data_bearish = {
        'symbol': 'ETH',
        'price_usd': 2500.0,
        'ema20': 2600.0,
        'ema50': 2700.0,
        'rsi': 35.0,
        'macd_trend': 'Bearish',
        'macd_histogram': -80.0,
        'market_structure': 'Bearish',
        'market_state': 'Weak Downtrend',
        'funding_rate': -0.0001,
        'open_interest_usd': 500000000,
        'oi_change_24h': -3.0,
        'change_24h': -4.5,
        'high_24h_usd': 2650.0,
        'low_24h_usd': 2480.0,
        'nearest_resistance': 2650.0,
        'nearest_support': 2400.0,
        'risk_reward': 0.8,
    }
    
    print("Testing Bullish Setup:")
    print("-" * 50)
    result_bullish = calculate_opportunity_score(test_data_bullish)
    print(format_opportunity_report(result_bullish))
    
    print("\n\nTesting Bearish Setup:")
    print("-" * 50)
    result_bearish = calculate_opportunity_score(test_data_bearish)
    print(format_opportunity_report(result_bearish))
    
    print("\n\nTesting Batch Scanner:")
    print("-" * 50)
    results = scan_multiple_assets([test_data_bullish, test_data_bearish])
    for r in results:
        print(f"{r.symbol}: {r.score}/100 - {r.classification}")

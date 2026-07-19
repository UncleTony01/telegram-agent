"""Uncle Tony Explainable Decision Engine (XDE) - Phase 8.

This module transforms numerical outputs into transparent, professional trading
reasoning. It enhances the Local Narrator by providing:

1. Confidence Breakdown - Shows WHY confidence is what it is
2. Opportunity Explanation - Detailed opportunity score analysis
3. Market Summary - Professional paragraph combining all data
4. Recommendation Explanation - Explicit reasons for every decision
5. Probability Engine - Detailed scenario analysis with triggers
6. Educational Insight - Teaching users the trading logic

IMPORTANT: This module does NOT change any trading logic. It only improves
the explanation quality of existing calculations.
"""

from typing import Dict, List, Optional, Any
from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# XDE Report Extensions
# ============================================================================

def build_explainable_report(report, analysis) -> Dict[str, Any]:
    """Build explainable additions to the TacticalReport.
    
    This function adds detailed explanations to the report without
    modifying any trading logic.
    
    Parameters
    ----------
    report : TacticalReport
        The structured report from Tactical Engine
    analysis : AnalysisObject or dict
        The original analysis data
    
    Returns
    -------
    dict
        Explainable extensions to add to the report
    """
    explainable = {}
    
    # 1. Confidence Breakdown
    explainable['confidence_breakdown'] = build_confidence_breakdown(report, analysis)
    
    # 2. Opportunity Explanation
    explainable['opportunity_explanation'] = build_opportunity_explanation(report, analysis)
    
    # 3. Market Summary
    explainable['market_summary'] = build_market_summary(report, analysis)
    
    # 4. Recommendation Explanation
    explainable['recommendation_explanation'] = build_recommendation_explanation(report, analysis)
    
    # 5. Probability Analysis
    explainable['probability_analysis'] = build_probability_analysis(report, analysis)
    
    # 6. Educational Insight
    explainable['educational_insight'] = build_educational_insight(report, analysis)
    
    return explainable


# ============================================================================
# 1. Confidence Breakdown
# ============================================================================

def build_confidence_breakdown(report, analysis) -> Dict[str, Any]:
    """Build detailed confidence breakdown showing positive and negative contributors.
    
    Parameters
    ----------
    report : TacticalReport
        Structured report
    analysis : AnalysisObject or dict
        Original analysis data
    
    Returns
    -------
    dict
        {
            'positive': List of positive factors,
            'negative': List of negative factors,
            'total': Final confidence score,
            'raw_score': Raw score before adjustments
        }
    """
    positive = []
    negative = []
    raw_score = 50  # Start at neutral
    
    # Extract data from analysis
    price = _get_value(analysis, 'price_usd', 'price')
    ema20 = _get_value(analysis, 'ema20')
    ema50 = _get_value(analysis, 'ema50')
    rsi = _get_value(analysis, 'rsi')
    trend = _get_value(analysis, 'trend', default='Neutral')
    market_structure = _get_value(analysis, 'market_structure', default='')
    macd_trend = _get_value(analysis, 'macd_trend', default='Neutral')
    funding = _get_value(analysis, 'funding_rate')
    
    # EMA20 position
    if price and ema20:
        if price > ema20:
            positive.append("Price above EMA20 (+10)")
            raw_score += 10
        else:
            negative.append("Price below EMA20 (-10)")
            raw_score -= 10
    
    # EMA50 position
    if price and ema50:
        if price > ema50:
            positive.append("Price above EMA50 (+15)")
            raw_score += 15
        else:
            negative.append("Price below EMA50 (-15)")
            raw_score -= 15
    
    # MACD trend
    macd_lower = str(macd_trend).lower()
    if 'bullish' in macd_lower:
        positive.append("Bullish MACD (+10)")
        raw_score += 10
    elif 'bearish' in macd_lower:
        negative.append("Bearish MACD (-10)")
        raw_score -= 10
    
    # Market structure
    ms_lower = str(market_structure).lower()
    if 'bullish' in ms_lower:
        positive.append("Bullish market structure (+15)")
        raw_score += 15
    elif 'bearish' in ms_lower:
        negative.append("Bearish market structure (-15)")
        raw_score -= 15
    elif 'sideways' in ms_lower or 'range' in ms_lower:
        negative.append("Sideways structure (-10)")
        raw_score -= 10
    
    # RSI
    if rsi is not None:
        if rsi > 60:
            positive.append(f"Strong RSI ({rsi:.0f}) (+8)")
            raw_score += 8
        elif rsi > 55:
            positive.append(f"Constructive RSI ({rsi:.0f}) (+5)")
            raw_score += 5
        elif 45 <= rsi <= 55:
            # Neutral RSI - no change
            pass
        elif rsi < 40:
            negative.append(f"Weak RSI ({rsi:.0f}) (-8)")
            raw_score -= 8
    
    # Funding rate
    if funding is not None:
        if funding < 0:
            positive.append("Negative funding (+5)")
            raw_score += 5
        elif funding > 0.0003:
            negative.append("High funding (-5)")
            raw_score -= 5
    
    # Check for resistance nearby (reduces confidence)
    resistance = report.resistance
    if price and resistance:
        distance = abs(resistance - price) / price * 100
        if distance < 2:
            negative.append(f"Resistance nearby (-10)")
            raw_score -= 10
    
    # Bound the score
    raw_score = max(0, min(100, raw_score))
    
    return {
        'positive': positive,
        'negative': negative,
        'total': report.confidence,
        'raw_score': raw_score,
        'explanation': f"Calculated from {len(positive)} positive and {len(negative)} negative factors"
    }


# ============================================================================
# 2. Opportunity Explanation
# ============================================================================

def build_opportunity_explanation(report, analysis) -> Dict[str, Any]:
    """Build detailed opportunity score explanation.
    
    Parameters
    ----------
    report : TacticalReport
        Structured report
    analysis : AnalysisObject or dict
        Original analysis data
    
    Returns
    -------
    dict
        {
            'score': Opportunity score,
            'positive': List of positive contributors,
            'negative': List of negative contributors,
            'assessment': Final assessment text
        }
    """
    positive = []
    negative = []
    
    # Extract values
    price = _get_value(analysis, 'price_usd', 'price')
    ema20 = _get_value(analysis, 'ema20')
    ema50 = _get_value(analysis, 'ema50')
    rsi = _get_value(analysis, 'rsi')
    trend = _get_value(analysis, 'trend', default='Neutral')
    volume = _get_value(analysis, 'volume_usd', 'volume_24h')
    funding = _get_value(analysis, 'funding_rate')
    
    # Trend analysis
    trend_lower = str(trend).lower()
    if 'bullish' in trend_lower:
        positive.append("Trend above EMA20")
    elif 'bearish' in trend_lower:
        negative.append("Bearish trend direction")
    
    # RSI
    if rsi is not None:
        if 50 < rsi < 70:
            positive.append("Healthy momentum zone")
        elif rsi > 70:
            negative.append("Overbought territory")
        elif rsi < 30:
            negative.append("Oversold conditions")
    
    # Volume
    if volume and volume > 1_000_000_000:
        positive.append("High liquidity")
    elif volume and volume < 100_000_000:
        negative.append("Low liquidity")
    
    # Resistance/Support proximity
    if price and report.resistance:
        dist = abs(report.resistance - price) / price * 100
        if dist < 1.5:
            negative.append("Near resistance")
    
    if price and report.support:
        dist = abs(report.support - price) / price * 100
        if dist < 1.5:
            negative.append("Near support")
    
    # MACD
    macd_trend = _get_value(analysis, 'macd_trend', default='Neutral')
    if 'bullish' in str(macd_trend).lower():
        positive.append("Bullish momentum")
    elif 'bearish' in str(macd_trend).lower():
        negative.append("Weak momentum")
    
    # Funding
    if funding is not None:
        if funding < 0:
            positive.append("Negative funding (squeeze potential)")
        elif funding > 0.0005:
            negative.append("Elevated funding (crowded)")
    
    # Generate assessment
    score = report.opportunity_score
    if score >= 75:
        assessment = "High-quality setup with multiple confirming factors."
    elif score >= 60:
        assessment = "Good quality setup with favorable conditions."
    elif score >= 45:
        assessment = "Average-quality setup. Proceed with standard risk management."
    elif score >= 30:
        assessment = "Below-average setup. Consider waiting for better conditions."
    else:
        assessment = "Poor setup quality. Not recommended for entry."
    
    return {
        'score': score,
        'positive': positive,
        'negative': negative,
        'assessment': assessment
    }


# ============================================================================
# 3. Market Summary
# ============================================================================

def build_market_summary(report, analysis) -> str:
    """Build professional institutional-style market summary paragraph.
    
    Parameters
    ----------
    report : TacticalReport
        Structured report
    analysis : AnalysisObject or dict
        Original analysis data
    
    Returns
    -------
    str
        Professional market summary paragraph
    """
    # Extract all needed values
    symbol = report.symbol
    price = report.price
    change_24h = report.change_24h
    rsi = report.rsi
    ema20 = report.ema20
    ema50 = report.ema50
    trend = report.trend
    market_state = report.market_state
    
    # Build sentences
    sentences = []
    
    # Price action
    if price:
        price_str = f"{symbol} is trading at ${price:,.2f}"
        if change_24h is not None:
            direction = "up" if change_24h >= 0 else "down"
            price_str += f", {direction} {abs(change_24h):.1f}% in the last 24 hours"
        sentences.append(price_str + ".")
    
    # Trend and EMAs
    if trend and ema20 and ema50 and price:
        if "Bullish" in trend or "bullish" in trend.lower():
            ema_sentence = f"The asset maintains a bullish posture above both EMA20 (${ema20:,.2f}) and EMA50 (${ema50:,.2f})."
        elif "Bearish" in trend or "bearish" in trend.lower():
            ema_sentence = f"Price action remains bearish, with ${symbol} trading below EMA20 (${ema20:,.2f}) and EMA50 (${ema50:,.2f})."
        else:
            ema_sentence = f"Price is consolidating between EMA20 (${ema20:,.2f}) and EMA50 (${ema50:,.2f}), suggesting indecision."
        sentences.append(ema_sentence)
    
    # RSI
    if rsi is not None:
        if rsi > 70:
            rsi_sentence = f"RSI readings at {rsi:.0f} indicate overbought conditions."
        elif rsi < 30:
            rsi_sentence = f"RSI at {rsi:.0f} signals oversold territory."
        elif rsi > 55:
            rsi_sentence = f"RSI at {rsi:.0f} shows constructive momentum."
        elif rsi < 45:
            rsi_sentence = f"RSI at {rsi:.0f} reflects weakening pressure."
        else:
            rsi_sentence = f"RSI readings at {rsi:.0f} are neutral."
        sentences.append(rsi_sentence)
    
    # Market structure summary
    if market_state:
        state_sentence = f"Market structure analysis suggests {market_state.lower()}."
        sentences.append(state_sentence)
    
    # Combine into paragraph
    paragraph = " ".join(sentences)
    
    return paragraph


# ============================================================================
# 4. Recommendation Explanation
# ============================================================================

def build_recommendation_explanation(report, analysis) -> Dict[str, str]:
    """Build explicit recommendation explanation with reasons.
    
    Parameters
    ----------
    report : TacticalReport
        Structured report
    analysis : AnalysisObject or dict
        Original analysis data
    
    Returns
    -------
    dict
        {
            'recommendation': The recommendation,
            'reason': The explicit reason,
            'supporting_factors': List of supporting evidence
        }
    """
    recommendation = report.recommendation
    supporting_factors = []
    
    # Extract values
    price = _get_value(analysis, 'price_usd', 'price')
    ema20 = _get_value(analysis, 'ema20')
    ema50 = _get_value(analysis, 'ema50')
    rsi = _get_value(analysis, 'rsi')
    trend = _get_value(analysis, 'trend', default='Neutral')
    market_structure = _get_value(analysis, 'market_structure', default='')
    resistance = report.resistance
    support = report.support
    risk_reward = report.risk_reward
    
    reason_parts = []
    
    # Build explanation based on recommendation type
    if "BUY" in recommendation.upper():
        # Positive factors for BUY
        if trend and "bullish" in trend.lower():
            reason_parts.append("Trend is constructive.")
            supporting_factors.append("Bullish trend confirmed")
        
        if ema20 and ema50 and price:
            if price > ema20 > ema50:
                reason_parts.append("Price is above both EMAs with proper alignment.")
                supporting_factors.append("EMA alignment bullish")
        
        if rsi and rsi > 55:
            reason_parts.append("RSI supports continuation.")
            supporting_factors.append(f"RSI at {rsi:.0f}")
        
        # Risks
        if resistance and price:
            dist = abs(resistance - price) / price * 100
            if dist < 2:
                reason_parts.append(f"However, resistance is nearby at ${resistance:,.2f}.")
                supporting_factors.append("Watch resistance level")
    
    elif "SELL" in recommendation.upper():
        # Positive factors for SELL
        if trend and "bearish" in trend.lower():
            reason_parts.append("Trend has turned bearish.")
            supporting_factors.append("Bearish trend confirmed")
        
        if ema20 and ema50 and price:
            if price < ema20 < ema50:
                reason_parts.append("Price is below both EMAs with bearish alignment.")
                supporting_factors.append("EMA alignment bearish")
        
        if rsi and rsi < 45:
            reason_parts.append("RSI confirms downside pressure.")
            supporting_factors.append(f"RSI at {rsi:.0f}")
        
        if support and price:
            dist = abs(price - support) / price * 100
            if dist < 2:
                reason_parts.append(f"Support at ${support:,.2f} is being tested.")
                supporting_factors.append("Testing support level")
    
    else:  # WAIT
        # Reasons for WAIT
        if price and ema20 and ema50:
            if min(ema20, ema50) < price < max(ema20, ema50):
                reason_parts.append("Price is trapped between EMAs, indicating consolidation.")
                supporting_factors.append("Consolidating between EMAs")
        
        if resistance and price:
            if abs(resistance - price) / price * 100 < 2:
                reason_parts.append(f"Price is testing resistance at ${resistance:,.2f}.")
                supporting_factors.append("At resistance")
        
        if support and price:
            if abs(price - support) / price * 100 < 2:
                reason_parts.append(f"Price is testing support at ${support:,.2f}.")
                supporting_factors.append("At support")
        
        if risk_reward and risk_reward < 1.5:
            reason_parts.append(f"Current reward/risk ratio of {risk_reward:.1f}:1 is poor.")
            supporting_factors.append(f"Low R:R ({risk_reward:.1f}:1)")
        
        reason_parts.append("Waiting improves statistical edge.")
    
    reason = " ".join(reason_parts) if reason_parts else "Market conditions suggest caution."
    
    return {
        'recommendation': recommendation,
        'reason': reason,
        'supporting_factors': supporting_factors
    }


# ============================================================================
# 5. Probability Analysis
# ============================================================================

def build_probability_analysis(report, analysis) -> Dict[str, Any]:
    """Build detailed scenario analysis with trigger conditions.
    
    Parameters
    ----------
    report : TacticalReport
        Structured report
    analysis : AnalysisObject or dict
        Original analysis data
    
    Returns
    -------
    dict
        {
            'bullish': {...},
            'bearish': {...},
            'sideways': {...}
        }
    """
    # Extract values
    price = _get_value(analysis, 'price_usd', 'price')
    rsi = _get_value(analysis, 'rsi')
    ema20 = _get_value(analysis, 'ema20')
    macd_trend = _get_value(analysis, 'macd_trend', default='Neutral')
    resistance = report.resistance
    support = report.support
    volume = _get_value(analysis, 'volume_usd', 'volume_24h')
    
    # Bullish scenario
    bullish = {
        'probability': report.bullish_probability,
        'name': 'Bullish Continuation',
        'requires': [],
        'expected_outcome': ''
    }
    
    if resistance:
        bullish['requires'].append(f"Break above resistance at ${resistance:,.2f}")
    if volume:
        bullish['requires'].append("Increasing volume confirmation")
    if rsi is not None and rsi < 60:
        bullish['requires'].append(f"RSI strength above 55 (currently {rsi:.0f})")
    if 'bullish' not in str(macd_trend).lower():
        bullish['requires'].append("MACD bullish crossover")
    
    bullish['expected_outcome'] = f"Targets ${report.take_profit_1:,.2f}" if report.take_profit_1 else "Upside continuation"
    
    # Bearish scenario
    bearish = {
        'probability': report.bearish_probability,
        'name': 'Bearish Breakdown',
        'requires': [],
        'expected_outcome': ''
    }
    
    if support:
        bearish['requires'].append(f"Break below support at ${support:,.2f}")
    if ema20 and price and price > ema20:
        bearish['requires'].append(f"Loss of EMA20 at ${ema20:,.2f}")
    if 'bearish' not in str(macd_trend).lower():
        bearish['requires'].append("MACD bearish crossover")
    
    bearish['expected_outcome'] = f"Targets ${report.take_profit_1:,.2f}" if report.take_profit_1 else "Downside continuation"
    
    # Sideways scenario
    sideways = {
        'probability': report.sideways_probability,
        'name': 'Sideways Consolidation',
        'requires': [],
        'expected_outcome': ''
    }
    
    if support and resistance:
        sideways['requires'].append(f"Price remains between ${support:,.2f} and ${resistance:,.2f}")
        sideways['expected_outcome'] = f"Range-bound trading until breakout"
    else:
        sideways['expected_outcome'] = "Consolidation with no clear directional bias"
    
    return {
        'bullish': bullish,
        'bearish': bearish,
        'sideways': sideways,
        'most_likely': report.most_likely
    }


# ============================================================================
# 6. Educational Insight
# ============================================================================

def build_educational_insight(report, analysis) -> str:
    """Build educational insight explaining the trading logic in plain English.
    
    Parameters
    ----------
    report : TacticalReport
        Structured report
    analysis : AnalysisObject or dict
        Original analysis data
    
    Returns
    -------
    str
        Educational explanation of the trading logic
    """
    # Extract values
    price = _get_value(analysis, 'price_usd', 'price')
    ema20 = _get_value(analysis, 'ema20')
    ema50 = _get_value(analysis, 'ema50')
    rsi = _get_value(analysis, 'rsi')
    trend = _get_value(analysis, 'trend', default='Neutral')
    market_state = report.market_state
    recommendation = report.recommendation
    
    insights = []
    
    # Opening
    insights.append(f"Why Uncle Tony thinks this:")
    insights.append("")
    
    # Market state explanation
    if market_state:
        if "Uptrend" in market_state:
            insights.append(f"The market state is classified as {market_state.lower()}, which means the dominant pressure is bullish. Price is making higher highs and higher lows.")
        elif "Downtrend" in market_state:
            insights.append(f"The market state shows {market_state.lower()}, indicating sellers are in control. The path of least resistance is lower.")
        elif "Range" in market_state or "Sideways" in market_state:
            insights.append(f"The market is in {market_state.lower()}, meaning neither buyers nor sellers have clear control. This is a choppy environment for directional trades.")
    
    # EMA explanation
    if price and ema20 and ema50:
        if price > ema20 > ema50:
            insights.append(f"")
            insights.append(f"EMAs are trend-following indicators. When price > EMA20 > EMA50, the short-term momentum aligns with the longer-term trend—this is a bullish alignment.")
        elif price < ema20 < ema50:
            insights.append(f"")
            insights.append(f"Price below both EMAs with EMA20 < EMA50 indicates bearish momentum. Sellers are pressing the asset lower on multiple timeframes.")
    
    # RSI explanation
    if rsi is not None:
        insights.append(f"")
        if rsi > 70:
            insights.append(f"RSI at {rsi:.0f} is in overbought territory (>70). This doesn't mean price will crash, but it suggests the move may be extended and due for consolidation or reversal.")
        elif rsi < 30:
            insights.append(f"RSI at {rsi:.0f} is oversold (<30). While this can signal a bounce, oversold conditions can persist in strong downtrends. It's a warning sign, not a buy signal alone.")
        elif 55 < rsi < 70:
            insights.append(f"RSI at {rsi:.0f} shows healthy bullish momentum. This zone often supports continued upside without being overextended.")
        elif 30 < rsi < 45:
            insights.append(f"RSI at {rsi:.0f} indicates mild bearish pressure. Not oversold, but momentum is weak.")
        else:
            insights.append(f"RSI at {rsi:.0f} is neutral. Neither buyers nor sellers have a momentum advantage.")
    
    # Recommendation reasoning
    insights.append(f"")
    if "BUY" in recommendation.upper():
        insights.append(f"The BUY recommendation comes from multiple confirming factors. Uncle Tony waits for alignment between trend, EMAs, and momentum before suggesting entry. This filters out noise and focuses on high-probability setups.")
    elif "SELL" in recommendation.upper():
        insights.append(f"The SELL recommendation reflects bearish alignment across multiple indicators. Uncle Tony prioritizes setups where multiple factors confirm the same direction, reducing the risk of false signals.")
    else:
        insights.append(f"The WAIT recommendation means not all criteria are met for a directional trade. Uncle Tony prioritizes capital preservation—entering a low-quality setup often leads to losses. Waiting for clarity is a valid strategy.")
    
    # Risk management note
    if report.risk_reward:
        insights.append(f"")
        insights.append(f"Risk/reward at {report.risk_reward:.1f}:1 means your potential reward exceeds your risk. This is essential—only take trades where the math works in your favor.")
    
    return "\n".join(insights)


# ============================================================================
# Helper Functions
# ============================================================================

def _get_value(analysis, key1: str, key2: str = None, default=None) -> Any:
    """Extract value from AnalysisObject or dict.
    
    Parameters
    ----------
    analysis : AnalysisObject or dict
        Source data
    key1 : str
        Primary key
    key2 : str, optional
        Secondary key
    default : Any
        Default value if not found
    
    Returns
    -------
    Any
        Extracted value
    """
    if hasattr(analysis, 'market_data'):
        # AnalysisObject format
        # Try direct attribute first
        if hasattr(analysis, key1):
            return getattr(analysis, key1)
        # Try nested in market_data
        if hasattr(analysis, 'market_data') and hasattr(analysis.market_data, key1):
            return getattr(analysis.market_data, key1)
        # Try nested in indicators
        if hasattr(analysis, 'indicators') and hasattr(analysis.indicators, key1):
            return getattr(analysis.indicators, key1)
        # Try nested in decision
        if hasattr(analysis, 'decision') and hasattr(analysis.decision, key1):
            return getattr(analysis.decision, key1)
    else:
        # Dict format
        if key1 in analysis:
            return analysis[key1]
        if key2 and key2 in analysis:
            return analysis[key2]
    
    return default


def format_confidence_breakdown(breakdown: Dict[str, Any]) -> str:
    """Format confidence breakdown for display.
    
    Parameters
    ----------
    breakdown : dict
        Confidence breakdown from build_confidence_breakdown()
    
    Returns
    -------
    str
        Formatted text
    """
    lines = []
    
    lines.append("Confidence Breakdown")
    lines.append("")
    
    if breakdown['positive']:
        lines.append("Positive Factors:")
        for factor in breakdown['positive']:
            lines.append(f"  + {factor}")
        lines.append("")
    
    if breakdown['negative']:
        lines.append("Negative Factors:")
        for factor in breakdown['negative']:
            lines.append(f"  - {factor}")
        lines.append("")
    
    lines.append(f"Final Confidence: {breakdown['total']}/100")
    
    return "\n".join(lines)


def format_opportunity_explanation(explanation: Dict[str, Any]) -> str:
    """Format opportunity explanation for display.
    
    Parameters
    ----------
    explanation : dict
        Opportunity explanation from build_opportunity_explanation()
    
    Returns
    -------
    str
        Formatted text
    """
    lines = []
    
    lines.append(f"Opportunity: {explanation['score']}/100")
    lines.append("")
    
    if explanation['positive']:
        lines.append("Positive")
        for factor in explanation['positive']:
            lines.append(f"  • {factor}")
        lines.append("")
    
    if explanation['negative']:
        lines.append("Negative")
        for factor in explanation['negative']:
            lines.append(f"  • {factor}")
        lines.append("")
    
    lines.append("Assessment")
    lines.append(f"{explanation['assessment']}")
    
    return "\n".join(lines)


def format_probability_analysis(analysis: Dict[str, Any]) -> str:
    """Format probability analysis for display.
    
    Parameters
    ----------
    analysis : dict
        Probability analysis from build_probability_analysis()
    
    Returns
    -------
    str
        Formatted text
    """
    lines = []
    
    # Bullish
    bull = analysis['bullish']
    lines.append(f"{bull['name']}")
    lines.append(f"{bull['probability']}%")
    if bull['requires']:
        lines.append("Requires:")
        for req in bull['requires']:
            lines.append(f"  - {req}")
    lines.append(f"Expected: {bull['expected_outcome']}")
    lines.append("")
    
    # Sideways
    side = analysis['sideways']
    lines.append(f"{side['name']}")
    lines.append(f"{side['probability']}%")
    if side['requires']:
        lines.append("Requires:")
        for req in side['requires']:
            lines.append(f"  - {req}")
    lines.append(f"Expected: {side['expected_outcome']}")
    lines.append("")
    
    # Bearish
    bear = analysis['bearish']
    lines.append(f"{bear['name']}")
    lines.append(f"{bear['probability']}%")
    if bear['requires']:
        lines.append("Requires:")
        for req in bear['requires']:
            lines.append(f"  - {req}")
    lines.append(f"Expected: {bear['expected_outcome']}")
    
    return "\n".join(lines)

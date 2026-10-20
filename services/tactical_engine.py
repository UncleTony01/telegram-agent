"""Uncle Tony Tactical Engine - Local Rule-Based Analysis Fallback.

This module provides a complete market analysis without relying on external AI.
It serves as a failover when AI services are unavailable, ensuring users always
receive actionable trading intelligence.

Features:
- Deterministic decision engine using local indicators
- Natural language narrative generation in Uncle Tony's style
- Complete analysis structure matching AI-generated reports
- No external API dependencies
- NEW: Supports AnalysisObject architecture
"""

from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# Decision Engine
# ============================================================================

def analyze_market_tactically(overview) -> Dict[str, Any]:
    """Generate complete tactical analysis using local indicators only.
    
    Parameters
    ----------
    overview : dict or AnalysisObject
        Market overview from okx_service.get_market_overview() or AnalysisObject
    
    Returns
    -------
    dict
        Complete tactical analysis including bias, confidence, scenarios,
        support/resistance, recommendation, and risk assessment
    """
    from services.opportunity_scanner import calculate_opportunity_score

    # Extract or calculate Opportunity Result (Phase 5.5)
    opp_result = None
    if hasattr(overview, '_opportunity_result') and overview._opportunity_result:
        opp_result = overview._opportunity_result
    elif isinstance(overview, dict) and '_opportunity_result' in overview:
        opp_result = overview['_opportunity_result']
    else:
        try:
            opp_result = calculate_opportunity_score(overview)
            if hasattr(overview, '__dict__'):
                overview._opportunity_result = opp_result
            elif isinstance(overview, dict):
                overview['_opportunity_result'] = opp_result
        except Exception:
            opp_result = None

    # Support both dict and AnalysisObject inputs
    if hasattr(overview, 'market_data'):
        # AnalysisObject input
        return _analyze_from_analysis_object(overview, opp_result=opp_result)
    else:
        # Legacy dict input (backward compatible)
        return _analyze_from_dict(overview, opp_result=opp_result)


def _perform_analysis(
    symbol: str,
    price: Optional[float],
    ema20: Optional[float],
    ema50: Optional[float],
    rsi: Optional[float],
    high24: Optional[float],
    low24: Optional[float],
    funding: Optional[float],
    volume: Optional[float],
    oi: Optional[float],
    market_structure: str,
    trend_analysis: dict,
    probability: Any = None,
    trade_decision: Any = None,
    opp_result: Any = None,
) -> Dict[str, Any]:
    """Internal helper to perform analysis and construct dictionary."""
    bias = determine_bias(price, ema20, ema50, rsi, market_structure, trend_analysis)
    confidence = calculate_confidence(price, ema20, ema50, rsi, funding, probability)
    scenarios = generate_scenarios(bias, confidence, price, ema20, ema50, high24, low24, rsi)
    support, resistance = identify_key_levels(price, ema20, ema50, low24, high24)
    
    # Recommendation logic considering Opportunity Score (Requirement 5)
    if opp_result is not None:
        if opp_result.score > 80:
            recommendation = "WATCH FOR ENTRY"
        elif opp_result.score < 40:
            recommendation = "NO TRADE"
        else:
            recommendation = "WAIT"
    else:
        recommendation = generate_recommendation(bias, confidence, price, resistance, support, rsi)
        
    risk_assessment = assess_risk(funding, rsi, volume, oi, confidence, price, high24)
    
    return {
        "symbol": symbol,
        "bias": bias,
        "confidence": confidence,
        "scenarios": scenarios,
        "support": support,
        "resistance": resistance,
        "recommendation": recommendation,
        "risk_assessment": risk_assessment,
        "price": price,
        "ema20": ema20,
        "ema50": ema50,
        "rsi": rsi,
        "funding": funding,
        "opportunity_result": opp_result,
        "opportunity_score": opp_result.score if opp_result else None,
    }


def _analyze_from_analysis_object(analysis, opp_result: Any = None) -> Dict[str, Any]:
    """Analyze from AnalysisObject (new architecture)."""
    symbol = analysis.symbol
    price = analysis.market_data.price
    ema20 = analysis.indicators.ema20
    ema50 = analysis.indicators.ema50
    rsi = analysis.indicators.rsi
    high24 = analysis.market_data.high_24h
    low24 = analysis.market_data.low_24h
    funding = analysis.derivatives.funding_rate
    volume = analysis.market_data.volume_24h
    oi = analysis.derivatives.open_interest_usd
    
    market_structure = analysis.market_structure.trend.lower() if analysis.market_structure.trend else ""
    trend_analysis = {"trend": analysis.market_structure.trend, "bias": analysis.decision.bias}
    
    probability = None
    trade_decision = None
    
    return _perform_analysis(
        symbol, price, ema20, ema50, rsi, high24, low24, 
        funding, volume, oi, market_structure, trend_analysis,
        probability, trade_decision, opp_result
    )


def _analyze_from_dict(overview: dict, opp_result: Any = None) -> Dict[str, Any]:
    """Generate complete tactical analysis using local indicators only."""
    def _float(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    
    symbol = overview.get("symbol", "UNKNOWN")
    price = _float(overview.get("price_usd"))
    ema20 = _float(overview.get("ema20"))
    ema50 = _float(overview.get("ema50"))
    rsi = _float(overview.get("rsi"))
    high24 = _float(overview.get("high_24h_usd"))
    low24 = _float(overview.get("low_24h_usd"))
    funding = _float(overview.get("funding_rate"))
    volume = _float(overview.get("volume_usd"))
    oi = _float(overview.get("open_interest_usd"))
    
    probability = overview.get("probability")
    trade_decision = overview.get("trade_decision")
    market_structure = str(overview.get("market_structure", "")).lower()
    trend_analysis = overview.get("trend_analysis", {})
    
    return _perform_analysis(
        symbol, price, ema20, ema50, rsi, high24, low24, 
        funding, volume, oi, market_structure, trend_analysis,
        probability, trade_decision, opp_result
    )


def determine_bias(
    price: Optional[float],
    ema20: Optional[float],
    ema50: Optional[float],
    rsi: Optional[float],
    market_structure: str,
    trend_analysis: dict,
) -> str:
    """Determine overall market bias: Bullish, Bearish, or Neutral."""
    
    if price is None or ema20 is None or ema50 is None:
        return "Neutral"
    
    bullish_signals = 0
    bearish_signals = 0
    
    # EMA alignment
    if price > ema20 and ema20 > ema50:
        bullish_signals += 3
    elif price < ema20 and ema20 < ema50:
        bearish_signals += 3
    elif price > ema20 and price > ema50:
        bullish_signals += 2
    elif price < ema20 and price < ema50:
        bearish_signals += 2
    
    # RSI
    if rsi is not None:
        if rsi > 60:
            bullish_signals += 2
        elif rsi > 55:
            bullish_signals += 1
        elif rsi < 40:
            bearish_signals += 2
        elif rsi < 45:
            bearish_signals += 1
    
    # Market structure
    if "bullish" in market_structure or "bull" in market_structure:
        bullish_signals += 2
    elif "bearish" in market_structure or "bear" in market_structure:
        bearish_signals += 2
    
    # Trend analysis
    trend_bias = str(trend_analysis.get("bias", "")).lower()
    if trend_bias == "bullish":
        bullish_signals += 1
    elif trend_bias == "bearish":
        bearish_signals += 1
    
    # Determine bias
    if bullish_signals > bearish_signals + 2:
        return "Bullish"
    elif bearish_signals > bullish_signals + 2:
        return "Bearish"
    else:
        return "Neutral"


def calculate_confidence(
    price: Optional[float],
    ema20: Optional[float],
    ema50: Optional[float],
    rsi: Optional[float],
    funding: Optional[float],
    probability: Any,
) -> int:
    """Calculate confidence level (0-100)."""
    
    confidence = 50  # baseline
    
    # EMA alignment adds/reduces confidence
    if price is not None and ema20 is not None and ema50 is not None:
        if (price > ema20 > ema50) or (price < ema20 < ema50):
            confidence += 20  # strong alignment
        elif (price > ema20 and price > ema50) or (price < ema20 and price < ema50):
            confidence += 10  # moderate alignment
    
    # RSI adds confidence in trending zones
    if rsi is not None:
        if 55 <= rsi <= 70 or 30 <= rsi <= 45:
            confidence += 10
        elif rsi > 70 or rsi < 30:
            confidence -= 10  # extreme zones reduce confidence
    
    # Funding rate impact
    if funding is not None:
        if abs(funding) < 0.0001:
            confidence += 5  # neutral funding is good
        elif funding >= 0.0003:
            confidence -= 10  # high funding = risk
    
    # Use probability engine if available
    if probability:
        prob_conf = getattr(probability, "confidence", None)
        if prob_conf is not None:
            confidence = int(confidence * 0.5 + prob_conf * 0.5)
    
    return max(0, min(100, confidence))


def generate_scenarios(
    bias: str,
    confidence: int,
    price: Optional[float],
    ema20: Optional[float],
    ema50: Optional[float],
    high24: Optional[float],
    low24: Optional[float],
    rsi: Optional[float],
) -> Dict[str, str]:
    """Generate bullish, bearish, and sideways scenarios."""
    
    scenarios = {}
    
    # Bullish scenario
    if bias == "Bullish":
        if confidence > 70:
            scenarios["bullish"] = f"Strong continuation above ${ema20:.2f} targeting ${high24 * 1.025:.2f}" if ema20 and high24 else "Strong bullish continuation expected"
        else:
            scenarios["bullish"] = f"Potential move to ${high24:.2f} if ${ema20:.2f} holds" if ema20 and high24 else "Bullish potential with support holding"
    else:
        scenarios["bullish"] = f"Reclaim ${ema20:.2f} could shift momentum" if ema20 else "Recovery needed to shift momentum"
    
    # Bearish scenario
    if bias == "Bearish":
        if confidence > 70:
            scenarios["bearish"] = f"Breakdown below ${ema20:.2f} targeting ${low24 * 0.975:.2f}" if ema20 and low24 else "Strong bearish pressure continues"
        else:
            scenarios["bearish"] = f"Potential drop to ${low24:.2f} if ${ema20:.2f} fails" if ema20 and low24 else "Bearish risk if support breaks"
    else:
        scenarios["bearish"] = f"Loss of ${ema20:.2f} would confirm weakness" if ema20 else "Weakness if key support fails"
    
    # Sideways scenario
    if bias == "Neutral" or confidence < 50:
        scenarios["sideways"] = f"Consolidation between ${low24:.2f} and ${high24:.2f}" if low24 and high24 else "Range-bound consolidation likely"
    else:
        scenarios["sideways"] = "Brief consolidation before next directional move"
    
    return scenarios


def identify_key_levels(
    price: Optional[float],
    ema20: Optional[float],
    ema50: Optional[float],
    low24: Optional[float],
    high24: Optional[float],
) -> Tuple[Optional[float], Optional[float]]:
    """Identify key support and resistance levels."""
    
    support = None
    resistance = None
    
    if price is not None:
        # Support: strongest of EMA20, EMA50, or low24 below price
        support_candidates = []
        if ema20 is not None and ema20 < price:
            support_candidates.append(ema20)
        if ema50 is not None and ema50 < price:
            support_candidates.append(ema50)
        if low24 is not None and low24 < price:
            support_candidates.append(low24)
        
        if support_candidates:
            support = max(support_candidates)  # nearest support
        
        # Resistance: weakest of EMA20, EMA50, or high24 above price
        resistance_candidates = []
        if ema20 is not None and ema20 > price:
            resistance_candidates.append(ema20)
        if ema50 is not None and ema50 > price:
            resistance_candidates.append(ema50)
        if high24 is not None and high24 > price:
            resistance_candidates.append(high24)
        
        if resistance_candidates:
            resistance = min(resistance_candidates)  # nearest resistance
    
    return support, resistance


def generate_recommendation(
    bias: str,
    confidence: int,
    price: Optional[float],
    resistance: Optional[float],
    support: Optional[float],
    rsi: Optional[float],
) -> str:
    """Generate trading recommendation."""
    
    if bias == "Bullish" and confidence > 65:
        if rsi is not None and rsi > 70:
            return "WAIT for pullback to enter longs"
        return "BUY on support or breakout above resistance"
    
    elif bias == "Bearish" and confidence > 65:
        if rsi is not None and rsi < 30:
            return "WAIT for bounce to enter shorts"
        return "SELL on resistance rejection or breakdown"
    
    elif bias == "Neutral" or confidence < 50:
        return "WAIT for clearer directional signal"
    
    else:
        # Moderate confidence
        if bias == "Bullish":
            return "CAUTIOUS BUY with tight stops"
        elif bias == "Bearish":
            return "CAUTIOUS SELL with tight stops"
        else:
            return "WAIT - risk/reward unclear"


def assess_risk(
    funding: Optional[float],
    rsi: Optional[float],
    volume: Optional[float],
    oi: Optional[float],
    confidence: int,
    price: Optional[float],
    high24: Optional[float],
) -> str:
    """Assess overall risk level."""
    
    risk_factors = []
    
    # Funding risk
    if funding is not None and funding >= 0.0003:
        risk_factors.append("elevated funding rate")
    
    # RSI extremes
    if rsi is not None:
        if rsi > 75:
            risk_factors.append("overbought RSI")
        elif rsi < 25:
            risk_factors.append("oversold RSI")
    
    # Low confidence
    if confidence < 50:
        risk_factors.append("low signal confidence")
    
    # Near resistance
    if price is not None and high24 is not None:
        distance = (high24 - price) / high24 * 100 if high24 > 0 else 100
        if distance < 2:
            risk_factors.append("approaching 24h high")
    
    if len(risk_factors) >= 3:
        return f"HIGH RISK - {', '.join(risk_factors)}"
    elif len(risk_factors) >= 1:
        return f"MODERATE RISK - {', '.join(risk_factors)}"
    else:
        return "ACCEPTABLE RISK"


# ============================================================================
# Narrative Builder
# ============================================================================

def build_tactical_narrative(tactical_analysis: Dict[str, Any]) -> str:
    """Build natural language narrative in Uncle Tony's style.
    
    Parameters
    ----------
    tactical_analysis : dict
        Output from analyze_market_tactically()
    
    Returns
    -------
    str
        Complete narrative report
    """
    
    symbol = tactical_analysis["symbol"]
    bias = tactical_analysis["bias"]
    confidence = tactical_analysis["confidence"]
    scenarios = tactical_analysis["scenarios"]
    support = tactical_analysis["support"]
    resistance = tactical_analysis["resistance"]
    recommendation = tactical_analysis["recommendation"]
    risk_assessment = tactical_analysis["risk_assessment"]
    price = tactical_analysis["price"]
    ema20 = tactical_analysis["ema20"]
    ema50 = tactical_analysis["ema50"]
    rsi = tactical_analysis["rsi"]
    funding = tactical_analysis["funding"]
    
    lines = []
    
    # Header
    lines.extend([
        "=" * 24,
        f"UNCLE TONY TACTICAL ANALYSIS: {symbol}",
        "=" * 24,
        "",
    ])
    
    # Executive Summary
    lines.append("📊 EXECUTIVE SUMMARY")
    lines.append("")
    lines.append(f"Market Bias:     {bias}")
    lines.append(f"Confidence:      {confidence}/100")
    lines.append(f"Recommendation:  {recommendation}")
    lines.append(f"Risk Level:      {risk_assessment}")
    lines.append("")
    
    # Market Overview
    lines.append("📈 MARKET OVERVIEW")
    lines.append("")
    
    if price and ema20 and ema50:
        if bias == "Bullish":
            lines.append(f"{symbol} is showing bullish structure with price at ${price:.2f}, trading above key moving averages.")
        elif bias == "Bearish":
            lines.append(f"{symbol} is displaying bearish pressure at ${price:.2f}, struggling below key moving averages.")
        else:
            lines.append(f"{symbol} is consolidating at ${price:.2f}, stuck between technical levels with unclear direction.")
    
    lines.append("")
    
    # Technical Levels
    lines.append("🎯 KEY LEVELS")
    lines.append("")
    if support:
        lines.append(f"Support:     ${support:.2f}")
    else:
        lines.append("Support:     No clear level below")
    
    if resistance:
        lines.append(f"Resistance:  ${resistance:.2f}")
    else:
        lines.append("Resistance:  No clear level above")
    lines.append("")
    
    # Indicators
    lines.append("📉 TECHNICAL INDICATORS")
    lines.append("")
    if ema20:
        lines.append(f"EMA20:       ${ema20:.2f}")
    if ema50:
        lines.append(f"EMA50:       ${ema50:.2f}")
    if rsi:
        rsi_desc = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
        lines.append(f"RSI:         {rsi:.1f} ({rsi_desc})")
    if funding:
        lines.append(f"Funding:     {funding:.4%}")
    lines.append("")
    
    # Scenarios
    lines.append("🔮 SCENARIOS")
    lines.append("")
    if "bullish" in scenarios:
        lines.append(f"Bullish:  {scenarios['bullish']}")
    if "bearish" in scenarios:
        lines.append(f"Bearish:  {scenarios['bearish']}")
    if "sideways" in scenarios:
        lines.append(f"Sideways: {scenarios['sideways']}")
    lines.append("")
    
    # Trading Plan
    lines.append("💡 TRADING PLAN")
    lines.append("")
    lines.append(f"Action: {recommendation}")
    lines.append("")
    
    if bias == "Bullish" and confidence > 60:
        lines.append("Entry Strategy:")
        if support:
            lines.append(f"  • Aggressive: Buy at support ${support:.2f}")
        if resistance:
            lines.append(f"  • Conservative: Buy breakout above ${resistance:.2f}")
        if support:
            lines.append(f"  • Stop Loss: Below ${support * 0.98:.2f}")
    
    elif bias == "Bearish" and confidence > 60:
        lines.append("Entry Strategy:")
        if resistance:
            lines.append(f"  • Aggressive: Sell at resistance ${resistance:.2f}")
        if support:
            lines.append(f"  • Conservative: Sell breakdown below ${support:.2f}")
        if resistance:
            lines.append(f"  • Stop Loss: Above ${resistance * 1.02:.2f}")
    
    else:
        lines.append("Strategy: Wait for clearer setup")
        lines.append(f"  • Watch for break of ${resistance:.2f} or ${support:.2f}" if resistance and support else "  • Monitor for directional break")
    
    lines.append("")
    
    # Risk Warning
    lines.append("⚠️  RISK ASSESSMENT")
    lines.append("")
    lines.append(f"{risk_assessment}")
    lines.append("")

    # Opportunity Scanner (Phase 5.5)
    opp_result = tactical_analysis.get("opportunity_result")
    if opp_result:
        lines.append("🎯 OPPORTUNITY")
        lines.append("")
        lines.append("Score:")
        lines.append(f"{opp_result.score} / 100")
        lines.append("")
        lines.append("Classification:")
        lines.append(f"{opp_result.classification}")
        lines.append("")
        lines.append("Priority:")
        lines.append(f"{opp_result.priority}")
        lines.append("")
        lines.append("Confidence:")
        lines.append(f"{opp_result.confidence}%")
        lines.append("")
        lines.append("Reasons")
        if opp_result.reasons:
            for reason in opp_result.reasons[:10]:
                clean_reason = reason.lstrip("✓•- ").strip()
                lines.append(f"✓ {clean_reason}")
        else:
            lines.append("✓ Standard market conditions")
        lines.append("")
        if opp_result.score > 80:
            lines.append("🔥 HIGH QUALITY SETUP")
            lines.append("")
        elif opp_result.score < 40:
            lines.append("⚠ Low-quality setup.")
            lines.append("Waiting is preferred.")
            lines.append("")
    
    # Footer
    lines.extend([
        "=" * 24,
        "Uncle Tony Tactical Engine - Local Analysis",
        "Generated without external AI dependency",
        "=" * 24,
    ])
    
    return "\n".join(lines)


def generate_tactical_analysis(overview: dict) -> str:
    """Main function: analyze market and generate narrative.
    
    Parameters
    ----------
    overview : dict
        Market overview from okx_service.get_market_overview()
    
    Returns
    -------
    str
        Complete tactical analysis narrative
    """
    tactical_analysis = analyze_market_tactically(overview)
    narrative = build_tactical_narrative(tactical_analysis)
    return narrative

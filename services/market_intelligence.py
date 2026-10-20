"""Market Intelligence Engine for Uncle Tony AI.

This module transforms Uncle Tony from a market analysis bot into a market
intelligence assistant that prioritizes trade quality over raw technical analysis.

Features:
- 10 market state classifications
- Opportunity scoring (0-100)
- Edge calculation (positive/neutral/negative)
- Warning generation
- Confidence breakdown per component
- Executive dashboard summary
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ============================================================================
# Market Intelligence Dataclass
# ============================================================================

@dataclass
class MarketIntelligence:
    """Holds comprehensive market intelligence for a single asset."""
    # Core fields
    asset: str
    market_state: str
    conviction_score: int  # 0-100
    opportunity_score: int  # 0-100
    expected_edge: str  # "Positive", "Neutral", "Negative"
    expected_gain: Optional[float]  # percentage
    expected_loss: Optional[float]  # percentage
    risk_reward: Optional[float]  # e.g., 2.5 means 2.5:1
    warnings: List[str]
    recommendation: str  # "LONG", "SHORT", "WAIT", "NO TRADE"
    confidence_breakdown: Dict[str, int]  # component contributions
    summary: str  # one-sentence executive summary


# ============================================================================
# Market State Engine
# ============================================================================

MARKET_STATES = [
    "Strong Uptrend",
    "Healthy Uptrend",
    "Pullback",
    "Accumulation",
    "Distribution",
    "Compression",
    "Expansion",
    "Sideways Range",
    "Weak Downtrend",
    "Strong Downtrend",
]


def determine_market_state(overview: dict) -> str:
    """Determine the current market state using deterministic classification.
    
    Classification criteria:
    - Strong Uptrend: price >> EMA20 >> EMA50, RSI 65-80, bullish structure, positive funding
    - Healthy Uptrend: price > EMA20 > EMA50, RSI 55-65, bullish structure, neutral funding
    - Pullback: price < EMA20 < EMA50, RSI 40-55, still Bullish structure
    - Accumulation: price between EMAs, RSI 45-55, consolidation pattern
    - Distribution: price between EMAs, RSI 45-55, bearish structure
    - Compression: price near recent range, low volatility, RSI 45-55
    - Expansion: high volatility, price breaking range, RSI > 65 or < 35
    - Sideways Range: price in clear range, RSI 45-55, no clear trend
    - Weak Downtrend: price < EMA20 < EMA50, RSI 35-45, bearish structure
    - Strong Downtrend: price << EMA20 << EMA50, RSI < 35, bearish structure, negative funding
    """
    
    def _float(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    
    price = _float(overview.get("price_usd"))
    ema20 = _float(overview.get("ema20"))
    ema50 = _float(overview.get("ema50"))
    rsi = _float(overview.get("rsi"))
    high24 = _float(overview.get("high_24h_usd"))
    low24 = _float(overview.get("low_24h_usd"))
    funding = _float(overview.get("funding_rate"))
    
    # Market structure from trend_engine or probability_engine
    market_structure = str(overview.get("market_structure", "")).lower()
    trend_result = overview.get("trend_analysis", {})
    trend_trend = str(trend_result.get("trend", "")).lower()
    
    # Calculate price positions relative to EMAs
    price_above_ema20 = price is not None and ema20 is not None and price > ema20
    price_above_ema50 = price is not None and ema50 is not None and price > ema50
    price_below_ema20 = price is not None and ema20 is not None and price < ema20
    price_below_ema50 = price is not None and ema50 is not None and price < ema50
    
    ema_bullish = ema20 is not None and ema50 is not None and ema20 > ema50
    ema_bearish = ema20 is not None and ema50 is not None and ema20 < ema50
    
    # Determine EMA alignment
    strong_bullish_ema = price_above_ema20 and price_above_ema50 and ema_bullish
    strong_bearish_ema = price_below_ema20 and price_below_ema50 and ema_bearish
    neutral_ema = (price_above_ema20 and price_below_ema50) or (price_below_ema20 and price_above_ema50)
    
    # Calculate volatility
    volatility = None
    if high24 is not None and low24 is not None and low24 > 0:
        volatility = (high24 - low24) / low24 * 100
    
    # Check for sideways consolidation
    range_width = None
    if high24 is not None and low24 is not None and low24 > 0:
        range_width = (high24 - low24) / low24 * 100
    
    is_sideways = market_structure in ["range", "sideways", "consolidation"] or trend_trend == "sideways"
    is_bullish_struct = "bullish" in market_structure or "bull" in market_structure or trend_trend == "bullish"
    is_bearish_struct = "bearish" in market_structure or "bear" in market_structure or trend_trend == "bearish"
    
    # Funding rate thresholds
    high_funding = funding is not None and funding >= 0.0003
    negative_funding = funding is not None and funding < 0.0
    
    # --- Decision Tree ---
    
    # 1. Strong Uptrend
    if (strong_bullish_ema and 
        rsi is not None and 65 <= rsi <= 80 and 
        is_bullish_struct and
        not negative_funding):
        return "Strong Uptrend"
    
    # 2. Healthy Uptrend
    if (strong_bullish_ema and 
        rsi is not None and 55 <= rsi < 65 and 
        is_bullish_struct):
        return "Healthy Uptrend"
    
    # 3. Pullback
    if (price_above_ema20 and price_below_ema50 and 
        rsi is not None and 50 <= rsi < 60 and 
        is_bullish_struct):
        return "Pullback"
    
    # 4. Accumulation
    if (neutral_ema and 
        rsi is not None and 45 <= rsi < 55 and 
        volatility is not None and volatility < 3.0):
        return "Accumulation"
    
    # 5. Distribution
    if (neutral_ema and 
        rsi is not None and 45 <= rsi < 55 and 
        is_bearish_struct):
        return "Distribution"
    
    # 6. Compression
    if (is_sideways or 
        (range_width is not None and range_width < 2.0 and 
         rsi is not None and 45 <= rsi < 55)):
        return "Compression"
    
    # 7. Expansion
    if (volatility is not None and volatility > 5.0 and 
        (rsi is None or rsi < 35 or rsi > 65)):
        return "Expansion"
    
    # 8. Sideways Range
    if (is_sideways or 
        (neutral_ema and 
         rsi is not None and 45 <= rsi < 55)):
        return "Sideways Range"
    
    # 9. Weak Downtrend
    if (strong_bearish_ema and 
        rsi is not None and 35 <= rsi < 45 and 
        is_bearish_struct):
        return "Weak Downtrend"
    
    # 10. Strong Downtrend
    if (strong_bearish_ema and 
        rsi is not None and rsi < 35 and 
        is_bearish_struct and
        negative_funding):
        return "Strong Downtrend"
    
    # Fallback: default to Sideways Range
    return "Sideways Range"


# ============================================================================
# Opportunity Score Engine
# ============================================================================

def calculate_opportunity_score(overview: dict, market_state: str) -> int:
    """Calculate opportunity score from 0-100.
    
    Weighting:
    - Trend: 25%
    - Probability: 20%
    - Market Structure: 15%
    - Confluence: 15%
    - Risk/Reward: 10%
    - Funding: 5%
    - Open Interest: 10%
    """
    
    def _float(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    
    score = 0
    weightings = {
        "trend": 0.25,
        "probability": 0.20,
        "structure": 0.15,
        "confluence": 0.15,
        "risk_reward": 0.10,
        "funding": 0.05,
        "oi": 0.10,
    }
    
    # --- Trend Component (25%) ---
    trend_score = 0
    price = _float(overview.get("price_usd"))
    ema20 = _float(overview.get("ema20"))
    ema50 = _float(overview.get("ema50"))
    rsi = _float(overview.get("rsi"))
    trend_result = overview.get("trend_analysis", {})
    trend_trend = str(trend_result.get("trend", "")).lower()
    
    if trend_trend in ["strong bullish", "very strong"]:
        trend_score = 100
    elif trend_trend in ["bullish", "strong"]:
        trend_score = 80
    elif trend_trend in ["recovery", "moderate"]:
        trend_score = 60
    elif trend_trend in ["neutral", "weak"]:
        trend_score = 40
    elif trend_trend in ["bearish", "distribution"]:
        trend_score = 30
    elif trend_trend in ["strong bearish", "very strong"]:
        trend_score = 15
    
    # --- Probability Component (20%) ---
    probability_score = 0
    probability = overview.get("probability")
    if probability:
        if isinstance(probability, dict):
            bullish = probability.get("bullish_probability", 0)
            bearish = probability.get("bearish_probability", 0)
            if "Bullish Continuation" in str(probability.get("most_likely", "")):
                probability_score = bullish
            elif "Bearish Breakdown" in str(probability.get("most_likely", "")):
                probability_score = 100 - bearish
            else:
                probability_score = 50
        else:
            # ProbabilityResult dataclass
            if "Bullish" in str(probability.most_likely):
                probability_score = probability.bullish_probability
            elif "Bearish" in str(probability.most_likely):
                probability_score = 100 - probability.bearish_probability
            else:
                probability_score = 50
    
    # --- Market Structure Component (15%) ---
    structure_score = 0
    market_structure = str(overview.get("market_structure", "")).lower()
    if "bullish" in market_structure:
        structure_score = 100
    elif "bearish" in market_structure:
        structure_score = 0
    elif "range" in market_structure or "sideways" in market_structure or "consolidation" in market_structure:
        structure_score = 40
    
    # --- Confluence Component (15%) ---
    confluence_score = 0
    confluence = overview.get("confluence") or overview.get("confluence_score")
    if confluence:
        if isinstance(confluence, dict):
            bullish = confluence.get("bullish") or confluence.get("Bullish", 0)
            confluence_score = float(bullish) if bullish else 50
        elif isinstance(confluence, (int, float)):
            confluence_score = float(confluence)
    
    # --- Risk/Reward Component (10%) ---
    rr_score = 50
    risk_reward = _float(overview.get("risk_reward"))
    trade_decision = overview.get("trade_decision")
    if trade_decision:
        if isinstance(trade_decision, dict):
            rr_score = int((risk_reward or 1.0) * 20) if risk_reward else 50
            rr_score = min(100, max(0, rr_score))
    
    # --- Funding Component (5%) ---
    funding_score = 50
    funding = _float(overview.get("funding_rate"))
    if funding is not None:
        if funding < 0:
            funding_score = 100  # Negative funding = potential squeeze
        elif funding < 0.0001:
            funding_score = 80
        elif funding < 0.0003:
            funding_score = 50
        else:
            funding_score = 30  # High funding = crowded
    
    # --- Open Interest Component (10%) ---
    oi_score = 50
    oi = overview.get("open_interest_usd")
    oi_change = overview.get("oi_change")
    if oi_change is not None:
        try:
            if float(oi_change) > 0:
                oi_score = 80
            else:
                oi_score = 30
        except (ValueError, TypeError):
            pass
    
    # --- Calculate weighted total ---
    score = (
        trend_score * weightings["trend"] +
        probability_score * weightings["probability"] +
        structure_score * weightings["structure"] +
        confluence_score * weightings["confluence"] +
        rr_score * weightings["risk_reward"] +
        funding_score * weightings["funding"] +
        oi_score * weightings["oi"]
    )
    
    return int(round(score))


# ============================================================================
# Edge Calculator
# ============================================================================

def calculate_edge(overview: dict, market_state: str) -> tuple:
    """Calculate expected edge with gain, loss, and risk-reward.
    
    Returns: (expected_gain_pct, expected_loss_pct, risk_reward_ratio, edge_classification)
    Edge classification: "Positive", "Neutral", "Negative"
    """
    
    def _float(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    
    price = _float(overview.get("price_usd"))
    ema20 = _float(overview.get("ema20"))
    ema50 = _float(overview.get("ema50"))
    high24 = _float(overview.get("high_24h_usd"))
    low24 = _float(overview.get("low_24h_usd"))
    risk_reward = _float(overview.get("risk_reward"))
    trade_decision = overview.get("trade_decision")
    
    # Get action from trade decision
    action = "WAIT"
    if trade_decision:
        if isinstance(trade_decision, dict):
            action = trade_decision.get("recommended_action", "WAIT")
        else:
            action = trade_decision.recommended_action
    
    expected_gain = None
    expected_loss = None
    
    if action in ("BUY", "BUY ON BREAKOUT", "WAIT FOR BREAKOUT"):
        # Long position
        # Entry: EMA20 or price
        entry = ema20 if ema20 is not None and ema20 < (price or 0) else price
        
        # Stop: below EMA20 or low24
        if ema20 is not None and entry is not None:
            expected_loss = (entry - ema20) / ema20 * 100 if ema20 > 0 else None
        elif low24 is not None and entry is not None:
            expected_loss = (entry - low24) / low24 * 100 if low24 > 0 else None
        else:
            expected_loss = 2.0  # Default 2% stop
        
        # Target: high24 or 2-5% above entry
        if high24 is not None and high24 > (price or 0):
            expected_gain = (high24 - entry) / entry * 100 if entry > 0 else None
        elif price is not None:
            expected_gain = 3.0  # Default 3% target
        
        if expected_gain is None:
            expected_gain = 3.0
        if expected_loss is None:
            expected_loss = 2.0
    
    elif action in ("SELL", "CAUTION — BEARISH BIAS"):
        # Short position
        # Entry: EMA20 or price
        entry = ema20 if ema20 is not None and ema20 > (price or 0) else price
        
        # Stop: above EMA20 or high24
        if ema20 is not None and entry is not None:
            expected_loss = (ema20 - entry) / entry * 100 if entry > 0 else None
        elif high24 is not None and entry is not None:
            expected_loss = (high24 - entry) / entry * 100 if entry > 0 else None
        else:
            expected_loss = 2.0
        
        # Target: low24 or 2-5% below entry
        if low24 is not None and low24 < (price or 0):
            expected_gain = (entry - low24) / entry * 100 if entry > 0 else None
        elif price is not None:
            expected_gain = 3.0
        
        if expected_gain is None:
            expected_gain = 3.0
        if expected_loss is None:
            expected_loss = 2.0
    
    else:
        # WAIT or NO TRADE - flat expectations
        expected_gain = 0.0
        expected_loss = 0.0
    
    # Calculate risk-reward
    risk_reward_ratio = None
    if expected_gain is not None and expected_loss is not None and expected_loss != 0:
        risk_reward_ratio = abs(expected_gain / expected_loss)
    
    # Determine edge classification
    if risk_reward_ratio is not None:
        if risk_reward_ratio > 1.5 and expected_gain > expected_loss:
            edge_class = "Positive"
        elif risk_reward_ratio > 1.0:
            edge_class = "Neutral"
        else:
            edge_class = "Negative"
    else:
        edge_class = "Neutral"
    
    return expected_gain, expected_loss, risk_reward_ratio, edge_class


# ============================================================================
# Warning Engine
# ============================================================================

def generate_warnings(overview: dict, market_state: str) -> List[str]:
    """Generate warnings based on market conditions."""
    warnings = []
    
    def _float(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    
    price = _float(overview.get("price_usd"))
    high24 = _float(overview.get("high_24h_usd"))
    ema20 = _float(overview.get("ema20"))
    ema50 = _float(overview.get("ema50"))
    funding = _float(overview.get("funding_rate"))
    rsi = _float(overview.get("rsi"))
    market_structure = str(overview.get("market_structure", "")).lower()
    trend_result = overview.get("trend_analysis", {})
    trend_strength = str(trend_result.get("strength", "")).lower()
    
    # Approaching resistance
    if price is not None and high24 is not None:
        distance_to_resistance = (high24 - price) / high24 * 100 if high24 > 0 else 100
        if distance_to_resistance < 2.0:
            warnings.append("Approaching 24h resistance")
    
    # Weak volume check (if available)
    # Note: volume analysis would require additional data
    
    # High funding
    if funding is not None and funding >= 0.0003:
        warnings.append("High funding rate - potential squeeze risk")
    elif funding is not None and funding >= 0.0001:
        warnings.append("Elevated funding rate")
    
    # Poor risk/reward
    risk_reward = _float(overview.get("risk_reward"))
    if risk_reward is not None and risk_reward < 1.0:
        warnings.append("Poor risk/reward ratio")
    
    # Sideways market
    if market_state == "Sideways Range" or market_structure in ["range", "sideways", "consolidation"]:
        warnings.append("Sideways market - lower trend quality")
    
    # Weak trend
    if trend_strength in ["weak", "moderate"] and market_state not in ["Accumulation", "Compression"]:
        warnings.append("Weak trend strength")
    
    # Divergence potential (RSI vs price)
    if rsi is not None:
        if rsi > 70:
            warnings.append("RSI overbought - potential divergence")
        elif rsi < 30:
            warnings.append("RSI oversold - potential divergence")
    
    # Low confidence
    probability = overview.get("probability")
    if probability:
        confidence = getattr(probability, "confidence", None)
        if confidence is not None and confidence < 50:
            warnings.append("Low market confidence")
    
    return warnings


# ============================================================================
# Confidence Breakdown
# ============================================================================

def calculate_confidence_breakdown(overview: dict, market_state: str) -> Dict[str, int]:
    """Calculate how much each component contributes to overall confidence.
    
    Returns a dictionary showing component contributions.
    """
    breakdown = {}
    
    def _float(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    
    price = _float(overview.get("price_usd"))
    ema20 = _float(overview.get("ema20"))
    ema50 = _float(overview.get("ema50"))
    rsi = _float(overview.get("rsi"))
    funding = _float(overview.get("funding_rate"))
    market_structure = str(overview.get("market_structure", "")).lower()
    trend_result = overview.get("trend_analysis", {})
    trend_trend = str(trend_result.get("trend", "")).lower()
    
    # EMA Alignment (+15 max)
    ema_score = 0
    if price is not None and ema20 is not None and ema50 is not None:
        if price > ema20 > ema50:
            ema_score = 15
        elif price < ema20 < ema50:
            ema_score = 5
        elif (price > ema20 and price > ema50) or (price < ema20 and price < ema50):
            ema_score = 10
        else:
            ema_score = 3
    breakdown["EMA Alignment"] = ema_score
    
    # MACD (+20 max) - infer from trend
    macd_score = 0
    if "strong" in trend_trend and "bullish" in trend_trend:
        macd_score = 20
    elif "bullish" in trend_trend:
        macd_score = 15
    elif "bearish" in trend_trend:
        macd_score = 5
    elif "neutral" in trend_trend:
        macd_score = 10
    breakdown["MACD"] = macd_score
    
    # RSI (+8 max)
    rsi_score = 0
    if rsi is not None:
        if 55 <= rsi <= 65:
            rsi_score = 8
        elif 50 <= rsi < 55 or 55 < rsi <= 60:
            rsi_score = 5
        elif rsi >= 70 or rsi <= 30:
            rsi_score = 3
        else:
            rsi_score = 4
    breakdown["RSI"] = rsi_score
    
    # Funding (+5 max)
    funding_score = 0
    if funding is not None:
        if funding < 0:
            funding_score = 5
        elif funding < 0.0001:
            funding_score = 4
        elif funding < 0.0003:
            funding_score = 3
        else:
            funding_score = 1
    breakdown["Funding"] = funding_score
    
    # Structure (-10 to +10)
    structure_score = 0
    if "bullish" in market_structure:
        structure_score = 10
    elif "bearish" in market_structure:
        structure_score = -5
    elif "range" in market_structure or "sideways" in market_structure:
        structure_score = -10
    breakdown["Structure"] = structure_score
    
    # Probability (+18 max)
    probability = overview.get("probability")
    prob_score = 0
    if probability:
        confidence = getattr(probability, "confidence", None)
        if confidence is not None:
            prob_score = min(18, int(confidence * 0.18))
    breakdown["Probability"] = prob_score
    
    return breakdown


# ============================================================================
# Executive Dashboard
# ============================================================================

def generate_dashboard(intelligence: MarketIntelligence) -> str:
    """Generate executive dashboard from MarketIntelligence data."""
    lines = [
        "=" * 24,
        f"ASSET:           {intelligence.asset}",
        "-" * 24,
        "",
        f"RECOMMENDATION:  {intelligence.recommendation}",
        f"CONVICTION:      {intelligence.conviction_score}/100",
        f"OPPORTUNITY:     {intelligence.opportunity_score}/100",
        f"TRADE QUALITY:   {get_trade_quality(intelligence.opportunity_score, intelligence.expected_edge)}",
        f"MARKET STATE:    {intelligence.market_state}",
        f"EXPECTED EDGE:   {intelligence.expected_edge}",
        "",
    ]
    
    # Add probability breakdown from market state
    lines.extend([
        f"BULLISH %:       {get_bullish_probability(intelligence.market_state)}%",
        f"SIDEWAYS %:      {get_sideways_probability(intelligence.market_state)}%",
        f"BEARISH %:       {get_bearish_probability(intelligence.market_state)}%",
        "",
    ])
    
    # Expected P&L
    if intelligence.expected_gain is not None:
        lines.append(f"EXPECTED GAIN:   {intelligence.expected_gain:.2f}%")
    if intelligence.expected_loss is not None:
        lines.append(f"EXPECTED LOSS:   {intelligence.expected_loss:.2f}%")
    if intelligence.risk_reward is not None:
        lines.append(f"R/R RATIO:       {intelligence.risk_reward:.2f} : 1")
    lines.append("")
    
    # Best Action
    lines.extend([
        f"BEST ACTION:     {intelligence.recommendation}",
        "",
    ])
    
    # Warnings
    if intelligence.warnings:
        lines.append("WARNINGS:")
        for warning in intelligence.warnings:
            lines.append(f"  • {warning}")
    else:
        lines.append("WARNINGS:        None")
    lines.append("")
    
    # Summary
    lines.extend([
        "=" * 24,
        "SUMMARY",
        "=" * 24,
        f"{intelligence.summary}",
        "",
    ])
    
    # Confidence Breakdown
    lines.extend([
        "CONFIDENCE BREAKDOWN:",
    ])
    total = sum(intelligence.confidence_breakdown.values())
    for component, score in intelligence.confidence_breakdown.items():
        lines.append(f"  {component}: {'+' if score >= 0 else ''}{score}")
    lines.append(f"  {'Total:':15} {total}/100")
    lines.append("")
    
    return "\n".join(lines)


def get_trade_quality(opportunity_score: int, edge: str) -> str:
    """Convert scores to star rating."""
    if opportunity_score >= 80 and edge == "Positive":
        return "★★★★★ (Excellent)"
    elif opportunity_score >= 60 and edge in ("Positive", "Neutral"):
        return "★★★★☆ (Good)"
    elif opportunity_score >= 40:
        return "★★★☆☆ (Average)"
    elif opportunity_score >= 20:
        return "★★☆☆☆ (Poor)"
    else:
        return "★☆☆☆☆ (Very Poor)"


def get_bullish_probability(market_state: str) -> int:
    """Get bullish probability based on market state."""
    bullish_states = {
        "Strong Uptrend": 85,
        "Healthy Uptrend": 75,
        "Pullback": 65,
        "Accumulation": 55,
    }
    return bullish_states.get(market_state, 30)


def get_sideways_probability(market_state: str) -> int:
    """Get sideways probability based on market state."""
    sideways_states = {
        "Compression": 80,
        "Sideways Range": 75,
        "Accumulation": 30,
        "Distribution": 30,
    }
    return sideways_states.get(market_state, 20)


def get_bearish_probability(market_state: str) -> int:
    """Get bearish probability based on market state."""
    bearish_states = {
        "Strong Downtrend": 85,
        "Weak Downtrend": 75,
        "Distribution": 65,
    }
    return bearish_states.get(market_state, 20)


# ============================================================================
# Main Intelligence Function
# ============================================================================

def generate_intelligence(overview: dict, asset: str = "") -> MarketIntelligence:
    """Generate complete market intelligence for an asset.
    
    Parameters
    ----------
    overview : dict
        Market overview from okx_service.get_market_overview()
    asset : str, optional
        Asset symbol. If empty, attempts to extract from overview.
    
    Returns
    -------
    MarketIntelligence
        Complete intelligence report
    """
    # Extract asset if not provided
    if not asset:
        asset = overview.get("symbol", "UNKNOWN")
        if isinstance(asset, str):
            asset = asset.upper()
    
    # Determine market state
    market_state = determine_market_state(overview)
    
    # Calculate opportunity score
    opportunity_score = calculate_opportunity_score(overview, market_state)
    
    # Calculate expected edge
    expected_gain, expected_loss, risk_reward, edge_class = calculate_edge(overview, market_state)
    
    # Generate warnings
    warnings = generate_warnings(overview, market_state)
    
    # Determine recommendation based on edge and opportunity
    if edge_class == "Positive" and opportunity_score >= 60:
        recommendation = "LONG"
    elif edge_class == "Negative" and opportunity_score >= 60:
        recommendation = "SHORT"
    elif opportunity_score >= 40:
        recommendation = "WAIT"
    else:
        recommendation = "NO TRADE"
    
    # Calculate conviction score (weighted average)
    conviction_score = int(
        opportunity_score * 0.4 +
        (get_bullish_probability(market_state) if recommendation == "LONG" else 
         get_bearish_probability(market_state) if recommendation == "SHORT" else 30) * 0.3 +
        (100 if edge_class == "Positive" else 50 if edge_class == "Neutral" else 20) * 0.3
    )
    
    # Calculate confidence breakdown
    confidence_breakdown = calculate_confidence_breakdown(overview, market_state)
    
    # Generate summary
    summary = generate_summary(asset, market_state, recommendation, opportunity_score, edge_class)
    
    return MarketIntelligence(
        asset=asset,
        market_state=market_state,
        conviction_score=conviction_score,
        opportunity_score=opportunity_score,
        expected_edge=edge_class,
        expected_gain=expected_gain,
        expected_loss=expected_loss,
        risk_reward=risk_reward,
        warnings=warnings,
        recommendation=recommendation,
        confidence_breakdown=confidence_breakdown,
        summary=summary,
    )


def generate_summary(asset: str, market_state: str, recommendation: str, 
                     opportunity_score: int, edge: str) -> str:
    """Generate one-sentence executive summary."""
    if recommendation == "LONG" and edge == "Positive":
        return f"{asset} shows {market_state.lower()} with strong bullish edge and {opportunity_score}/100 opportunity score."
    elif recommendation == "SHORT" and edge == "Negative":
        return f"{asset} shows {market_state.lower()} with bearish bias and {opportunity_score}/100 opportunity score."
    elif recommendation == "WAIT":
        return f"{asset} is in {market_state.lower()} - wait for clearer entry setup."
    else:
        return f"{asset} shows mixed signals in {market_state.lower()} with {opportunity_score}/100 opportunity score."

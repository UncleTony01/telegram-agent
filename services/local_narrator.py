"""Uncle Tony Local Narrator - Template-Based Report Generation.

This module generates professional trading reports using the Tactical Engine's
structured analysis, without any AI dependency. It serves as the primary
narrative engine, with AI narration being an optional enhancement.

Architecture:
    AnalysisObject → Tactical Engine → TacticalReport → Local Narrator → Text Report
    
The Local Narrator is ALWAYS used. AI narration is optional enhancement.
Users never see "AI service unavailable" - they always get a complete report.

Phase 8 - Explainable Decision Engine (XDE):
    The Local Narrator now integrates XDE components to provide transparent,
    professional trading reasoning that explains WHY decisions are made.
"""

from typing import Dict, Any, List, Optional
from utils.logger import get_logger

# Import XDE components for explainable reports
try:
    from services.explainable_decision_engine import (
        build_explainable_report,
        format_confidence_breakdown,
        format_opportunity_explanation,
        format_probability_analysis,
    )
    XDE_AVAILABLE = True
except ImportError:
    XDE_AVAILABLE = False

logger = get_logger(__name__)


# ============================================================================
# Tactical Report Object
# ============================================================================

class TacticalReport:
    """Structured report from Tactical Engine.
    
    This object contains all the analysis data needed to generate
    a complete report. The Local Narrator transforms this into
    natural language without requiring AI.
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        
        # Executive Summary
        self.market_state: str = "Unknown"
        self.bias: str = "Neutral"
        self.confidence: int = 50
        self.opportunity_score: int = 50
        self.recommendation: str = "WAIT"
        
        # Market Overview
        self.price: Optional[float] = None
        self.change_24h: Optional[float] = None
        self.volume: Optional[float] = None
        self.trend: str = "Neutral"
        
        # Technical Indicators
        self.rsi: Optional[float] = None
        self.ema20: Optional[float] = None
        self.ema50: Optional[float] = None
        self.macd_trend: str = "Neutral"
        
        # Key Levels
        self.support: Optional[float] = None
        self.resistance: Optional[float] = None
        self.stop_loss: Optional[float] = None
        self.take_profit_1: Optional[float] = None
        self.take_profit_2: Optional[float] = None
        
        # Scenarios
        self.bullish_scenario: str = ""
        self.bearish_scenario: str = ""
        self.sideways_scenario: str = ""
        
        # Trading Plan
        self.entry_type: str = "n/a"
        self.aggressive_entry: Optional[float] = None
        self.conservative_entry: Optional[float] = None
        self.risk_reward: Optional[float] = None
        
        # Risk Assessment
        self.risk_level: str = "MODERATE"
        self.warnings: List[str] = []
        self.risk_factors: List[str] = []
        
        # Derivatives
        self.funding_rate: Optional[float] = None
        self.open_interest: Optional[float] = None
        
        # Probabilities
        self.bullish_probability: int = 33
        self.bearish_probability: int = 33
        self.sideways_probability: int = 34
        self.most_likely: str = "Sideways Consolidation"
        
        # Edge Analysis
        self.expected_edge: str = "Neutral"
        self.expected_gain: Optional[float] = None
        self.expected_loss: Optional[float] = None
        
        # Reasoning
        self.reasoning: str = ""
        self.bullish_factors: List[str] = []
        self.bearish_factors: List[str] = []
        
        # Opportunity Scanner Result (Phase 5.5)
        self.opportunity_result: Optional[Any] = None


# ============================================================================
# Report Builder
# ============================================================================

def build_tactical_report(analysis) -> TacticalReport:
    """Build structured report from AnalysisObject or dict.
    
    This is the core function that extracts all data needed for
    the report. It works with both the new AnalysisObject and
    legacy dict formats.
    
    Parameters
    ----------
    analysis : AnalysisObject or dict
        Market analysis data
    
    Returns
    -------
    TacticalReport
        Structured report object
    """
    report = TacticalReport(symbol=_get_symbol(analysis))
    
    # Extract data based on input type
    if hasattr(analysis, 'market_data'):
        # AnalysisObject format
        _populate_from_analysis_object(report, analysis)
    else:
        # Legacy dict format
        _populate_from_dict(report, analysis)
    
    # Generate scenarios
    _generate_scenarios(report)
    
    return report


def _get_symbol(analysis) -> str:
    """Extract symbol from analysis object or dict."""
    if hasattr(analysis, 'symbol'):
        return analysis.symbol
    elif hasattr(analysis, 'market_data'):
        return analysis.market_data.symbol
    else:
        return analysis.get("symbol", "UNKNOWN")


def _populate_from_analysis_object(report: TacticalReport, analysis) -> None:
    """Populate report from AnalysisObject."""
    # Market data
    report.price = analysis.market_data.price
    report.change_24h = analysis.market_data.change_24h
    report.volume = analysis.market_data.volume_24h
    
    # Indicators
    report.rsi = analysis.indicators.rsi
    report.ema20 = analysis.indicators.ema20
    report.ema50 = analysis.indicators.ema50
    report.trend = analysis.indicators.trend
    report.macd_trend = analysis.indicators.macd_trend
    
    # Derivatives
    report.funding_rate = analysis.derivatives.funding_rate
    report.open_interest = analysis.derivatives.open_interest_usd
    
    # Market structure
    report.market_state = analysis.market_structure.market_state
    report.bias = analysis.decision.bias
    report.support = analysis.market_structure.nearest_support
    report.resistance = analysis.market_structure.nearest_resistance
    
    # Confluence
    report.confidence = analysis.confluence.confidence
    report.bullish_probability = analysis.decision.bullish_probability
    report.bearish_probability = analysis.decision.bearish_probability
    report.sideways_probability = analysis.decision.sideways_probability
    report.most_likely = analysis.decision.most_likely_scenario
    report.bullish_factors = analysis.confluence.bullish_factors
    report.bearish_factors = analysis.confluence.bearish_factors
    
    # Decision
    report.recommendation = analysis.decision.recommended_action
    report.opportunity_score = analysis.decision.opportunity_score
    report.aggressive_entry = analysis.decision.aggressive_entry
    report.conservative_entry = analysis.decision.conservative_entry
    report.stop_loss = analysis.decision.stop_loss
    report.take_profit_1 = analysis.decision.take_profit_1
    report.take_profit_2 = analysis.decision.take_profit_2
    report.risk_reward = analysis.decision.risk_reward_ratio
    report.expected_edge = analysis.decision.expected_edge
    report.expected_gain = analysis.decision.expected_gain
    report.expected_loss = analysis.decision.expected_loss
    report.reasoning = analysis.decision.reasoning
    report.risk_factors = analysis.decision.risk_factors
    report.risk_level = analysis.decision.risk_level
    
    # Warnings
    report.warnings = analysis.narrative.warnings if analysis.narrative.warnings else []
    
    # Opportunity Scanner Result (Phase 5.5)
    opp_result = getattr(analysis, '_opportunity_result', None)
    if opp_result is None:
        try:
            from services.opportunity_scanner import calculate_opportunity_score
            opp_result = calculate_opportunity_score(analysis)
            setattr(analysis, '_opportunity_result', opp_result)
        except Exception:
            opp_result = None
    if opp_result:
        report.opportunity_result = opp_result
        report.opportunity_score = opp_result.score


def _populate_from_dict(report: TacticalReport, overview: dict) -> None:
    """Populate report from legacy dict."""
    
    def _float(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    
    # Market data
    report.price = _float(overview.get("price_usd"))
    report.change_24h = _float(overview.get("change_24h"))
    report.volume = _float(overview.get("volume_usd"))
    
    # Indicators
    report.rsi = _float(overview.get("rsi"))
    report.ema20 = _float(overview.get("ema20"))
    report.ema50 = _float(overview.get("ema50"))
    report.trend = overview.get("trend", "Neutral")
    
    # Derivatives
    report.funding_rate = _float(overview.get("funding_rate"))
    report.open_interest = _float(overview.get("open_interest_usd"))
    
    # Market structure
    report.market_state = overview.get("market_state", "Unknown")
    report.bias = overview.get("market_bias", "Neutral")
    
    # Support/Resistance
    price = report.price
    ema20 = report.ema20
    ema50 = report.ema50
    high24 = _float(overview.get("high_24h_usd"))
    low24 = _float(overview.get("low_24h_usd"))
    
    if price:
        supports = [x for x in [ema20, ema50, low24] if x and x < price]
        resistances = [x for x in [ema20, ema50, high24] if x and x > price]
        
        if supports:
            report.support = max(supports)
        if resistances:
            report.resistance = min(resistances)
    
    # Decision
    trade_decision = overview.get("trade_decision")
    if trade_decision and hasattr(trade_decision, "recommended_action"):
        report.recommendation = trade_decision.recommended_action
        report.confidence = trade_decision.confidence
        report.aggressive_entry = trade_decision.aggressive_entry
        report.conservative_entry = trade_decision.conservative_entry
        report.stop_loss = trade_decision.stop_loss
        report.take_profit_1 = trade_decision.take_profit_1
        report.take_profit_2 = trade_decision.take_profit_2
        report.risk_reward = trade_decision.risk_reward
        report.reasoning = trade_decision.reason
    
    # Probability
    prob = overview.get("probability")
    if prob and hasattr(prob, "bullish_probability"):
        report.bullish_probability = prob.bullish_probability
        report.bearish_probability = prob.bearish_probability
        report.sideways_probability = prob.sideways_probability
        report.most_likely = prob.most_likely
        report.confidence = prob.confidence
    
    # Opportunity Scanner Result (Phase 5.5)
    opp_result = overview.get("_opportunity_result")
    if opp_result is None:
        try:
            from services.opportunity_scanner import calculate_opportunity_score
            opp_result = calculate_opportunity_score(overview)
            overview["_opportunity_result"] = opp_result
        except Exception:
            opp_result = None
    if opp_result:
        report.opportunity_result = opp_result
        report.opportunity_score = opp_result.score


def _generate_scenarios(report: TacticalReport) -> None:
    """Generate scenario descriptions."""
    # Bullish scenario
    if report.resistance:
        report.bullish_scenario = f"Break above ${report.resistance:.2f}"
        if report.take_profit_1:
            report.bullish_scenario += f" targeting ${report.take_profit_1:.2f}"
        if report.bullish_probability > 60:
            report.bullish_scenario += f" ({report.bullish_probability}% probability)"
    else:
        report.bullish_scenario = "Bullish continuation if support holds"
    
    # Bearish scenario
    if report.support:
        report.bearish_scenario = f"Break below ${report.support:.2f}"
        if report.take_profit_1:
            report.bearish_scenario += f" targeting ${report.take_profit_1:.2f}"
        if report.bearish_probability > 60:
            report.bearish_scenario += f" ({report.bearish_probability}% probability)"
    else:
        report.bearish_scenario = "Bearish breakdown if resistance holds"
    
    # Sideways scenario
    if report.support and report.resistance:
        report.sideways_scenario = f"Range between ${report.support:.2f} and ${report.resistance:.2f}"
    else:
        report.sideways_scenario = "Consolidation with no clear directional bias"


# ============================================================================
# Local Narrator - Template-Based Report Generation
# ============================================================================

def narrate_tactical_report(report: TacticalReport, analysis=None) -> str:
    """Generate complete text report from TacticalReport.
    
    This is the PRIMARY narration engine. It always produces a
    complete, professional report without requiring AI.
    
    Phase 8 - Now integrates XDE for explainable decisions.
    
    Parameters
    ----------
    report : TacticalReport
        Structured report from Tactical Engine
    analysis : AnalysisObject or dict, optional
        Original analysis data for XDE explainability
    
    Returns
    -------
    str
        Complete natural language report
    """
    logger.info(f"Generating local narrative for {report.symbol}")
    
    # Build explainable extensions if analysis is provided
    explainable = None
    if analysis and XDE_AVAILABLE:
        try:
            explainable = build_explainable_report(report, analysis)
            logger.info("XDE explainable report generated successfully")
        except Exception as e:
            logger.warning(f"XDE generation failed: {e}")
            explainable = None
    
    lines = []
    
    # Header
    lines.extend([
        "=" * 24,
        f"UNCLE TONY TACTICAL ANALYSIS: {report.symbol}",
        "=" * 24,
        "",
    ])
    
    # Executive Summary
    lines.extend(_narrate_executive_summary(report))
    
    # Market Summary (XDE Phase 8 - Professional paragraph)
    if explainable and 'market_summary' in explainable:
        lines.extend(_narrate_market_summary_xde(explainable['market_summary']))
    
    # Confidence Breakdown (XDE Phase 8 - Shows WHY)
    if explainable and 'confidence_breakdown' in explainable:
        lines.extend(_narrate_confidence_breakdown_xde(explainable['confidence_breakdown']))
    else:
        # Fallback to basic confidence display
        lines.extend(_narrate_confidence_basic(report))
    
    # Opportunity Explanation (XDE Phase 8 - Detailed)
    if explainable and 'opportunity_explanation' in explainable:
        lines.extend(_narrate_opportunity_xde(explainable['opportunity_explanation']))
    
    # Key Levels
    lines.extend(_narrate_key_levels(report))
    
    # Technical Indicators
    lines.extend(_narrate_technical_indicators(report))
    
    # Derivatives
    if report.funding_rate is not None or report.open_interest is not None:
        lines.extend(_narrate_derivatives(report))
    
    # Scenarios (XDE Phase 8 - Enhanced with triggers)
    if explainable and 'probability_analysis' in explainable:
        lines.extend(_narrate_scenarios_xde(explainable['probability_analysis']))
    else:
        lines.extend(_narrate_scenarios(report))
    
    # Trading Plan
    lines.extend(_narrate_trading_plan(report))
    
    # Recommendation Explanation (XDE Phase 8 - Explicit reasons)
    if explainable and 'recommendation_explanation' in explainable:
        lines.extend(_narrate_recommendation_xde(explainable['recommendation_explanation']))
    
    # Risk Assessment
    lines.extend(_narrate_risk_assessment(report))
    
    # Educational Insight (XDE Phase 8 - Teaching users)
    if explainable and 'educational_insight' in explainable:
        lines.extend(_narrate_educational_insight_xde(explainable['educational_insight']))
    
    # Opportunity Scanner Section (Phase 5.5)
    if report.opportunity_result:
        lines.extend(_narrate_opportunity_scanner(report.opportunity_result))
    
    # Footer
    lines.extend([
        "",
        "=" * 24,
        f"Analysis powered by Uncle Tony Tactical Engine",
        "=" * 24,
    ])
    
    return "\n".join(lines)


def _narrate_executive_summary(report: TacticalReport) -> List[str]:
    """Narrate executive summary section."""
    lines = [
        "📊 EXECUTIVE SUMMARY",
        "",
        f"Market State:     {report.market_state}",
        f"Bias:             {report.bias}",
        f"Signal:           {_get_signal_from_recommendation(report.recommendation)}",
        f"Recommendation:   {report.recommendation}",
        f"Confidence:       {report.confidence}/100",
        f"Opportunity:      {report.opportunity_score}/100",
        "",
    ]
    return lines


# ============================================================================
# XDE Narration Functions (Phase 8)
# ============================================================================

def _narrate_market_summary_xde(summary: str) -> List[str]:
    """Narrate professional market summary paragraph (XDE)."""
    lines = [
        "📝 MARKET SUMMARY",
        "",
        summary,
        "",
    ]
    return lines


def _narrate_confidence_breakdown_xde(breakdown: Dict[str, Any]) -> List[str]:
    """Narrate confidence breakdown showing positive/negative factors (XDE)."""
    lines = [
        "📊 CONFIDENCE BREAKDOWN",
        "",
    ]
    
    if breakdown.get('positive'):
        for factor in breakdown['positive']:
            lines.append(f"  + {factor}")
    
    if breakdown.get('negative'):
        for factor in breakdown['negative']:
            lines.append(f"  - {factor}")
    
    lines.append("")
    lines.append(f"Final Confidence: {breakdown['total']}/100")
    lines.append("")
    
    return lines


def _narrate_confidence_basic(report: TacticalReport) -> List[str]:
    """Fallback basic confidence display when XDE not available."""
    lines = [
        "📊 CONFIDENCE",
        "",
        f"Confidence: {report.confidence}/100",
        "",
    ]
    return lines


def _narrate_opportunity_xde(explanation: Dict[str, Any]) -> List[str]:
    """Narrate detailed opportunity explanation (XDE)."""
    lines = [
        f"🎯 OPPORTUNITY: {explanation['score']}/100",
        "",
    ]
    
    if explanation.get('positive'):
        lines.append("Positive Factors:")
        for factor in explanation['positive']:
            lines.append(f"  • {factor}")
        lines.append("")
    
    if explanation.get('negative'):
        lines.append("Negative Factors:")
        for factor in explanation['negative']:
            lines.append(f"  • {factor}")
        lines.append("")
    
    lines.append("Assessment:")
    lines.append(f"  {explanation['assessment']}")
    lines.append("")
    
    return lines


def _narrate_scenarios_xde(analysis: Dict[str, Any]) -> List[str]:
    """Narrate scenarios with trigger conditions (XDE)."""
    lines = [
        "🔮 SCENARIO ANALYSIS",
        "",
        f"Most Likely: {analysis['most_likely']}",
        "",
    ]
    
    # Bullish scenario
    bull = analysis.get('bullish', {})
    lines.append(f"📈 {bull.get('name', 'Bullish Continuation')} ({bull.get('probability', 0)}%)")
    if bull.get('requires'):
        lines.append("  Requires:")
        for req in bull['requires']:
            lines.append(f"    • {req}")
    if bull.get('expected_outcome'):
        lines.append(f"  Expected: {bull['expected_outcome']}")
    lines.append("")
    
    # Sideways scenario
    side = analysis.get('sideways', {})
    lines.append(f"➡️  {side.get('name', 'Sideways Consolidation')} ({side.get('probability', 0)}%)")
    if side.get('requires'):
        lines.append("  Requires:")
        for req in side['requires']:
            lines.append(f"    • {req}")
    if side.get('expected_outcome'):
        lines.append(f"  Expected: {side['expected_outcome']}")
    lines.append("")
    
    # Bearish scenario
    bear = analysis.get('bearish', {})
    lines.append(f"📉 {bear.get('name', 'Bearish Breakdown')} ({bear.get('probability', 0)}%)")
    if bear.get('requires'):
        lines.append("  Requires:")
        for req in bear['requires']:
            lines.append(f"    • {req}")
    if bear.get('expected_outcome'):
        lines.append(f"  Expected: {bear['expected_outcome']}")
    lines.append("")
    
    return lines


def _narrate_recommendation_xde(rec: Dict[str, Any]) -> List[str]:
    """Narrate recommendation with explicit reason (XDE)."""
    lines = [
        "💡 RECOMMENDATION EXPLANATION",
        "",
        f"Action: {rec['recommendation']}",
        "",
        "Reason:",
    ]
    
    # Split reason into lines for better readability
    reason = rec.get('reason', 'Market conditions suggest caution.')
    lines.append(f"  {reason}")
    
    if rec.get('supporting_factors'):
        lines.append("")
        lines.append("Supporting Evidence:")
        for factor in rec['supporting_factors']:
            lines.append(f"  • {factor}")
    
    lines.append("")
    
    return lines


def _narrate_educational_insight_xde(insight: str) -> List[str]:
    """Narrate educational insight section (XDE)."""
    lines = [
        "📚 WHY UNCLE TONY THINKS THIS",
        "",
    ]
    
    # Split insight into lines
    for line in insight.split('\n'):
        lines.append(line)
    
    lines.append("")
    
    return lines


def _narrate_market_overview(report: TacticalReport) -> List[str]:
    """Narrate market overview section."""
    lines = [
        "📈 MARKET OVERVIEW",
        "",
    ]
    
    if report.price:
        lines.append(f"Price:            ${report.price:,.2f}")
    if report.change_24h is not None:
        sign = "+" if report.change_24h >= 0 else ""
        lines.append(f"24h Change:       {sign}{report.change_24h:.2f}%")
    if report.volume:
        lines.append(f"24h Volume:       {_format_volume(report.volume)}")
    
    lines.append(f"Trend:            {report.trend}")
    lines.append("")
    
    return lines


def _narrate_key_levels(report: TacticalReport) -> List[str]:
    """Narrate key levels section."""
    lines = [
        "🎯 KEY LEVELS",
        "",
    ]
    
    if report.support:
        lines.append(f"Support:          ${report.support:,.2f}")
    else:
        lines.append("Support:          N/A")
    
    if report.resistance:
        lines.append(f"Resistance:       ${report.resistance:,.2f}")
    else:
        lines.append("Resistance:       N/A")
    
    if report.stop_loss:
        lines.append(f"Stop Loss:        ${report.stop_loss:,.2f}")
    
    if report.take_profit_1:
        lines.append(f"Take Profit 1:    ${report.take_profit_1:,.2f}")
    
    if report.take_profit_2:
        lines.append(f"Take Profit 2:    ${report.take_profit_2:,.2f}")
    
    lines.append("")
    
    return lines


def _narrate_technical_indicators(report: TacticalReport) -> List[str]:
    """Narrate technical indicators section."""
    lines = [
        "📉 TECHNICAL INDICATORS",
        "",
    ]
    
    if report.rsi is not None:
        rsi_desc = "Overbought" if report.rsi > 70 else "Oversold" if report.rsi < 30 else "Neutral"
        lines.append(f"RSI:              {report.rsi:.1f} ({rsi_desc})")
    
    if report.ema20:
        lines.append(f"EMA20:            ${report.ema20:,.2f}")
    
    if report.ema50:
        lines.append(f"EMA50:            ${report.ema50:,.2f}")
    
    lines.append(f"MACD Trend:       {report.macd_trend}")
    lines.append("")
    
    return lines


def _narrate_derivatives(report: TacticalReport) -> List[str]:
    """Narrate derivatives section."""
    lines = [
        "⚡ DERIVATIVES",
        "",
    ]
    
    if report.funding_rate is not None:
        funding_pct = report.funding_rate * 100
        lines.append(f"Funding Rate:     {funding_pct:.4f}%")
    
    if report.open_interest:
        lines.append(f"Open Interest:    {_format_volume(report.open_interest)}")
    
    lines.append("")
    
    return lines


def _narrate_scenarios(report: TacticalReport) -> List[str]:
    """Narrate scenarios section."""
    lines = [
        "🔮 SCENARIOS",
        "",
        f"Most Likely:      {report.most_likely}",
        "",
        f"Bullish:          {report.bullish_scenario}",
        f"Bearish:          {report.bearish_scenario}",
        f"Sideways:         {report.sideways_scenario}",
        "",
    ]
    
    return lines


def _narrate_trading_plan(report: TacticalReport) -> List[str]:
    """Narrate trading plan section."""
    # Get enhanced recommendation based on opportunity score
    enhanced_rec = _get_enhanced_recommendation(report)
    
    lines = [
        "💡 TRADING PLAN",
        "",
        f"Action:           {enhanced_rec}",
        "",
    ]
    
    if "BUY" in enhanced_rec.upper() or "LONG" in enhanced_rec.upper():
        lines.extend(_narrate_long_plan(report))
    elif "SELL" in enhanced_rec.upper() or "SHORT" in enhanced_rec.upper():
        lines.extend(_narrate_short_plan(report))
    else:
        lines.append("Strategy:         Wait for clearer setup")
        if report.support and report.resistance:
            lines.append(f"Watch for break of ${report.resistance:,.2f} or ${report.support:,.2f}")
    
    if report.risk_reward:
        lines.append(f"Risk/Reward:      {report.risk_reward:.2f}:1")
    
    if report.expected_edge != "Neutral":
        lines.append(f"Expected Edge:    {report.expected_edge}")
    
    lines.append("")
    
    return lines


def _narrate_long_plan(report: TacticalReport) -> List[str]:
    """Narrate long position plan."""
    lines = []
    
    if report.conservative_entry:
        lines.append(f"Entry:            Breakout above ${report.conservative_entry:,.2f}")
    elif report.aggressive_entry:
        lines.append(f"Entry:            ${report.aggressive_entry:,.2f} (aggressive)")
    
    if report.stop_loss:
        lines.append(f"Stop Loss:        ${report.stop_loss:,.2f}")
    
    if report.take_profit_1:
        lines.append(f"Target 1:         ${report.take_profit_1:,.2f}")
    
    if report.take_profit_2:
        lines.append(f"Target 2:         ${report.take_profit_2:,.2f}")
    
    return lines


def _narrate_short_plan(report: TacticalReport) -> List[str]:
    """Narrate short position plan."""
    lines = []
    
    if report.conservative_entry:
        lines.append(f"Entry:            Breakdown below ${report.conservative_entry:,.2f}")
    elif report.aggressive_entry:
        lines.append(f"Entry:            ${report.aggressive_entry:,.2f} (aggressive)")
    
    if report.stop_loss:
        lines.append(f"Stop Loss:        ${report.stop_loss:,.2f}")
    
    if report.take_profit_1:
        lines.append(f"Target 1:         ${report.take_profit_1:,.2f}")
    
    if report.take_profit_2:
        lines.append(f"Target 2:         ${report.take_profit_2:,.2f}")
    
    return lines


def _narrate_risk_assessment(report: TacticalReport) -> List[str]:
    """Narrate risk assessment section."""
    lines = [
        "⚠️  RISK ASSESSMENT",
        "",
        f"Risk Level:       {report.risk_level}",
    ]
    
    if report.risk_factors:
        lines.append("")
        lines.append("Risk Factors:")
        for factor in report.risk_factors:
            lines.append(f"  • {factor}")
    
    if report.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in report.warnings:
            lines.append(f"  • {warning}")
    
    if report.reasoning:
        lines.append("")
        lines.append("Reasoning:")
        lines.append(f"{report.reasoning}")
    
    lines.append("")
    
    return lines


# ============================================================================
# Helper Functions
# ============================================================================

def _get_signal_from_recommendation(recommendation: str) -> str:
    """Extract signal from recommendation."""
    rec_upper = recommendation.upper()
    if "BUY" in rec_upper:
        return "BUY"
    elif "SELL" in rec_upper:
        return "SELL"
    elif "WAIT" in rec_upper:
        return "WAIT"
    else:
        return "NO TRADE"


def _format_volume(volume: float) -> str:
    """Format volume with appropriate suffix."""
    if volume >= 1_000_000_000:
        return f"${volume / 1_000_000_000:.2f}B"
    elif volume >= 1_000_000:
        return f"${volume / 1_000_000:.2f}M"
    elif volume >= 1_000:
        return f"${volume / 1_000:.2f}K"
    else:
        return f"${volume:,.0f}"


# ============================================================================
# Opportunity Scanner Narration (Phase 5.5)
# ============================================================================

def _narrate_opportunity_scanner(opp_result) -> List[str]:
    """Narrate opportunity scanner result.
    
    Phase 5.5 - Displays the Opportunity Scanner output with
    score, classification, priority, and reasons.
    
    Parameters
    ----------
    opp_result : OpportunityResult
        Result from opportunity_scanner.calculate_opportunity_score()
    
    Returns
    -------
    List[str]
        Formatted lines for the report
    """
    lines = [
        "",
        "🎯 OPPORTUNITY",
        "",
        "Score:",
        f"{opp_result.score} / 100",
        "",
        "Classification:",
        f"{opp_result.classification}",
        "",
        "Priority:",
        f"{opp_result.priority}",
        "",
        "Confidence:",
        f"{opp_result.confidence}%",
        "",
        "Reasons",
    ]
    
    if opp_result.reasons:
        for reason in opp_result.reasons[:10]:  # Limit to 10 reasons
            clean_reason = reason.lstrip("✓•- ").strip()
            lines.append(f"✓ {clean_reason}")
    else:
        lines.append("✓ Standard market conditions")
    lines.append("")
    
    # Quality indicator based on score (Requirements 3)
    if opp_result.score > 80:
        lines.append("🔥 HIGH QUALITY SETUP")
        lines.append("")
    elif opp_result.score < 40:
        lines.append("⚠ Low-quality setup.")
        lines.append("Waiting is preferred.")
        lines.append("")
    
    return lines


def _get_enhanced_recommendation(report: TacticalReport) -> str:
    """Get enhanced recommendation based on opportunity score.
    
    Phase 5.5 - Uses Opportunity Score as a decision layer.
    
    Requirement 5:
    if score > 80 -> WATCH FOR ENTRY
    if score < 40 -> NO TRADE
    otherwise     -> WAIT
    """
    if not report.opportunity_result:
        return report.recommendation
    
    opp_score = report.opportunity_result.score
    
    if opp_score > 80:
        return "WATCH FOR ENTRY"
    elif opp_score < 40:
        return "NO TRADE"
    else:
        return "WAIT"


# ============================================================================
# Main Entry Point
# ============================================================================

def generate_local_narrative(analysis) -> str:
    """Generate complete report from analysis data.
    
    This is the main entry point for the Local Narrator.
    It always produces a complete report without AI.
    
    Parameters
    ----------
    analysis : AnalysisObject or dict
        Market analysis data
    
    Returns
    -------
    str
        Complete natural language report
    """
    # Build structured report
    report = build_tactical_report(analysis)
    
    # Generate narrative
    return narrate_tactical_report(report)

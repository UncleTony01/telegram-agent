"""Analysis Pipeline - Orchestrates data flow through all analysis engines.

This module provides a clean pipeline that processes an AnalysisObject through
all available engines in the correct order. Each engine reads from and writes
to specific sections of the AnalysisObject.

Pipeline Order:
1. Market Data Engine     - Populates market_data section
2. Technical Engine       - Reads market_data, populates indicators
3. Derivatives Engine     - Reads market_data, populates derivatives
4. Market Structure Engine - Reads market_data + indicators, populates market_structure
5. Confluence Engine      - Reads indicators + derivatives + market_structure, populates confluence
6. Decision Engine        - Reads confluence + market_structure, populates decision
7. Narrative Engine       - Reads all sections, populates narrative

Future engines can be inserted at any point in the pipeline without modifying
existing engines. They simply read the sections they need and write to their
own section.
"""

from typing import Optional, List, Callable
from utils.logger import get_logger

logger = get_logger(__name__)


class AnalysisPipeline:
    """Orchestrates analysis through all registered engines.
    
    Usage:
        pipeline = AnalysisPipeline()
        analysis = pipeline.run("BTC")
        
        # Or with custom engines
        pipeline = AnalysisPipeline()
        pipeline.register_engine(my_custom_engine, position=4)
        analysis = pipeline.run("BTC")
    """
    
    def __init__(self):
        self.engines: List[tuple] = []  # List of (position, engine_func, name)
        self._register_default_engines()
    
    def _register_default_engines(self):
        """Register the standard analysis engines in execution order."""
        # Order 0-9: Data collection
        self.register_engine(
            _market_data_engine,
            position=0,
            name="market_data"
        )
        
        # Order 10-19: Technical analysis
        self.register_engine(
            _technical_indicator_engine,
            position=10,
            name="technical_indicators"
        )
        
        self.register_engine(
            _derivatives_engine,
            position=11,
            name="derivatives"
        )
        
        # Order 20-29: Structure analysis
        self.register_engine(
            _market_structure_engine,
            position=20,
            name="market_structure"
        )
        
        # Order 30-39: Scoring and confluence
        self.register_engine(
            _confluence_engine,
            position=30,
            name="confluence"
        )
        
        # Order 40-49: Decision making
        self.register_engine(
            _decision_engine,
            position=40,
            name="decision"
        )
        
        # Order 50-59: Narrative generation
        self.register_engine(
            _narrative_engine,
            position=50,
            name="narrative"
        )
    
    def register_engine(
        self,
        engine_func: Callable,
        position: int,
        name: str
    ) -> None:
        """Register a new analysis engine.
        
        Future engines can be added at any position:
        - Position 0-9: Data collection
        - Position 10-19: Technical analysis
        - Position 20-29: Structure analysis
        - Position 30-39: Scoring/confluence
        - Position 40-49: Decision making
        - Position 50-59: Narrative generation
        - Position 60+: Custom extensions
        
        Parameters
        ----------
        engine_func : Callable
            Function that takes AnalysisObject and returns AnalysisObject
        position : int
            Execution order (lower runs first)
        name : str
            Engine name for logging
        """
        self.engines.append((position, engine_func, name))
        self.engines.sort(key=lambda x: x[0])  # Sort by position
        logger.info(f"Registered engine '{name}' at position {position}")
    
    def run(self, symbol: str, initial_data: dict = None) -> 'AnalysisObject':
        """Run the complete analysis pipeline for a symbol.
        
        Parameters
        ----------
        symbol : str
            Trading symbol (e.g., "BTC", "ETH")
        initial_data : dict, optional
            Pre-populated market data (skips data fetching)
        
        Returns
        -------
        AnalysisObject
            Complete analysis with all sections populated
        """
        from core.analysis_object import AnalysisObject
        
        # Create empty analysis object
        analysis = AnalysisObject(symbol=symbol.upper())
        
        # Pre-populate if initial data provided
        if initial_data:
            from core.analysis_object import create_analysis_from_overview
            analysis = create_analysis_from_overview(initial_data)
        
        # Run through all engines
        for position, engine_func, name in self.engines:
            try:
                logger.debug(f"Running engine: {name}")
                analysis = engine_func(analysis)
                analysis.mark_engine_used(name)
                logger.debug(f"Engine '{name}' completed successfully")
            except Exception as e:
                logger.error(f"Engine '{name}' failed: {e}")
                # Continue with remaining engines
                # Each engine should handle missing data gracefully
        
        logger.info(f"Pipeline completed for {symbol}. Engines used: {analysis.engines_used}")
        
        return analysis


# ============================================================================
# Default Engine Implementations
# ============================================================================

def _market_data_engine(analysis: 'AnalysisObject') -> 'AnalysisObject':
    """Populate market_data section from OKX.
    
    Reads: Nothing (fetches fresh data)
    Writes: analysis.market_data
    """
    try:
        from services.okx_service import get_market_overview
        
        overview = get_market_overview(analysis.symbol)
        
        # Populate market data section
        analysis.market_data.symbol = analysis.symbol
        analysis.market_data.price = overview.get("price_usd")
        analysis.market_data.change_24h = overview.get("change_24h")
        analysis.market_data.high_24h = overview.get("high_24h_usd")
        analysis.market_data.low_24h = overview.get("low_24h_usd")
        analysis.market_data.volume_24h = overview.get("volume_usd")
        analysis.market_data.bid = overview.get("bid_price")
        analysis.market_data.ask = overview.get("ask_price")
        analysis.market_data.spread = overview.get("spread")
        
        # Also populate other sections that come with market overview
        # This ensures backward compatibility
        analysis.indicators.ema20 = overview.get("ema20")
        analysis.indicators.ema50 = overview.get("ema50")
        analysis.indicators.rsi = overview.get("rsi")
        analysis.indicators.trend = overview.get("trend", "Neutral")
        
        analysis.derivatives.funding_rate = overview.get("funding_rate")
        analysis.derivatives.open_interest_usd = overview.get("open_interest_usd")
        
        # Store raw for reference
        analysis.market_data.raw = overview
        
    except Exception as e:
        logger.warning(f"Market data engine failed: {e}")
    
    return analysis


def _technical_indicator_engine(analysis: 'AnalysisObject') -> 'AnalysisObject':
    """Calculate technical indicators.
    
    Reads: analysis.market_data
    Writes: analysis.indicators
    
    Note: Most indicators are already populated by market_data_engine
    via get_market_overview(). This engine can be extended for
    additional calculations.
    """
    # Indicators already populated in market_data_engine via get_market_overview
    # This is a placeholder for additional indicator calculations
    
    # Example: Calculate additional indicators if needed
    # if analysis.indicators.rsi is not None:
    #     analysis.indicators.rsi_period = 14
    
    return analysis


def _derivatives_engine(analysis: 'AnalysisObject') -> 'AnalysisObject':
    """Process derivatives data.
    
    Reads: analysis.market_data
    Writes: analysis.derivatives
    
    Note: Most derivatives already populated by market_data_engine.
    This engine can be extended for additional derivatives analysis.
    """
    # Derivatives already populated in market_data_engine
    # Placeholder for additional derivatives processing
    
    return analysis


def _market_structure_engine(analysis: 'AnalysisObject') -> 'AnalysisObject':
    """Analyze market structure.
    
    Reads: analysis.market_data, analysis.indicators
    Writes: analysis.market_structure
    """
    try:
        from services.trend_engine import analyze_trend
        
        # Build minimal overview dict for trend engine (backward compatibility)
        overview = {
            "price_usd": analysis.market_data.price,
            "ema20": analysis.indicators.ema20,
            "ema50": analysis.indicators.ema50,
            "rsi": analysis.indicators.rsi,
            "market_structure_trend": analysis.market_structure.trend,
        }
        
        trend_result = analyze_trend(overview)
        
        # Populate market structure section
        analysis.market_structure.trend = trend_result.get("trend", "Neutral")
        analysis.market_structure.phase = _determine_phase(trend_result.get("trend", ""))
        
        # Calculate support/resistance
        price = analysis.market_data.price
        high24 = analysis.market_data.high_24h
        low24 = analysis.market_data.low_24h
        ema20 = analysis.indicators.ema20
        ema50 = analysis.indicators.ema50
        
        # Determine nearest support and resistance
        if price:
            supports = [x for x in [ema20, ema50, low24] if x and x < price]
            resistances = [x for x in [ema20, ema50, high24] if x and x > price]
            
            if supports:
                analysis.market_structure.nearest_support = max(supports)
                analysis.market_structure.support_levels = sorted(supports, reverse=True)
            
            if resistances:
                analysis.market_structure.nearest_resistance = min(resistances)
                analysis.market_structure.resistance_levels = sorted(resistances)
        
        # Market state from market intelligence engine
        try:
            from services.market_intelligence import determine_market_state
            
            # Build overview dict for market state determination
            ms_overview = {
                "price_usd": price,
                "ema20": ema20,
                "ema50": ema50,
                "rsi": analysis.indicators.rsi,
                "high_24h_usd": high24,
                "low_24h_usd": low24,
                "funding_rate": analysis.derivatives.funding_rate,
                "market_structure": analysis.market_structure.trend,
            }
            
            analysis.market_structure.market_state = determine_market_state(ms_overview)
            
        except Exception as e:
            logger.debug(f"Market state determination failed: {e}")
        
        # Store notes
        analysis.market_structure.notes = trend_result.get("reason", "")
        
    except Exception as e:
        logger.warning(f"Market structure engine failed: {e}")
    
    return analysis


def _confluence_engine(analysis: 'AnalysisObject') -> 'AnalysisObject':
    """Calculate confluence scores.
    
    Reads: analysis.indicators, analysis.derivatives, analysis.market_structure
    Writes: analysis.confluence
    """
    try:
        from services.probability_engine import calculate_market_probability
        
        # Build overview dict for probability engine
        overview = {
            "symbol": analysis.symbol,
            "price_usd": analysis.market_data.price,
            "ema20": analysis.indicators.ema20,
            "ema50": analysis.indicators.ema50,
            "rsi": analysis.indicators.rsi,
            "high_24h_usd": analysis.market_data.high_24h,
            "low_24h_usd": analysis.market_data.low_24h,
            "funding_rate": analysis.derivatives.funding_rate,
            "market_structure": analysis.market_structure.trend,
            "break_of_structure": analysis.market_structure.break_of_structure,
        }
        
        probability = calculate_market_probability(overview)
        
        # Populate confluence section
        analysis.confluence.bullish_score = probability.bullish_probability
        analysis.confluence.bearish_score = probability.bearish_probability
        analysis.confluence.neutral_score = probability.sideways_probability
        analysis.confluence.confidence = probability.confidence
        analysis.confluence.trade_quality = probability.trade_quality
        
        # Populate decision probabilities
        analysis.decision.bullish_probability = probability.bullish_probability
        analysis.decision.bearish_probability = probability.bearish_probability
        analysis.decision.sideways_probability = probability.sideways_probability
        analysis.decision.most_likely_scenario = probability.most_likely
        
        # Calculate alignment
        total = 3  # trend, rsi, structure
        aligned = 0
        
        if analysis.indicators.trend == "Bullish":
            aligned += 1
        if analysis.indicators.rsi and analysis.indicators.rsi > 55:
            aligned += 1
        if "bullish" in analysis.market_structure.trend.lower():
            aligned += 1
        
        analysis.confluence.indicators_aligned = aligned
        analysis.confluence.indicators_total = total
        analysis.confluence.alignment_percentage = (aligned / total * 100) if total > 0 else 0
        
        # Store reasoning
        analysis.confluence.reason = "\n".join(probability.reasoning)
        analysis.confluence.bullish_factors = [r for r in probability.reasoning if "bullish" in r.lower() or "above" in r.lower()]
        analysis.confluence.bearish_factors = [r for r in probability.reasoning if "bearish" in r.lower() or "below" in r.lower()]
        
    except Exception as e:
        logger.warning(f"Confluence engine failed: {e}")
    
    return analysis


def _decision_engine(analysis: 'AnalysisObject') -> 'AnalysisObject':
    """Generate trading decision.
    
    Reads: analysis.confluence, analysis.market_structure, analysis.market_data
    Writes: analysis.decision
    """
    try:
        from services.trade_decision import generate_trade_decision
        
        # Build overview dict for trade decision engine
        overview = {
            "symbol": analysis.symbol,
            "price_usd": analysis.market_data.price,
            "ema20": analysis.indicators.ema20,
            "ema50": analysis.indicators.ema50,
            "rsi": analysis.indicators.rsi,
            "funding_rate": analysis.derivatives.funding_rate,
            "open_interest_usd": analysis.derivatives.open_interest_usd,
            "high_24h_usd": analysis.market_data.high_24h,
            "low_24h_usd": analysis.market_data.low_24h,
            "market_structure": analysis.market_structure.trend,
            "confluence": {
                "bullish": analysis.confluence.bullish_score,
                "bearish": analysis.confluence.bearish_score,
            },
        }
        
        decision = generate_trade_decision(overview)
        
        # Populate decision section
        analysis.decision.signal = "BUY" if "BUY" in decision.recommended_action else "SELL" if "SELL" in decision.recommended_action else "WAIT"
        analysis.decision.bias = decision.market_bias
        analysis.decision.recommended_action = decision.recommended_action
        analysis.decision.conviction_score = decision.confidence
        analysis.decision.trade_quality = decision.trade_quality
        analysis.decision.aggressive_entry = decision.aggressive_entry
        analysis.decision.conservative_entry = decision.conservative_entry
        analysis.decision.stop_loss = decision.stop_loss
        analysis.decision.take_profit_1 = decision.take_profit_1
        analysis.decision.take_profit_2 = decision.take_profit_2
        analysis.decision.risk_reward_ratio = decision.risk_reward
        analysis.decision.reasoning = decision.reason
        
        # Calculate edge
        try:
            from services.market_intelligence import calculate_edge
            
            edge_data = calculate_edge(
                {"price_usd": analysis.market_data.price,
                 "ema20": analysis.indicators.ema20,
                 "ema50": analysis.indicators.ema50,
                 "high_24h_usd": analysis.market_data.high_24h,
                 "low_24h_usd": analysis.market_data.low_24h,
                 "risk_reward": decision.risk_reward,
                 "trade_decision": decision},
                analysis.market_structure.market_state
            )
            
            analysis.decision.expected_gain = edge_data[0]
            analysis.decision.expected_loss = edge_data[1]
            analysis.decision.risk_reward_ratio = edge_data[2]
            analysis.decision.expected_edge = edge_data[3]
            
        except Exception as e:
            logger.debug(f"Edge calculation failed: {e}")
        
        # Assess risk
        analysis.decision.risk_factors = []
        if analysis.derivatives.funding_rate and analysis.derivatives.funding_rate >= 0.0003:
            analysis.decision.risk_factors.append("High funding rate")
        if analysis.indicators.rsi and (analysis.indicators.rsi > 70 or analysis.indicators.rsi < 30):
            analysis.decision.risk_factors.append("RSI extreme")
        if analysis.confluence.confidence < 50:
            analysis.decision.risk_factors.append("Low confidence")
        
        if len(analysis.decision.risk_factors) >= 2:
            analysis.decision.risk_level = "HIGH"
        elif len(analysis.decision.risk_factors) == 1:
            analysis.decision.risk_level = "MODERATE"
        else:
            analysis.decision.risk_level = "LOW"
        
        # Opportunity score
        try:
            from services.market_intelligence import calculate_opportunity_score
            
            opp_score = calculate_opportunity_score(
                overview,
                analysis.market_structure.market_state
            )
            analysis.decision.opportunity_score = opp_score
            
        except Exception as e:
            logger.debug(f"Opportunity score calculation failed: {e}")
        
    except Exception as e:
        logger.warning(f"Decision engine failed: {e}")
    
    return analysis


def _narrative_engine(analysis: 'AnalysisObject') -> 'AnalysisObject':
    """Generate natural language narrative.
    
    Reads: All sections
    Writes: analysis.narrative
    """
    try:
        # Generate scenarios
        analysis.narrative.bullish_case = _generate_bullish_case(analysis)
        analysis.narrative.bearish_case = _generate_bearish_case(analysis)
        analysis.narrative.sideways_case = _generate_sideways_case(analysis)
        
        # Generate summary
        analysis.narrative.summary = _generate_summary(analysis)
        
        # Generate warnings
        analysis.narrative.warnings = analysis.decision.risk_factors.copy()
        
        # Additional warnings from market intelligence
        try:
            from services.market_intelligence import generate_warnings
            
            overview = {
                "price_usd": analysis.market_data.price,
                "high_24h_usd": analysis.market_data.high_24h,
                "ema20": analysis.indicators.ema20,
                "ema50": analysis.indicators.ema50,
                "rsi": analysis.indicators.rsi,
                "funding_rate": analysis.derivatives.funding_rate,
                "market_structure": analysis.market_structure.trend,
            }
            
            warnings = generate_warnings(overview, analysis.market_structure.market_state)
            analysis.narrative.warnings.extend(warnings)
            
        except Exception as e:
            logger.debug(f"Warning generation failed: {e}")
        
        # Generate full report
        analysis.narrative.full_report = _generate_full_report(analysis)
        
    except Exception as e:
        logger.warning(f"Narrative engine failed: {e}")
    
    return analysis


# ============================================================================
# Helper Functions
# ============================================================================

def _determine_phase(trend: str) -> str:
    """Determine market phase from trend."""
    trend_lower = trend.lower()
    
    if "strong bullish" in trend_lower or "strong uptrend" in trend_lower:
        return "Markup"
    elif "bullish" in trend_lower or "uptrend" in trend_lower:
        return "Markup"
    elif "recovery" in trend_lower or "pullback" in trend_lower:
        return "Reaccumulation"
    elif "strong bearish" in trend_lower or "strong downtrend" in trend_lower:
        return "Markdown"
    elif "bearish" in trend_lower or "downtrend" in trend_lower:
        return "Markdown"
    elif "distribution" in trend_lower:
        return "Distribution"
    elif "accumulation" in trend_lower:
        return "Accumulation"
    else:
        return "Consolidation"


def _generate_summary(analysis: 'AnalysisObject') -> str:
    """Generate one-sentence summary."""
    symbol = analysis.symbol
    bias = analysis.decision.bias
    action = analysis.decision.recommended_action
    confidence = analysis.decision.conviction_score
    state = analysis.market_structure.market_state
    
    if bias == "Bullish":
        return f"{symbol} shows {state.lower()} with bullish bias ({confidence}% confidence). {action}."
    elif bias == "Bearish":
        return f"{symbol} shows {state.lower()} with bearish bias ({confidence}% confidence). {action}."
    else:
        return f"{symbol} is in {state.lower()} with neutral bias ({confidence}% confidence). Wait for clearer signal."


def _generate_bullish_case(analysis: 'AnalysisObject') -> str:
    """Generate bullish scenario."""
    parts = []
    
    if analysis.market_structure.nearest_resistance:
        parts.append(f"Break above ${analysis.market_structure.nearest_resistance:.2f}")
    
    if analysis.decision.take_profit_1:
        parts.append(f"target ${analysis.decision.take_profit_1:.2f}")
    
    if analysis.confluence.bullish_score > 60:
        parts.append(f"({analysis.confluence.bullish_score}% probability)")
    
    if parts:
        return " ".join(parts)
    else:
        return "Bullish continuation if support holds"


def _generate_bearish_case(analysis: 'AnalysisObject') -> str:
    """Generate bearish scenario."""
    parts = []
    
    if analysis.market_structure.nearest_support:
        parts.append(f"Break below ${analysis.market_structure.nearest_support:.2f}")
    
    if analysis.decision.take_profit_1:
        parts.append(f"target ${analysis.decision.take_profit_1:.2f}")
    
    if analysis.confluence.bearish_score > 60:
        parts.append(f"({analysis.confluence.bearish_score}% probability)")
    
    if parts:
        return " ".join(parts)
    else:
        return "Bearish breakdown if resistance holds"


def _generate_sideways_case(analysis: 'AnalysisObject') -> str:
    """Generate sideways scenario."""
    if analysis.market_structure.nearest_support and analysis.market_structure.nearest_resistance:
        return f"Range between ${analysis.market_structure.nearest_support:.2f} and ${analysis.market_structure.nearest_resistance:.2f}"
    else:
        return "Consolidation with no clear directional bias"


def _generate_full_report(analysis: 'AnalysisObject') -> str:
    """Generate complete text report."""
    lines = [
        "=" * 60,
        f"UNCLE TONY ANALYSIS: {analysis.symbol}",
        "=" * 60,
        "",
        "📊 EXECUTIVE SUMMARY",
        "",
        f"Market State:    {analysis.market_structure.market_state}",
        f"Bias:            {analysis.decision.bias}",
        f"Signal:          {analysis.decision.signal}",
        f"Recommendation:  {analysis.decision.recommended_action}",
        f"Confidence:      {analysis.decision.conviction_score}/100",
        f"Opportunity:     {analysis.decision.opportunity_score}/100",
        "",
        "🎯 KEY LEVELS",
        "",
        f"Support:         ${analysis.market_structure.nearest_support:.2f}" if analysis.market_structure.nearest_support else "Support:         N/A",
        f"Resistance:      ${analysis.market_structure.nearest_resistance:.2f}" if analysis.market_structure.nearest_resistance else "Resistance:      N/A",
        "",
        "📈 INDICATORS",
        "",
        f"Price:           ${analysis.market_data.price:.2f}" if analysis.market_data.price else "Price:           N/A",
        f"RSI:             {analysis.indicators.rsi:.1f}" if analysis.indicators.rsi else "RSI:             N/A",
        f"EMA20:           ${analysis.indicators.ema20:.2f}" if analysis.indicators.ema20 else "EMA20:           N/A",
        f"Trend:           {analysis.indicators.trend}",
        "",
        "🔮 SCENARIOS",
        "",
        f"Bullish:   {analysis.narrative.bullish_case}",
        f"Bearish:   {analysis.narrative.bearish_case}",
        f"Sideways:  {analysis.narrative.sideways_case}",
        "",
    ]
    
    if analysis.narrative.warnings:
        lines.extend([
            "⚠️  WARNINGS",
            "",
        ])
        for warning in analysis.narrative.warnings:
            lines.append(f"  • {warning}")
        lines.append("")
    
    lines.extend([
        "=" * 60,
    ])
    
    return "\n".join(lines)


# ============================================================================
# Convenience Functions
# ============================================================================

def analyze(symbol: str) -> 'AnalysisObject':
    """Run complete analysis for a symbol.
    
    This is the main entry point for analysis. It creates a fresh
    AnalysisObject and processes it through all engines.
    
    Parameters
    ----------
    symbol : str
        Trading symbol (e.g., "BTC", "ETH")
    
    Returns
    -------
    AnalysisObject
        Complete analysis with all sections populated
    """
    pipeline = AnalysisPipeline()
    return pipeline.run(symbol)


def analyze_with_data(symbol: str, market_data: dict) -> 'AnalysisObject':
    """Run analysis with pre-fetched market data.
    
    Parameters
    ----------
    symbol : str
        Trading symbol
    market_data : dict
        Pre-fetched market data (skips data fetching step)
    
    Returns
    -------
    AnalysisObject
        Complete analysis
    """
    pipeline = AnalysisPipeline()
    return pipeline.run(symbol, initial_data=market_data)

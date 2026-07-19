"""Analysis Object - Standardized Data Container for Uncle Tony Trading AI.

This module defines the central data structure that all analysis engines use to
communicate. Instead of passing dozens of parameters between functions, every
module reads from and writes to this single standardized object.

Architecture Benefits:
- Single source of truth for all market analysis
- No missing values in fallback reports
- Easy to extend with new engines
- Clear data flow between modules
- Backward compatible with existing code

Future Extension Points:
- Liquidity Engine: Add liquidity section
- Order Block Engine: Add order_blocks section
- Fair Value Gap Engine: Add fvg section
- Wyckoff Engine: Add wyckoff section
- News Sentiment Engine: Add sentiment section
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


# ============================================================================
# Market Data Section
# ============================================================================

@dataclass
class MarketData:
    """Raw market data from exchanges.
    
    Populated by: OKX service, market data fetchers
    """
    symbol: str = ""
    timestamp: Optional[str] = None
    
    # Price data
    price: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None
    
    # 24h statistics
    change_24h: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    volume_24h: Optional[float] = None
    
    # Market cap (if available)
    market_cap: Optional[float] = None
    
    # Raw exchange data (for debugging)
    raw: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Indicators Section
# ============================================================================

@dataclass
class TechnicalIndicators:
    """Technical analysis indicators.
    
    Populated by: Technical Indicator Engine
    """
    # Moving Averages
    ema20: Optional[float] = None
    ema50: Optional[float] = None
    ema100: Optional[float] = None
    ema200: Optional[float] = None
    sma20: Optional[float] = None
    
    # Oscillators
    rsi: Optional[float] = None
    rsi_period: int = 14
    
    # MACD
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    macd_trend: str = "Neutral"  # Bullish, Bearish, Neutral
    
    # Bollinger Bands
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    
    # ATR (volatility)
    atr: Optional[float] = None
    
    # Trend indicators
    trend: str = "Neutral"  # Bullish, Bearish, Neutral
    trend_strength: str = "Weak"  # Very Strong, Strong, Moderate, Weak
    
    # Volume analysis
    volume_ratio: Optional[float] = None
    volume_strength: str = "Normal"  # Very Low, Low, Normal, High, Very High


# ============================================================================
# Derivatives Section
# ============================================================================

@dataclass
class DerivativesData:
    """Derivatives market data (funding, OI, etc.).
    
    Populated by: Derivatives Data Engine
    """
    # Funding rate
    funding_rate: Optional[float] = None
    next_funding_rate: Optional[float] = None
    funding_time: Optional[str] = None
    
    # Open Interest
    open_interest: Optional[float] = None
    open_interest_usd: Optional[float] = None
    oi_change_24h: Optional[float] = None
    
    # Liquidation data (if available)
    liquidation_long: Optional[float] = None
    liquidation_short: Optional[float] = None
    
    # Long/Short ratio
    long_short_ratio: Optional[float] = None


# ============================================================================
# Market Structure Section
# ============================================================================

@dataclass
class MarketStructure:
    """Market structure analysis (price action, swings, BOS).
    
    Populated by: Market Structure Engine
    """
    # Trend classification
    trend: str = "Neutral"  # Bullish, Bearish, Sideways
    phase: str = "Unknown"  # Markup, Markdown, Accumulation, Distribution, Reaccumulation, Redistribution
    
    # Market state (from Market Intelligence Engine)
    market_state: str = "Sideways Range"  # Strong Uptrend, Healthy Uptrend, Pullback, etc.
    
    # Swing points
    swing_high: Optional[float] = None
    swing_low: Optional[float] = None
    recent_high: Optional[float] = None
    recent_low: Optional[float] = None
    
    # Structure breaks
    break_of_structure: Optional[str] = None  # Bullish BOS, Bearish BOS, None
    bos_level: Optional[float] = None
    
    # Higher highs/lows tracking
    higher_high: bool = False
    higher_low: bool = False
    lower_high: bool = False
    lower_low: bool = False
    
    # Support and Resistance
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)
    nearest_support: Optional[float] = None
    nearest_resistance: Optional[float] = None
    
    # Range analysis
    in_range: bool = False
    range_high: Optional[float] = None
    range_low: Optional[float] = None
    range_position: Optional[float] = None  # 0-1, position within range
    
    # Structure notes
    notes: str = ""


# ============================================================================
# Confluence Section
# ============================================================================

@dataclass
class ConfluenceData:
    """Confluence scoring and analysis.
    
    Populated by: Confluence Engine
    """
    # Scores
    bullish_score: float = 0.0
    bearish_score: float = 0.0
    neutral_score: float = 0.0
    
    # Confidence
    confidence: int = 50  # 0-100
    trade_quality: int = 3  # 1-5 stars
    
    # Alignment
    indicators_aligned: int = 0
    indicators_total: int = 0
    alignment_percentage: float = 0.0
    
    # Contributing factors
    bullish_factors: List[str] = field(default_factory=list)
    bearish_factors: List[str] = field(default_factory=list)
    neutral_factors: List[str] = field(default_factory=list)
    
    # Reason
    reason: str = ""
    
    # Detailed breakdown
    breakdown: Dict[str, int] = field(default_factory=dict)


# ============================================================================
# Decision Section
# ============================================================================

@dataclass
class DecisionData:
    """Trading decision and recommendation.
    
    Populated by: Decision Engine, Probability Engine
    """
    # Primary signal
    signal: str = "WAIT"  # BUY, SELL, WAIT, NO TRADE
    bias: str = "Neutral"  # Bullish, Bearish, Neutral
    
    # Risk assessment
    risk_level: str = "MODERATE"  # LOW, MODERATE, HIGH, VERY HIGH
    risk_factors: List[str] = field(default_factory=list)
    
    # Probabilities
    bullish_probability: int = 33
    bearish_probability: int = 33
    sideways_probability: int = 34
    most_likely_scenario: str = "Sideways Consolidation"
    
    # Trade parameters
    recommended_action: str = "WAIT"
    entry_type: str = "n/a"  # Aggressive, Conservative
    aggressive_entry: Optional[float] = None
    conservative_entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    
    # Edge analysis
    expected_edge: str = "Neutral"  # Positive, Neutral, Negative
    expected_gain: Optional[float] = None  # Percentage
    expected_loss: Optional[float] = None  # Percentage
    
    # Conviction
    conviction_score: int = 50  # 0-100
    opportunity_score: int = 50  # 0-100
    
    # Reason
    reasoning: str = ""


# ============================================================================
# Narrative Section
# ============================================================================

@dataclass
class NarrativeData:
    """Natural language narrative and explanations.
    
    Populated by: Narrative Engine
    """
    # Executive summary
    summary: str = ""
    
    # Scenarios
    bullish_case: str = ""
    bearish_case: str = ""
    sideways_case: str = ""
    
    # Warnings
    warnings: List[str] = field(default_factory=list)
    
    # Full report
    full_report: str = ""
    
    # Hermes AI enhancement (optional)
    ai_analysis: str = ""
    used_ai: bool = False


# ============================================================================
# Main Analysis Object
# ============================================================================

@dataclass
class AnalysisObject:
    """Central data container for all market analysis.
    
    This is the single object that all analysis modules read from and write to.
    Each module is responsible for updating only its own section.
    
    Data Flow:
    1. Market Data Engine → populates market_data
    2. Technical Indicator Engine → reads market_data, populates indicators
    3. Derivatives Engine → reads market_data, populates derivatives
    4. Market Structure Engine → reads market_data + indicators, populates market_structure
    5. Confluence Engine → reads indicators + derivatives + market_structure, populates confluence
    6. Decision Engine → reads confluence + market_structure, populates decision
    7. Narrative Engine → reads all sections, populates narrative
    
    Future Extension Example:
    - Liquidity Engine → reads market_data + market_structure, populates analysis.liquidity
    - Order Block Engine → reads market_structure, populates analysis.order_blocks
    - News Sentiment Engine → populates analysis.sentiment
    
    Usage:
        analysis = AnalysisObject(symbol="BTC")
        analysis = populate_market_data(analysis, market_dict)
        analysis = calculate_indicators(analysis)
        analysis = analyze_structure(analysis)
        analysis = calculate_confluence(analysis)
        analysis = generate_decision(analysis)
        analysis = build_narrative(analysis)
    """
    # Identity
    symbol: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Data sections (each module updates its own section)
    market_data: MarketData = field(default_factory=MarketData)
    indicators: TechnicalIndicators = field(default_factory=TechnicalIndicators)
    derivatives: DerivativesData = field(default_factory=DerivativesData)
    market_structure: MarketStructure = field(default_factory=MarketStructure)
    confluence: ConfluenceData = field(default_factory=ConfluenceData)
    decision: DecisionData = field(default_factory=DecisionData)
    narrative: NarrativeData = field(default_factory=NarrativeData)
    
    # Metadata
    analysis_version: str = "1.0.0"
    engines_used: List[str] = field(default_factory=list)
    
    # Extension points for future engines
    # These can be added without modifying existing modules:
    # liquidity: Optional[LiquidityData] = None
    # order_blocks: Optional[OrderBlockData] = None
    # fair_value_gaps: Optional[FVGData] = None
    # wyckoff: Optional[WyckoffData] = None
    # sentiment: Optional[SentimentData] = None
    
    def mark_engine_used(self, engine_name: str) -> None:
        """Track which engines have processed this analysis."""
        if engine_name not in self.engines_used:
            self.engines_used.append(engine_name)
    
    def is_complete(self) -> bool:
        """Check if all required sections have been populated."""
        return len(self.engines_used) >= 4  # At least market_data, indicators, structure, decision
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization or debugging."""
        from dataclasses import asdict
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisObject':
        """Create AnalysisObject from dictionary."""
        obj = cls(symbol=data.get("symbol", ""))
        
        # Populate sections if present
        if "market_data" in data:
            obj.market_data = MarketData(**data["market_data"])
        if "indicators" in data:
            obj.indicators = TechnicalIndicators(**data["indicators"])
        if "derivatives" in data:
            obj.derivatives = DerivativesData(**data["derivatives"])
        if "market_structure" in data:
            obj.market_structure = MarketStructure(**data["market_structure"])
        if "confluence" in data:
            obj.confluence = ConfluenceData(**data["confluence"])
        if "decision" in data:
            obj.decision = DecisionData(**data["decision"])
        if "narrative" in data:
            obj.narrative = NarrativeData(**data["narrative"])
        
        return obj


# ============================================================================
# Helper Functions for Backward Compatibility
# ============================================================================

def create_analysis_from_overview(overview: Dict[str, Any]) -> AnalysisObject:
    """Create AnalysisObject from legacy market overview dict.
    
    This provides backward compatibility with existing code that uses
    the old dictionary-based approach.
    
    Parameters
    ----------
    overview : dict
        Legacy market overview from okx_service.get_market_overview()
    
    Returns
    -------
    AnalysisObject
        New standardized analysis object
    """
    symbol = overview.get("symbol", "")
    analysis = AnalysisObject(symbol=symbol)
    
    # Populate market_data
    analysis.market_data.symbol = symbol
    analysis.market_data.price = overview.get("price_usd")
    analysis.market_data.change_24h = overview.get("change_24h")
    analysis.market_data.high_24h = overview.get("high_24h_usd")
    analysis.market_data.low_24h = overview.get("low_24h_usd")
    analysis.market_data.volume_24h = overview.get("volume_usd")
    analysis.market_data.bid = overview.get("bid_price")
    analysis.market_data.ask = overview.get("ask_price")
    analysis.market_data.spread = overview.get("spread")
    analysis.market_data.market_cap = overview.get("market_cap_usd")
    
    # Populate indicators
    analysis.indicators.ema20 = overview.get("ema20")
    analysis.indicators.ema50 = overview.get("ema50")
    analysis.indicators.rsi = overview.get("rsi")
    analysis.indicators.trend = overview.get("trend", "Neutral")
    
    # Populate derivatives
    analysis.derivatives.funding_rate = overview.get("funding_rate")
    analysis.derivatives.open_interest_usd = overview.get("open_interest_usd")
    
    # Populate market_structure if available
    ms = overview.get("market_structure")
    if ms:
        analysis.market_structure.trend = str(ms).lower()
    
    # Populate confluence if available
    conf = overview.get("confluence")
    if conf:
        if isinstance(conf, dict):
            analysis.confluence.bullish_score = conf.get("bullish", conf.get("Bullish", 0))
            analysis.confluence.bearish_score = conf.get("bearish", conf.get("Bearish", 0))
    
    # Populate decision if available
    trade_decision = overview.get("trade_decision")
    if trade_decision:
        if hasattr(trade_decision, "recommended_action"):
            analysis.decision.recommended_action = trade_decision.recommended_action
            analysis.decision.bias = trade_decision.market_bias
            analysis.decision.signal = "BUY" if "BUY" in trade_decision.recommended_action else "SELL" if "SELL" in trade_decision.recommended_action else "WAIT"
            analysis.decision.stop_loss = trade_decision.stop_loss
            analysis.decision.take_profit_1 = trade_decision.take_profit_1
            analysis.decision.take_profit_2 = trade_decision.take_profit_2
            analysis.decision.risk_reward_ratio = trade_decision.risk_reward
            analysis.decision.reasoning = trade_decision.reason
            analysis.decision.conviction_score = trade_decision.confidence
            analysis.decision.trade_quality = trade_decision.trade_quality
    
    # Populate probability if available
    prob = overview.get("probability")
    if prob:
        if hasattr(prob, "bullish_probability"):
            analysis.decision.bullish_probability = prob.bullish_probability
            analysis.decision.bearish_probability = prob.bearish_probability
            analysis.decision.sideways_probability = prob.sideways_probability
            analysis.decision.most_likely_scenario = prob.most_likely
            analysis.decision.confidence = prob.confidence
    
    analysis.mark_engine_used("legacy_adapter")
    
    return analysis


def overview_from_analysis(analysis: AnalysisObject) -> Dict[str, Any]:
    """Convert AnalysisObject back to legacy overview dict.
    
    Provides backward compatibility for code expecting the old format.
    
    Parameters
    ----------
    analysis : AnalysisObject
        Standardized analysis object
    
    Returns
    -------
    dict
        Legacy market overview dictionary
    """
    overview = {
        "symbol": analysis.symbol,
        
        # Market data
        "price_usd": analysis.market_data.price,
        "change_24h": analysis.market_data.change_24h,
        "high_24h_usd": analysis.market_data.high_24h,
        "low_24h_usd": analysis.market_data.low_24h,
        "volume_usd": analysis.market_data.volume_24h,
        "bid_price": analysis.market_data.bid,
        "ask_price": analysis.market_data.ask,
        "spread": analysis.market_data.spread,
        
        # Indicators
        "ema20": analysis.indicators.ema20,
        "ema50": analysis.indicators.ema50,
        "rsi": analysis.indicators.rsi,
        "trend": analysis.indicators.trend,
        
        # Derivatives
        "funding_rate": analysis.derivatives.funding_rate,
        "open_interest_usd": analysis.derivatives.open_interest_usd,
        
        # Market structure
        "market_structure": analysis.market_structure.trend,
        "break_of_structure": analysis.market_structure.break_of_structure,
        
        # Confluence
        "confluence": {
            "bullish": analysis.confluence.bullish_score,
            "bearish": analysis.confluence.bearish_score,
        },
        
        # Decision
        "recommended_action": analysis.decision.recommended_action,
        "market_bias": analysis.decision.bias,
        "confidence": analysis.decision.conviction_score,
        
        # Analysis object reference
        "_analysis_object": analysis,
    }
    
    return overview

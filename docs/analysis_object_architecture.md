# AnalysisObject Architecture - Unified Data Flow

## Overview

The `AnalysisObject` is a standardized data container that all analysis modules communicate through. Instead of passing dozens of independent parameters between functions, every module reads from and writes to this single object.

This architecture solves:
- **Missing values** in fallback reports
- **Difficult maintenance** with scattered parameters
- **Hard-to-track data flow** between modules
- **Difficult extension** for new engines

---

## Architecture

### Data Sections

The `AnalysisObject` contains logical sections, each populated by a specific engine:

```python
AnalysisObject
├── market_data        # Raw market data (price, volume, bid/ask)
├── indicators         # Technical indicators (RSI, EMA, MACD)
├── derivatives        # Derivatives data (funding, OI)
├── market_structure   # Structure analysis (trend, support/resistance, BOS)
├── confluence         # Scoring and alignment (bullish/bearish scores)
├── decision           # Trading decision (signal, entry, stop, target)
└── narrative          # Natural language (summary, scenarios, warnings)
```

### Data Flow

Each engine reads specific sections and writes to its own section:

```
┌─────────────────────┐
│   Market Data       │  → writes to: market_data
│     Engine          │
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│  Technical Engine   │  reads: market_data
│                     │  writes: indicators
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│  Derivatives Engine │  reads: market_data
│                     │  writes: derivatives
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│  Market Structure   │  reads: market_data, indicators
│     Engine          │  writes: market_structure
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│ Confluence Engine   │  reads: indicators, derivatives, market_structure
│                     │  writes: confluence
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│  Decision Engine    │  reads: confluence, market_structure
│                     │  writes: decision
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│  Narrative Engine   │  reads: ALL sections
│                     │  writes: narrative
└─────────────────────┘
```

---

## Implementation

### Creating an AnalysisObject

```python
from core.analysis_object import AnalysisObject

# Create empty object
analysis = AnalysisObject(symbol="BTC")

# Or create from legacy dict (backward compatible)
from core.analysis_object import create_analysis_from_overview
analysis = create_analysis_from_overview(market_overview_dict)
```

### Using the Pipeline

```python
from core.analysis_pipeline import analyze

# Run complete analysis
analysis = analyze("BTC")

# Access results
print(analysis.decision.signal)          # "BUY"
print(analysis.market_structure.trend)   # "Bullish"
print(analysis.indicators.rsi)           # 62.5
```

### Updating a Section

Each engine only updates its own section:

```python
def my_custom_engine(analysis: AnalysisObject) -> AnalysisObject:
    """Custom engine that adds liquidity analysis."""
    
    # Read from other sections
    price = analysis.market_data.price
    volume = analysis.market_data.volume_24h
    
    # Write to your own section (e.g., liquidity)
    # analysis.liquidity.score = calculate_liquidity(price, volume)
    
    return analysis
```

---

## Extending the Architecture

### Adding a New Engine

Future engines can plug into the pipeline without modifying existing modules:

#### Step 1: Define Your Data Section

```python
# In core/analysis_object.py

@dataclass
class LiquidityData:
    """Liquidity analysis data."""
    score: float = 0.0
    zones: List[float] = field(default_factory=list)
    sweep_probability: float = 0.0
```

#### Step 2: Add to AnalysisObject

```python
@dataclass
class AnalysisObject:
    # ... existing sections ...
    
    # Extension points
    liquidity: Optional[LiquidityData] = None
```

#### Step 3: Create Your Engine

```python
# services/liquidity_engine.py

def analyze_liquidity(analysis: AnalysisObject) -> AnalysisObject:
    """Liquidity analysis engine.
    
    Reads: analysis.market_data, analysis.market_structure
    Writes: analysis.liquidity
    """
    if analysis.liquidity is None:
        analysis.liquidity = LiquidityData()
    
    # Read from other sections
    price = analysis.market_data.price
    high = analysis.market_data.high_24h
    low = analysis.market_data.low_24h
    
    # Calculate liquidity
    analysis.liquidity.score = calculate_liquidity_score(price, high, low)
    analysis.liquidity.zones = find_liquidity_zones(price, high, low)
    
    return analysis
```

#### Step 4: Register in Pipeline

```python
from core.analysis_pipeline import AnalysisPipeline

pipeline = AnalysisPipeline()
pipeline.register_engine(
    analyze_liquidity,
    position=25,  # After market structure (20-29), before confluence (30-39)
    name="liquidity"
)
```

### Extension Position Guide

| Position Range | Purpose | Examples |
|---------------|---------|----------|
| 0-9 | Data collection | Market data, orderbook |
| 10-19 | Technical analysis | RSI, MACD, Bollinger |
| 20-29 | Structure analysis | Market structure, swing points, order blocks |
| 30-39 | Scoring | Confluence, probability |
| 40-49 | Decision making | Trade decision, risk assessment |
| 50-59 | Narrative | Text generation, formatting |
| 60+ | Custom extensions | News sentiment, Wyckoff, FVG |

---

## Future Engine Examples

### Liquidity Engine

```python
@dataclass
class LiquidityData:
    score: float = 0.0
    zones: List[Dict[str, Any]] = field(default_factory=list)
    sweep_probability: float = 0.0

def liquidity_engine(analysis: AnalysisObject) -> AnalysisObject:
    """Detect liquidity zones and sweep probability."""
    analysis.liquidity = LiquidityData()
    
    # Find equal highs/lows (liquidity pools)
    # Calculate sweep probability
    # Identify buy-side and sell-side liquidity
    
    return analysis
```

### Order Block Engine

```python
@dataclass
class OrderBlockData:
    bullish_blocks: List[Dict[str, Any]] = field(default_factory=list)
    bearish_blocks: List[Dict[str, Any]] = field(default_factory=list)
    nearest_bullish: Optional[Dict[str, Any]] = None
    nearest_bearish: Optional[Dict[str, Any]] = None

def order_block_engine(analysis: AnalysisObject) -> AnalysisObject:
    """Identify institutional order blocks."""
    analysis.order_blocks = OrderBlockData()
    
    # Find bullish order blocks (last down candle before impulse up)
    # Find bearish order blocks (last up candle before impulse down)
    
    return analysis
```

### Fair Value Gap Engine

```python
@dataclass
class FVGData:
    bullish_gaps: List[Dict[str, Any]] = field(default_factory=list)
    bearish_gaps: List[Dict[str, Any]] = field(default_factory=list)
    unfilled_gaps: int = 0

def fvg_engine(analysis: AnalysisObject) -> AnalysisObject:
    """Identify fair value gaps (imbalances)."""
    analysis.fair_value_gaps = FVGData()
    
    # Find bullish FVGs (gap between candle 1 high and candle 3 low)
    # Find bearish FVGs (gap between candle 1 low and candle 3 high)
    
    return analysis
```

### Wyckoff Engine

```python
@dataclass
class WyckoffData:
    phase: str = "Unknown"  # Accumulation, Markup, Distribution, Markdown
    ps: Optional[str] = None  # Preliminary Support
    sc: Optional[str] = None  # Selling Climax
    ar: Optional[str] = None  # Automatic Rally
    st: Optional[str] = None  # Secondary Test
    sos: Optional[str] = None  # Sign of Strength
    lps: Optional[str] = None  # Last Point Support

def wyckoff_engine(analysis: AnalysisObject) -> AnalysisObject:
    """Wyckoff market analysis."""
    analysis.wyckoff = WyckoffData()
    
    # Identify accumulation/distribution phases
    # Mark key Wyckoff events
    
    return analysis
```

### News Sentiment Engine

```python
@dataclass
class SentimentData:
    overall_score: float = 0.0  # -1 to +1
    news_count: int = 0
    trending_topics: List[str] = field(default_factory=list)
    impact_assessment: str = "Neutral"

def sentiment_engine(analysis: AnalysisObject) -> AnalysisObject:
    """Analyze news sentiment for the asset."""
    analysis.sentiment = SentimentData()
    
    # Fetch recent news
    # Calculate sentiment score
    # Identify trending topics
    
    return analysis
```

---

## Backward Compatibility

The architecture maintains backward compatibility with existing code:

### Legacy Dict Support

```python
# Old code still works
from services.okx_service import get_market_overview
overview = get_market_overview("BTC")

# Can convert to AnalysisObject
from core.analysis_object import create_analysis_from_overview
analysis = create_analysis_from_overview(overview)

# Can convert back to dict
from core.analysis_object import overview_from_analysis
legacy_dict = overview_from_analysis(analysis)
```

### Function Signature Compatibility

All existing functions that accept `overview: dict` now also accept `AnalysisObject`:

```python
# Both work:
analyze_market_tactically(overview_dict)
analyze_market_tactically(analysis_object)
```

---

## Benefits

### 1. Single Source of Truth

All modules work from the same data structure:

```python
# Instead of:
def calculate_something(price, ema20, ema50, rsi, macd, funding, oi, ...):
    pass

# Now:
def calculate_something(analysis: AnalysisObject):
    price = analysis.market_data.price
    ema20 = analysis.indicators.ema20
    # Everything is in one place
```

### 2. No Missing Values

Every section is initialized with defaults:

```python
analysis = AnalysisObject()
# All sections exist, no KeyError
print(analysis.indicators.rsi)  # None (not missing)
```

### 3. Clear Data Flow

Each engine declares what it reads and writes:

```python
def confluence_engine(analysis: AnalysisObject) -> AnalysisObject:
    """Calculate confluence.
    
    Reads: analysis.indicators, analysis.market_structure
    Writes: analysis.confluence
    """
```

### 4. Easy Testing

Test each engine independently:

```python
# Create mock analysis object
analysis = AnalysisObject(symbol="BTC")
analysis.market_data.price = 45000
analysis.indicators.rsi = 65

# Test single engine
result = my_engine(analysis)
assert result.my_section.score > 0
```

### 5. Serialization

Easy to save/load analysis:

```python
# To dict
data = analysis.to_dict()

# From dict
analysis = AnalysisObject.from_dict(data)

# To JSON
import json
json_str = json.dumps(analysis.to_dict())
```

---

## Migration Guide

### Updating Existing Engines

1. **Accept AnalysisObject parameter:**

```python
# Before:
def my_function(price, ema20, rsi):
    pass

# After:
def my_function(analysis: AnalysisObject):
    price = analysis.market_data.price
    ema20 = analysis.indicators.ema20
    rsi = analysis.indicators.rsi
```

2. **Return AnalysisObject:**

```python
# Before:
def my_function(price, ema20):
    result = calculate(price, ema20)
    return result

# After:
def my_function(analysis: AnalysisObject):
    result = calculate(analysis.market_data.price, analysis.indicators.ema20)
    analysis.my_section.result = result
    return analysis
```

3. **Update only your section:**

```python
def my_engine(analysis: AnalysisObject):
    # Read from other sections
    data = analysis.market_data.price
    
    # Write only to your section
    analysis.my_section.value = process(data)
    
    return analysis
```

---

## Command Usage

### New `/analyze` Command

```bash
/analyze BTC
```

Returns analysis using the new pipeline architecture.

### Existing Commands

All existing commands (`/analysis`, `/intelligence`, `/tactical`) continue to work and will be gradually migrated to use the new architecture internally.

---

## Summary

The `AnalysisObject` architecture provides:

✅ **Unified data structure** - Single object for all modules  
✅ **Clear data flow** - Each engine reads/writes specific sections  
✅ **No missing values** - All sections initialized with defaults  
✅ **Easy extension** - New engines plug in without changing existing code  
✅ **Backward compatible** - Legacy code continues to work  
✅ **Testable** - Each engine testable in isolation  
✅ **Serializable** - Easy to save/load analysis  

**Future engines simply read the AnalysisObject, update their own section, and return the same object.**

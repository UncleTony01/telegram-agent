"""Tests for Phase 5.5 - Opportunity Scanner Integration into Tactical Engine."""

import pytest
from services.opportunity_scanner import calculate_opportunity_score, OpportunityResult
from services.tactical_engine import analyze_market_tactically, generate_tactical_analysis
from services.local_narrator import generate_local_narrative
from core.analysis_object import AnalysisObject


@pytest.fixture
def sample_high_quality_data():
    """High quality bullish market data setup (score > 80)."""
    return {
        "symbol": "BTC",
        "price_usd": 68000.0,
        "ema20": 65000.0,
        "ema50": 60000.0,
        "rsi": 62.0,
        "macd_trend": "Bullish",
        "macd_histogram": 45.0,
        "market_structure": "Bullish",
        "market_state": "Healthy Uptrend",
        "funding_rate": 0.0001,
        "open_interest_usd": 1500000000.0,
        "oi_change_24h": 6.5,
        "change_24h": 4.2,
        "high_24h_usd": 69000.0,
        "low_24h_usd": 64500.0,
        "nearest_resistance": 70000.0,
        "nearest_support": 65000.0,
        "risk_reward": 3.0,
    }


@pytest.fixture
def sample_low_quality_data():
    """Low quality market data setup (score < 40)."""
    return {
        "symbol": "ETH",
        "price_usd": 2200.0,
        "ema20": 2400.0,
        "ema50": 2600.0,
        "rsi": 32.0,
        "macd_trend": "Bearish",
        "macd_histogram": -75.0,
        "market_structure": "Bearish",
        "market_state": "Weak Downtrend",
        "funding_rate": 0.0004,  # High funding rate penalty
        "open_interest_usd": 400000000.0,
        "oi_change_24h": -8.0,
        "change_24h": -5.5,
        "high_24h_usd": 2350.0,
        "low_24h_usd": 2180.0,
        "nearest_resistance": 2400.0,
        "nearest_support": 2100.0,
        "risk_reward": 0.8,
    }


def test_calculate_opportunity_score_uses_existing_data(sample_high_quality_data):
    """Req 1: Opportunity Scanner accepts complete market data object directly."""
    result = calculate_opportunity_score(sample_high_quality_data)
    assert isinstance(result, OpportunityResult)
    assert result.symbol == "BTC"
    assert result.score > 0
    assert len(result.reasons) > 0


def test_tactical_engine_integration_high_quality(sample_high_quality_data):
    """Req 2, 3, 5: High quality setup integration tests."""
    tactical_analysis = analyze_market_tactically(sample_high_quality_data)
    
    assert "opportunity_result" in tactical_analysis
    opp_res = tactical_analysis["opportunity_result"]
    assert opp_res is not None
    assert opp_res.score > 80
    
    # Recommendation check (Req 5)
    assert tactical_analysis["recommendation"] == "WATCH FOR ENTRY"
    
    # Narrative check (Req 2 & 3)
    report_text = generate_tactical_analysis(sample_high_quality_data)
    assert "🎯 OPPORTUNITY" in report_text
    assert "Score:" in report_text
    assert "Classification:" in report_text
    assert "Priority:" in report_text
    assert "Confidence:" in report_text
    assert "Reasons" in report_text
    assert "🔥 HIGH QUALITY SETUP" in report_text


def test_tactical_engine_integration_low_quality(sample_low_quality_data):
    """Req 2, 3, 5: Low quality setup integration tests."""
    tactical_analysis = analyze_market_tactically(sample_low_quality_data)
    
    assert "opportunity_result" in tactical_analysis
    opp_res = tactical_analysis["opportunity_result"]
    assert opp_res is not None
    assert opp_res.score < 40
    
    # Recommendation check (Req 5)
    assert tactical_analysis["recommendation"] == "NO TRADE"
    
    # Narrative check (Req 2 & 3)
    report_text = generate_tactical_analysis(sample_low_quality_data)
    assert "🎯 OPPORTUNITY" in report_text
    assert "⚠ Low-quality setup." in report_text or "Low-quality setup" in report_text
    assert "Waiting is preferred." in report_text


def test_analysis_object_flow():
    """Req 1 & 6: Works seamlessly with AnalysisObject."""
    analysis = AnalysisObject(symbol="SOL")
    analysis.market_data.price = 150.0
    analysis.indicators.ema20 = 145.0
    analysis.indicators.ema50 = 140.0
    analysis.indicators.rsi = 60.0
    analysis.market_structure.trend = "Bullish"
    
    tactical_analysis = analyze_market_tactically(analysis)
    assert tactical_analysis["symbol"] == "SOL"
    assert "opportunity_result" in tactical_analysis
    assert tactical_analysis["opportunity_result"] is not None


def test_local_narrator_opportunity_formatting(sample_high_quality_data):
    """Test Local Narrator output includes Opportunity Scanner section."""
    narrative = generate_local_narrative(sample_high_quality_data)
    assert "🎯 OPPORTUNITY" in narrative
    assert "Reasons" in narrative
    assert "🔥 HIGH QUALITY SETUP" in narrative

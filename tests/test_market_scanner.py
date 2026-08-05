"""Unit tests for Phase 6.1 Automatic Market Scanner."""

import pytest
from unittest.mock import patch, MagicMock
from services.market_scanner import (
    scan_markets,
    scan_top_opportunities,
    format_scan_report,
    DEFAULT_SCAN_SYMBOLS,
)
from services.opportunity_scanner import OpportunityResult


@pytest.fixture
def mock_market_analysis():
    """Mock analysis output map for symbols."""
    def _mock_tactical_analysis(overview):
        sym = overview.get("symbol", "UNKNOWN") if isinstance(overview, dict) else getattr(overview, "symbol", "UNKNOWN")
        
        if sym == "SOL":
            opp = OpportunityResult(
                symbol="SOL", score=92, classification="Watchlist Long",
                priority="High", confidence=87, reasons=["Bullish EMA", "Strong RSI"]
            )
            return {
                "symbol": "SOL", "bias": "Bullish", "confidence": 87,
                "recommendation": "WATCH FOR ENTRY", "opportunity_result": opp, "opportunity_score": 92
            }
        elif sym == "BTC":
            opp = OpportunityResult(
                symbol="BTC", score=85, classification="Watchlist Long",
                priority="High", confidence=80, reasons=["EMA support"]
            )
            return {
                "symbol": "BTC", "bias": "Bullish", "confidence": 80,
                "recommendation": "WATCH FOR ENTRY", "opportunity_result": opp, "opportunity_score": 85
            }
        elif sym == "ETH":
            opp = OpportunityResult(
                symbol="ETH", score=65, classification="Watchlist Long",
                priority="Medium", confidence=75, reasons=["Consolidating"]
            )
            return {
                "symbol": "ETH", "bias": "Neutral", "confidence": 75,
                "recommendation": "WAIT", "opportunity_result": opp, "opportunity_score": 65
            }
        elif sym == "TRX":
            opp = OpportunityResult(
                symbol="TRX", score=30, classification="Strong Short Opportunity",
                priority="High", confidence=60, reasons=["Downtrend"]
            )
            return {
                "symbol": "TRX", "bias": "Bearish", "confidence": 60,
                "recommendation": "NO TRADE", "opportunity_result": opp, "opportunity_score": 30
            }
        else:
            opp = OpportunityResult(
                symbol=sym, score=50, classification="Neutral",
                priority="Low", confidence=50, reasons=[]
            )
            return {
                "symbol": sym, "bias": "Neutral", "confidence": 50,
                "recommendation": "WAIT", "opportunity_result": opp, "opportunity_score": 50
            }

    return _mock_tactical_analysis


@patch("services.okx_service.get_market_overview")
@patch("services.tactical_engine.analyze_market_tactically")
def test_scan_markets_basic_and_ranking(mock_tactical, mock_okx, mock_market_analysis):
    """Test that scan_markets returns properly ranked asset opportunities."""
    mock_okx.side_effect = lambda s: {"symbol": s}
    mock_tactical.side_effect = mock_market_analysis

    results = scan_markets(symbols=["TRX", "SOL", "BTC", "ETH"])

    assert len(results) == 4
    # Check ranking (descending score): SOL (92) -> BTC (85) -> ETH (65) -> TRX (30)
    assert results[0]["symbol"] == "SOL"
    assert results[0]["score"] == 92
    assert results[0]["confidence"] == 87
    assert results[0]["recommendation"] == "WATCH FOR ENTRY"
    assert results[0]["classification"] == "Watchlist Long"

    assert results[1]["symbol"] == "BTC"
    assert results[1]["score"] == 85

    assert results[2]["symbol"] == "ETH"
    assert results[2]["score"] == 65

    assert results[3]["symbol"] == "TRX"
    assert results[3]["score"] == 30
    assert results[3]["recommendation"] == "NO TRADE"


@patch("services.okx_service.get_market_overview")
@patch("services.tactical_engine.analyze_market_tactically")
def test_scan_markets_min_score_filtering(mock_tactical, mock_okx, mock_market_analysis):
    """Test min_score filter excludes low score opportunities."""
    mock_okx.side_effect = lambda s: {"symbol": s}
    mock_tactical.side_effect = mock_market_analysis

    results = scan_markets(symbols=["TRX", "SOL", "BTC", "ETH"], min_score=70)

    # Only SOL (92) and BTC (85) are >= 70
    assert len(results) == 2
    assert [r["symbol"] for r in results] == ["SOL", "BTC"]


@patch("services.okx_service.get_market_overview")
@patch("services.tactical_engine.analyze_market_tactically")
def test_scan_markets_limit_capping(mock_tactical, mock_okx, mock_market_analysis):
    """Test limit caps the max return count."""
    mock_okx.side_effect = lambda s: {"symbol": s}
    mock_tactical.side_effect = mock_market_analysis

    results = scan_markets(symbols=["TRX", "SOL", "BTC", "ETH"], limit=2)

    assert len(results) == 2
    assert results[0]["symbol"] == "SOL"
    assert results[1]["symbol"] == "BTC"


@patch("services.okx_service.get_market_overview")
@patch("services.tactical_engine.analyze_market_tactically")
def test_scan_markets_error_resilience(mock_tactical, mock_okx):
    """Test that a failure for one symbol does not stop the scan."""
    def _faulty_overview(symbol):
        if symbol == "BAD":
            raise RuntimeError("API Timeout for BAD coin")
        return {"symbol": symbol}

    mock_okx.side_effect = _faulty_overview
    mock_tactical.side_effect = lambda ov: {
        "symbol": ov["symbol"],
        "recommendation": "WAIT",
        "opportunity_result": OpportunityResult(
            symbol=ov["symbol"], score=80, classification="Watchlist Long",
            priority="High", confidence=75
        )
    }

    # "BAD" coin fails, but "BTC" and "SOL" should succeed
    results = scan_markets(symbols=["BTC", "BAD", "SOL"])

    assert len(results) == 2
    symbols_scanned = [r["symbol"] for r in results]
    assert "BAD" not in symbols_scanned
    assert "BTC" in symbols_scanned
    assert "SOL" in symbols_scanned


def test_format_scan_report():
    """Test formatting scan results into a human readable report."""
    results = [
        {
            "symbol": "SOL",
            "score": 92,
            "confidence": 87,
            "recommendation": "WATCH FOR ENTRY",
            "classification": "Watchlist Long"
        },
        {
            "symbol": "ETH",
            "score": 65,
            "confidence": 75,
            "recommendation": "WAIT",
            "classification": "Watchlist Long"
        }
    ]

    report = format_scan_report(results)
    assert "🔍 MARKET SCANNER RESULTS" in report
    assert "🔥 SOL" in report
    assert "Opportunity Score: 92 / 100" in report
    assert "Confidence:        87%" in report
    assert "Recommendation:    WATCH FOR ENTRY" in report
    assert "🎯 ETH" in report

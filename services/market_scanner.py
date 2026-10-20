"""Automatic Market Scanner for Uncle Tony Trading Bot.

This service automatically evaluates multiple market assets by orchestrating
existing analysis components (OKX Service, Tactical Engine, Opportunity Scanner)
without duplicating indicator calculations or scoring logic.

Design Principles:
- Pure orchestration layer (no duplicated indicator/scoring code)
- Graceful per-symbol error handling (one coin failure does not stop the scan)
- Sorting by Opportunity Score (descending) and Confidence (descending)
- Flexible filtering by minimum score and limit
"""

from typing import Any, Dict, List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

# Initial high-liquidity symbols for scanning
DEFAULT_SCAN_SYMBOLS = [
    "BTC", "ETH", "SOL", "BNB", "XRP",
    "DOGE", "TRX", "TON", "OKB", "HYPE"
]


def scan_markets(
    symbols: Optional[List[str]] = None,
    min_score: int = 0,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Scan multiple cryptocurrency assets and rank opportunities.

    Parameters
    ----------
    symbols : List[str], optional
        List of symbol strings to scan. Defaults to DEFAULT_SCAN_SYMBOLS.
    min_score : int, optional
        Minimum opportunity score threshold (0-100). Default is 0.
    limit : int, optional
        Maximum number of results to return. Default is None (all).

    Returns
    -------
    List[Dict[str, Any]]
        List of dictionaries containing scanned market opportunities:
        [
            {
                "symbol": "SOL",
                "score": 92,
                "confidence": 87,
                "recommendation": "WATCH FOR ENTRY",
                "classification": "Watchlist Long"
            },
            ...
        ]
    """
    from core.analysis_pipeline import analyze as run_analysis_pipeline
    from services.tactical_engine import analyze_market_tactically

    if not symbols:
        symbols = DEFAULT_SCAN_SYMBOLS

    results = []

    def _extract_from_opp(opp, field, default=None):
        """Safely extract a field from OpportunityResult which may be a dataclass or dict."""
        if opp is None:
            return default
        # dataclass / object attribute
        val = getattr(opp, field, None)
        if val is not None:
            return val
        # dict-like access
        if isinstance(opp, dict):
            return opp.get(field, default)
        return default

    for symbol in symbols:
        symbol_upper = symbol.upper()
        try:
            # 1. Build/run full AnalysisObject through the pipeline
            analysis_obj = run_analysis_pipeline(symbol_upper)

            # 2. Pass AnalysisObject through Tactical Engine (works with AnalysisObject)
            tactical_analysis = analyze_market_tactically(analysis_obj)

            # 3. Read Opportunity Result (may be attached to AnalysisObject or returned by tactical_analysis)
            opp_res = tactical_analysis.get("opportunity_result") if isinstance(tactical_analysis, dict) else None
            if opp_res is None:
                # Tactical engine may have stored it on the analysis object
                opp_res = getattr(analysis_obj, "_opportunity_result", None)

            # Extract primary fields with graceful fallbacks
            score = _extract_from_opp(opp_res, "score", tactical_analysis.get("opportunity_score") if isinstance(tactical_analysis, dict) else None) or 0
            confidence = _extract_from_opp(opp_res, "confidence", tactical_analysis.get("confidence") if isinstance(tactical_analysis, dict) else None) or 0
            classification = _extract_from_opp(opp_res, "classification", "Neutral")
            priority = _extract_from_opp(opp_res, "priority", "Low")
            reasons = _extract_from_opp(opp_res, "reasons", [])

            # Ensure numeric types
            try:
                score = int(score)
            except Exception:
                score = 0
            try:
                confidence = int(confidence)
            except Exception:
                confidence = 0

            if isinstance(tactical_analysis, dict):
                recommendation = tactical_analysis.get("recommendation", "WAIT")
            else:
                dec = getattr(analysis_obj, "decision", None)
                recommendation = getattr(dec, "recommended_action", "WAIT") if dec is not None else "WAIT"

            # 4. Filter by minimum score
            if score >= min_score:
                results.append({
                    "symbol": symbol_upper,
                    "score": score,
                    "confidence": confidence,
                    "recommendation": recommendation,
                    "classification": classification,
                    "priority": priority,
                    "reasons": reasons,
                    # keep some extra fields for richer reports/alerts
                    "price": getattr(analysis_obj.market_data, "price", None) if hasattr(analysis_obj, "market_data") else tactical_analysis.get("price"),
                    "bias": tactical_analysis.get("bias", "Neutral") if isinstance(tactical_analysis, dict) else getattr(analysis_obj.decision, "bias", "Neutral") if hasattr(analysis_obj, "decision") else "Neutral",
                })

        except Exception as e:
            # Log error and continue with remaining symbols
            logger.warning(f"Error scanning market for symbol '{symbol_upper}': {e}")
            continue

    # Sort results by score (descending), then confidence (descending)
    results.sort(key=lambda item: (item["score"], item["confidence"]), reverse=True)

    # Apply limit if specified
    if limit is not None and limit > 0:
        results = results[:limit]

    return results


def scan_top_opportunities(min_score: int = 70, limit: int = 10) -> List[Dict[str, Any]]:
    """Convenience helper to scan top high-quality opportunities.

    Parameters
    ----------
    min_score : int, optional
        Minimum opportunity score threshold. Default is 70.
    limit : int, optional
        Maximum number of top setups to return. Default is 10.

    Returns
    -------
    List[Dict[str, Any]]
        Sorted list of top opportunity dicts.
    """
    return scan_markets(symbols=DEFAULT_SCAN_SYMBOLS, min_score=min_score, limit=limit)


def format_scan_report(results: List[Dict[str, Any]]) -> str:
    """Format market scan results into a clean string summary.

    Parameters
    ----------
    results : List[Dict[str, Any]]
        List of scanned opportunity dictionaries from scan_markets().

    Returns
    -------
    str
        Formatted report suitable for terminal or Telegram message.
    """
    if not results:
        return "🔍 MARKET SCANNER RESULTS\n\nNo market opportunities found matching the criteria."

    lines = [
        "🔍 MARKET SCANNER RESULTS",
        f"Found {len(results)} opportunity/opportunities:",
        "=" * 24,
        "",
    ]

    for item in results:
        score = item["score"]
        symbol = item["symbol"]
        rec = item["recommendation"]
        classification = item["classification"]
        confidence = item["confidence"]

        if score > 80:
            badge = "🔥"
        elif score >= 65:
            badge = "🎯"
        elif score < 40:
            badge = "⚠️"
        else:
            badge = "📊"

        lines.extend([
            f"{badge} {symbol}",
            f"  Opportunity Score: {score} / 100",
            f"  Confidence:        {confidence}%",
            f"  Classification:    {classification}",
            f"  Recommendation:    {rec}",
            "",
        ])

    lines.append("=" * 24)
    return "\n".join(lines)

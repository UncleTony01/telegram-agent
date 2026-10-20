#!/usr/bin/env python3
"""
Validate Market Intelligence Engine across a watchlist of symbols.

Produces a printed report for each symbol and a final validation summary.

Read-only: uses AnalysisPipeline.analyze and generate_market_intelligence only.
"""
from typing import List, Dict
import statistics

from core.analysis_pipeline import analyze
from services.market_intelligence_engine import generate_market_intelligence
from core.analysis_object import AnalysisObject

WATCHLIST = [
    "BTC",
    "ETH",
    "SOL",
    "BNB",
    "XRP",
    "DOGE",
    "TON",
    "LINK",
    "AVAX",
    "SUI",
]


def _trend_score(analysis: AnalysisObject) -> int:
    s = 50
    try:
        ts = (analysis.indicators.trend_strength or "").lower()
        if "very" in ts:
            s = 90
        elif "strong" in ts:
            s = 75
        elif "moderate" in ts or "moder" in ts:
            s = 55
        elif "weak" in ts:
            s = 25
        else:
            s = 50
        # slight boost if market structure shows higher highs
        if getattr(analysis.market_structure, "higher_high", False):
            s = min(100, s + 10)
    except Exception:
        s = 50
    return int(s)


def _momentum_score(analysis: AnalysisObject) -> int:
    s = 50
    try:
        rsi = analysis.indicators.rsi
        macd_trend = (analysis.indicators.macd_trend or "").lower()
        if rsi is not None:
            if rsi >= 75:
                s = 90
            elif rsi >= 65:
                s = 75
            elif rsi >= 55:
                s = 60
            elif rsi >= 45:
                s = 50
            elif rsi >= 35:
                s = 40
            else:
                s = 25
        if macd_trend == "bullish":
            s = min(100, s + 10)
        elif macd_trend == "bearish":
            s = max(0, s - 10)
    except Exception:
        s = 50
    return int(s)


def _participation_score(analysis: AnalysisObject) -> int:
    s = 50
    try:
        vs = (analysis.indicators.volume_strength or "").lower()
        if "very high" in vs or "veryhigh" in vs or "very-high" in vs:
            s = 90
        elif "high" in vs:
            s = 75
        elif "low" in vs:
            s = 30
        else:
            s = 50
        # open interest change provides additional signal
        oi_change = analysis.derivatives.oi_change_24h
        if oi_change is not None:
            if oi_change > 1:
                s = min(100, s + 10)
            elif oi_change < -1:
                s = max(0, s - 10)
    except Exception:
        s = 50
    return int(s)


def _structure_score(analysis: AnalysisObject) -> int:
    s = 50
    try:
        ms = analysis.market_structure
        if ms.break_of_structure and (ms.higher_high or ms.higher_low):
            s = 90
        elif ms.lower_high or ms.lower_low:
            s = 20
        elif ms.in_range:
            s = 55
        else:
            s = 60
    except Exception:
        s = 50
    return int(s)


def _setup_score(analysis: AnalysisObject) -> int:
    s = 50
    try:
        opp = int(getattr(analysis.decision, "opportunity_score", 0) or 0)
        conf = int(getattr(analysis.confluence, "confidence", 0) or 0)
        trade_quality = int(getattr(analysis.confluence, "trade_quality", 3) or 3)
        # weighted: opportunity 60%, conf 30%, trade_quality(1-5) -> normalized 0-100 10%
        s = int((opp * 0.6) + (conf * 0.3) + ((trade_quality / 5.0 * 100) * 0.1))
    except Exception:
        s = 50
    return max(0, min(100, s))


def _intelligence_score(components: List[int]) -> int:
    # simple average of components
    if not components:
        return 0
    return int(sum(components) / len(components))


def _intelligence_confidence(analysis: AnalysisObject, components: Dict[str, int]) -> str:
    # Agreement between confluence.confidence, decision.opportunity_score, and structure score
    vals = []
    try:
        vals.append(int(getattr(analysis.confluence, "confidence", 0) or 0))
    except Exception:
        vals.append(0)
    try:
        vals.append(int(getattr(analysis.decision, "opportunity_score", 0) or 0))
    except Exception:
        vals.append(0)
    try:
        vals.append(int(components.get("structure_score", 50)))
    except Exception:
        vals.append(50)

    # compute stddev
    try:
        sd = statistics.pstdev(vals)
    except Exception:
        sd = 50

    if sd <= 7:
        return "Very High"
    elif sd <= 15:
        return "High"
    elif sd <= 30:
        return "Medium"
    else:
        return "Low"


def _detect_contradictions(mi, analysis: AnalysisObject) -> List[str]:
    issues = []
    # BUYERS + Bearish Summary
    summary_lower = (mi.summary or "").lower()
    if mi.market_controller == "BUYERS" and ("bear" in summary_lower or analysis.decision.bias.lower().startswith("bear")):
        issues.append("BUYERS control but summary/bias is bearish")

    # HIGH PRIORITY + IGNORE
    if mi.attention_level == "HIGH PRIORITY" and "ignore" in mi.summary.lower():
        issues.append("HIGH PRIORITY but summary suggests ignore")

    # Strong Trend + Weak Momentum + summary says accelerating
    if mi.trend_quality in ("VERY STRONG", "STRONG") and mi.momentum_quality in ("WEAKENING", "WEAK") and "accelerat" in mi.summary.lower():
        issues.append("Strong trend but weak momentum while summary says accelerating")

    # Setup high but attention ignore
    if mi.setup_quality in ("A+", "A") and mi.attention_level == "IGNORE":
        issues.append("High quality setup but attention set to IGNORE")

    return issues


def run_validation():
    results = []
    contradictions = {}
    pass_count = 0
    fail_count = 0
    intelligence_scores = []

    for sym in WATCHLIST:
        print("\n---", sym, "---")
        analysis = analyze(sym)
        mi = generate_market_intelligence(analysis)

        # compute component scores
        t_score = _trend_score(analysis)
        m_score = _momentum_score(analysis)
        p_score = _participation_score(analysis)
        s_score = _structure_score(analysis)
        setup = _setup_score(analysis)

        components = {
            "trend_score": t_score,
            "momentum_score": m_score,
            "participation_score": p_score,
            "structure_score": s_score,
            "setup_score": setup,
        }

        intelligence = _intelligence_score(list(components.values()))
        intelligence_scores.append(intelligence)

        confidence = _intelligence_confidence(analysis, components)

        # Print requested fields
        print(f"Symbol: {sym}")
        print(f"Market Controller: {mi.market_controller}")
        print(f"Market Phase: {mi.market_phase}")
        print(f"Trend Quality: {mi.trend_quality} (score {t_score})")
        print(f"Momentum Quality: {mi.momentum_quality} (score {m_score})")
        print(f"Participation Quality: {mi.participation_quality} (score {p_score})")
        print(f"Structure Quality: {mi.structure_quality} (score {s_score})")
        print(f"Setup Quality: {mi.setup_quality} (score {setup})")
        print(f"Attention Level: {mi.attention_level}")
        print(f"Summary: {mi.summary}")
        print(f"Intelligence Score: {intelligence}")
        print(f"Intelligence Confidence: {confidence}")

        # Check contradictions
        issues = _detect_contradictions(mi, analysis)
        if issues:
            print("CONTRADICTIONS:")
            for it in issues:
                print(" -", it)
            contradictions[sym] = issues
            fail_count += 1
        else:
            print("No contradictions detected.")
            pass_count += 1

        results.append({
            "symbol": sym,
            "mi": mi,
            "components": components,
            "intelligence": intelligence,
            "confidence": confidence,
            "issues": issues,
        })

    # Final report
    print("\n\n================================================\nMARKET INTELLIGENCE VALIDATION\n================================================")
    print(f"Assets Tested: {len(WATCHLIST)}")
    print(f"PASS: {pass_count}")
    print(f"FAIL: {fail_count}")
    if contradictions:
        print("\nContradictions Found:")
        for k, v in contradictions.items():
            print(f" - {k}: {v}")
    else:
        print("\nContradictions Found: None")

    # Component completeness (simple heuristic: count non-zero component scores)
    avg_components = {"trend": 0, "momentum": 0, "participation": 0, "structure": 0, "setup": 0}
    for r in results:
        avg_components["trend"] += r["components"]["trend_score"]
        avg_components["momentum"] += r["components"]["momentum_score"]
        avg_components["participation"] += r["components"]["participation_score"]
        avg_components["structure"] += r["components"]["structure_score"]
        avg_components["setup"] += r["components"]["setup_score"]

    n = len(results) or 1
    avg_components = {k: int(v / n) for k, v in avg_components.items()}

    print("\nComponent Completeness (avg scores):")
    for k, v in avg_components.items():
        print(f" - {k}: {v}")

    avg_intelligence = int(sum(intelligence_scores) / len(intelligence_scores)) if intelligence_scores else 0
    print(f"\nAverage Intelligence Score: {avg_intelligence}")


if __name__ == "__main__":
    run_validation()

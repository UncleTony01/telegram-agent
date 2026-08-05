"""Automatic Market Scanner (Credit-Efficient Mode).

Orchestration only — uses existing analysis pipeline, tactical engine and
opportunity scanner. Exposes three public functions:

- start_scanner()
- stop_scanner()
- scan_once()

The background scanner runs in a separate thread and will not block Telegram.
Alerts are sent only when Opportunity Score >= ALERT_SCORE_THRESHOLD and
duplicate alerts are suppressed during ALERT_COOLDOWN seconds.

This module intentionally keeps implementation focused on scheduling and
delivery. No indicator or scoring logic is duplicated.
"""
from __future__ import annotations

import threading
import time
import collections
from typing import Callable, Dict, List, Optional

from utils.logger import get_logger
import config

logger = get_logger(__name__)

# Defaults / configuration
WATCHLIST: List[str] = [
    "BTC",
    "ETH",
    "SOL",
    "BNB",
    "TRX",
    "TON",
    "OKB",
    "HYPE",
]

SCAN_EVERY_SECONDS = 300  # full-cycle interval
SYMBOL_DELAY_SECONDS = 1  # delay between individual symbol scans (rate limiting)
ALERT_SCORE_THRESHOLD = 80  # minimum opportunity score to alert
ALERT_COOLDOWN = 60 * 60  # seconds to suppress identical re-alert (default 1 hour)

# Internal state
_stop_event = threading.Event()
_thread: Optional[threading.Thread] = None
_last_alerts: Dict[str, Dict] = {}  # symbol -> {score, recommendation, ts}
_alert_queue = collections.deque()  # queue of pending alert dicts
_lock = threading.Lock()

# Optional alert handler override (for tests or custom integrations)
_alert_handler: Optional[Callable[[Dict], None]] = None


# ------------------------ Helpers -----------------------------------------
def _fmt_price(val: Optional[float]) -> str:
    if val is None:
        return "n/a"
    try:
        if isinstance(val, float) or isinstance(val, int):
            # show as integer if > 1, otherwise 6 decimals
            if val >= 1:
                return f"{val:,.0f}"
            return f"{val:.6f}"
    except Exception:
        pass
    return str(val)


def _enqueue_alert(alert: Dict) -> None:
    """Enqueue and dispatch alert asynchronously."""
    logger.info("Enqueuing alert for %s: score=%s", alert.get("symbol"), alert.get("score"))
    _alert_queue.append(alert)
    # Dispatch immediately in background
    t = threading.Thread(target=_dispatch_alert, args=(alert,), daemon=True)
    t.start()


def _dispatch_alert(alert: Dict) -> None:
    """Deliver alert using configured handler or Telegram (non-blocking)."""
    try:
        if _alert_handler:
            try:
                _alert_handler(alert)
                return
            except Exception as e:
                logger.warning("Custom alert handler failed: %s", e)

        # Default behaviour: send to Telegram chat if configured
        if getattr(config, "CHAT_ID", None):
            try:
                from services.telegram_service import send_message

                text_lines = ["🔥 HIGH QUALITY SETUP\n"]
                text_lines.append(alert.get("symbol", "UNKNOWN"))
                text_lines.append("")
                text_lines.append(f"Opportunity Score: {alert.get('score')}")
                text_lines.append("")
                text_lines.append(f"Confidence: {alert.get('confidence')}%")
                text_lines.append("")
                bias = alert.get("bias") or alert.get("decision_bias") or "n/a"
                text_lines.append("Bias:")
                text_lines.append(bias)
                text_lines.append("")
                text_lines.append("Recommendation:")
                text_lines.append(alert.get("recommendation", "n/a"))
                text_lines.append("")
                support = _fmt_price(alert.get("support"))
                resistance = _fmt_price(alert.get("resistance"))
                text_lines.append("Support:")
                text_lines.append(support)
                text_lines.append("")
                text_lines.append("Resistance:")
                text_lines.append(resistance)

                text = "\n".join(text_lines)

                # send in background so that network delays don't block scanner
                sender = threading.Thread(target=send_message, args=(config.CHAT_ID, text), daemon=True)
                sender.start()
                logger.info("Alert dispatched to Telegram for %s", alert.get("symbol"))
                return
            except Exception as e:
                logger.warning("Failed to send Telegram alert: %s", e)

        # Fallback: log the alert
        logger.info("ALERT: %s", alert)
    except Exception as e:
        logger.error("Error while dispatching alert: %s", e)


def _should_alert(symbol: str, score: int, recommendation: str) -> bool:
    """Determine if an alert should be sent (duplicates suppressed)."""
    now = time.time()
    with _lock:
        last = _last_alerts.get(symbol)
        if last:
            same_score = int(last.get("score", -1)) == int(score)
            same_reco = str(last.get("recommendation", "")) == str(recommendation)
            ts = last.get("ts", 0)
            if same_score and same_reco and (now - ts) < ALERT_COOLDOWN:
                return False
        # Otherwise update last_alerts and allow
        _last_alerts[symbol] = {"score": int(score), "recommendation": recommendation, "ts": now}
    return True


# ------------------------ Core scanning -----------------------------------

def scan_once(
    watchlist: Optional[List[str]] = None,
    min_score: int = ALERT_SCORE_THRESHOLD,
    symbol_delay: float = SYMBOL_DELAY_SECONDS,
) -> List[Dict]:
    """Run one scan cycle and return generated alerts (list of alert dicts).

    This function is synchronous and performs per-symbol scans with a small
    delay to respect rate limits.
    """
    if watchlist is None:
        watchlist = WATCHLIST

    alerts: List[Dict] = []

    # Import here to avoid top-level heavy imports
    from services.analysis_pipeline import analyze as run_analysis_pipeline
    from services.tactical_engine import analyze_market_tactically

    for sym in watchlist:
        symbol = sym.upper()
        try:
            # Build full AnalysisObject via pipeline (this will fetch market data)
            analysis_obj = run_analysis_pipeline(symbol)

            # Run tactical engine (re-uses opportunity scanner result attached by pipeline)
            tactical_analysis = analyze_market_tactically(analysis_obj)

            # Try to extract OpportunityResult (dataclass or dict)
            opp_res = None
            if isinstance(tactical_analysis, dict):
                opp_res = tactical_analysis.get("opportunity_result")
            if opp_res is None:
                opp_res = getattr(analysis_obj, "_opportunity_result", None)

            score = None
            confidence = None
            recommendation = None
            if opp_res is not None:
                score = getattr(opp_res, "score", None) if not isinstance(opp_res, dict) else opp_res.get("score")
                confidence = getattr(opp_res, "confidence", None) if not isinstance(opp_res, dict) else opp_res.get("confidence")
                recommendation = getattr(opp_res, "recommendation", None) if not isinstance(opp_res, dict) else opp_res.get("recommendation")
            else:
                # fallback to fields in tactical_analysis
                if isinstance(tactical_analysis, dict):
                    score = tactical_analysis.get("opportunity_score")
                    confidence = tactical_analysis.get("confidence")
                    recommendation = tactical_analysis.get("recommendation")

            try:
                score_int = int(score) if score is not None else 0
            except Exception:
                score_int = 0
            try:
                confidence_int = int(confidence) if confidence is not None else 0
            except Exception:
                confidence_int = 0

            if score_int >= min_score:
                # Gather support/resistance from analysis object when available
                support = None
                resistance = None
                try:
                    support = getattr(analysis_obj.market_structure, "nearest_support", None)
                    resistance = getattr(analysis_obj.market_structure, "nearest_resistance", None)
                except Exception:
                    # ignore missing attributes
                    pass

                reco = recommendation or (getattr(analysis_obj.decision, "recommended_action", None) if hasattr(analysis_obj, "decision") else "")

                if _should_alert(symbol, score_int, reco):
                    alert = {
                        "symbol": symbol,
                        "score": score_int,
                        "confidence": confidence_int,
                        "recommendation": reco,
                        "support": support,
                        "resistance": resistance,
                        "bias": getattr(analysis_obj.decision, "bias", None) if hasattr(analysis_obj, "decision") else None,
                    }
                    _enqueue_alert(alert)
                    alerts.append(alert)
                else:
                    logger.info("Duplicate alert suppressed for %s (score=%s)", symbol, score_int)

        except Exception as e:
            logger.warning("Scan failed for %s: %s", symbol, e)

        # Rate limit between symbols
        if symbol_delay and symbol != watchlist[-1]:
            # allow stop early
            if _stop_event.wait(symbol_delay):
                break

    return alerts


def _run_loop(
    watchlist: Optional[List[str]] = None,
    scan_every: float = SCAN_EVERY_SECONDS,
    min_score: int = ALERT_SCORE_THRESHOLD,
    symbol_delay: float = SYMBOL_DELAY_SECONDS,
):
    """Internal background loop."""
    logger.info("Auto-scanner started: interval=%s sec, symbols=%s", scan_every, len(watchlist or WATCHLIST))
    while not _stop_event.is_set():
        try:
            scan_once(watchlist=watchlist, min_score=min_score, symbol_delay=symbol_delay)
        except Exception as e:
            logger.error("Error during scan loop: %s", e)

        # Wait for next cycle but exit early if stop requested
        if _stop_event.wait(scan_every):
            break

    logger.info("Auto-scanner stopped")


# ------------------------ Public API -------------------------------------
def start_scanner(
    watchlist: Optional[List[str]] = None,
    scan_every: float = SCAN_EVERY_SECONDS,
    min_score: int = ALERT_SCORE_THRESHOLD,
    symbol_delay: float = SYMBOL_DELAY_SECONDS,
) -> None:
    """Start the background scanner. Non-blocking.

    If already running, the call is ignored.
    """
    global _thread, _stop_event
    if _thread and _thread.is_alive():
        logger.info("Scanner already running")
        return

    _stop_event.clear()
    _thread = threading.Thread(target=_run_loop, args=(watchlist, scan_every, min_score, symbol_delay), daemon=True)
    _thread.start()
    logger.info("Scanner thread started")


def stop_scanner(timeout: Optional[float] = None) -> None:
    """Stop the background scanner and wait for thread to finish (optional timeout)."""
    global _thread, _stop_event
    _stop_event.set()
    if _thread:
        _thread.join(timeout=timeout)
        if _thread.is_alive():
            logger.warning("Scanner thread did not stop within timeout")
        else:
            logger.info("Scanner thread joined")


# Allow tests or external code to inject a custom alert handler (kept private)
def _set_alert_handler(handler: Callable[[Dict], None]) -> None:
    global _alert_handler
    _alert_handler = handler


# Module loaded
logger.debug("auto_scanner module loaded")

"""Hermes Service - AI Narrator (Optional Enhancement).

PHASE 7.5 ARCHITECTURE:
=======================
The Tactical Engine ALWAYS runs first and generates a complete structured report.
The Local Narrator ALWAYS generates a complete text report.
AI (Hermes) is OPTIONAL - it only enhances the wording if available.

Users NEVER see "AI service unavailable" - they always receive a complete report.

Flow:
    1. Build AnalysisObject
    2. Run Technical Engines → populate AnalysisObject
    3. Run Decision Engine → populate decision section
    4. Build TacticalReport (structured)
    5. Local Narrator → complete text report
    6. [OPTIONAL] Try AI Narrator → enhanced wording
    7. Return report (user never knows if AI was used)

Failover:
    If AI fails → log error → return Local Narrator report
"""

from core.ai import generate_reply
from core.backends import (
    AIBackendError,
    AITimeoutError,
    AIConnectionError,
    AIRateLimitError,
)
from utils.logger import get_logger

logger = get_logger(__name__)


def ask_hermes(prompt, history=None):
    """Ask Hermes with automatic failover to tactical engine.
    
    DEPRECATED: Use generate_analysis_with_optional_ai() instead.
    This function is kept for backward compatibility.
    
    Parameters
    ----------
    prompt : str
        The prompt to send to Hermes
    history : list, optional
        Conversation history
    
    Returns
    -------
    str
        AI response or tactical engine fallback
    """
    try:
        logger.info("Attempting Hermes AI generation")
        response = generate_reply(prompt, history)
        logger.info("Hermes AI generation successful")
        return response
        
    except AIRateLimitError as e:
        logger.warning(f"Hermes rate limited: {e}")
        return _failover_to_tactical("AI service rate limited", prompt)
    
    except AITimeoutError as e:
        logger.warning(f"Hermes timeout: {e}")
        return _failover_to_tactical("AI service timeout", prompt)
    
    except AIConnectionError as e:
        logger.warning(f"Hermes connection error: {e}")
        return _failover_to_tactical("AI service connection failed", prompt)
    
    except AIBackendError as e:
        logger.warning(f"Hermes backend error: {e}")
        return _failover_to_tactical("AI service unavailable", prompt)
    
    except Exception as e:
        logger.error(f"Unexpected Hermes error: {e}")
        return _failover_to_tactical("AI service error", prompt)


# ============================================================================
# New Architecture - AI as Optional Enhancement
# ============================================================================

def generate_analysis_with_optional_ai(symbol: str, analysis_object=None) -> str:
    """Generate complete market analysis with AI as optional enhancement.
    
    PHASE 7.5 ARCHITECTURE:
    This function implements the correct flow where AI is completely optional.
    
    Flow:
        1. Build/get AnalysisObject
        2. Generate Local Narrator report (ALWAYS succeeds)
        3. Optionally try AI enhancement
        4. Return complete report
    
    User NEVER sees "AI service unavailable" - they always get a complete report.
    
    Parameters
    ----------
    symbol : str
        Trading symbol
    analysis_object : AnalysisObject, optional
        Pre-built analysis object. If None, will be built.
    
    Returns
    -------
    str
        Complete market analysis report
    """
    from services.okx_service import get_market_overview
    from services.local_narrator import generate_local_narrative
    
    logger.info(f"Generating analysis for {symbol} with optional AI enhancement")
    
    # Step 1: Get or build analysis object
    if analysis_object is None:
        try:
            analysis_object = get_market_overview(symbol)
        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            return _generate_error_report(symbol, str(e))
    
    # Step 2: ALWAYS generate Local Narrator report
    # This ensures we ALWAYS have a complete report
    try:
        local_report = generate_local_narrative(analysis_object)
        logger.info(f"Local narrative generated for {symbol}")
    except Exception as e:
        logger.error(f"Local narrator failed for {symbol}: {e}")
        return _generate_error_report(symbol, "Analysis generation failed")
    
    # Step 3: Optionally try AI enhancement
    # AI is completely optional - if it fails, we still return the local report
    try:
        enhanced_report = _try_ai_enhancement(symbol, analysis_object, local_report)
        if enhanced_report:
            logger.info(f"AI enhancement successful for {symbol}")
            return enhanced_report
    except Exception as e:
        logger.warning(f"AI enhancement failed for {symbol}: {e}")
        # Continue with local report
    
    # Step 4: Return local report
    logger.info(f"Returning local narrative for {symbol}")
    return local_report


def _try_ai_enhancement(symbol: str, analysis_object, local_report: str) -> str:
    """Attempt to enhance report with AI narration.
    
    AI is completely optional. If it fails, returns None.
    
    Parameters
    ----------
    symbol : str
        Trading symbol
    analysis_object : AnalysisObject or dict
        Market analysis data
    local_report : str
        Complete local report (fallback if AI fails)
    
    Returns
    -------
    str or None
        AI-enhanced report, or None if AI fails
    """
    from services.local_narrator import build_tactical_report
    
    logger.debug(f"Attempting AI enhancement for {symbol}")
    
    try:
        # Build structured report for AI to enhance
        report = build_tactical_report(analysis_object)
        
        # Create prompt for AI
        prompt = _build_ai_narration_prompt(report)
        
        # Try to get AI enhancement
        ai_response = generate_reply(prompt)
        
        if ai_response and len(ai_response) > 100:
            # AI succeeded - return enhanced report
            return ai_response
        else:
            logger.warning(f"AI returned short response for {symbol}")
            return None
            
    except AIRateLimitError as e:
        logger.info(f"AI rate limited for {symbol}: {e}")
        return None
    except AITimeoutError as e:
        logger.info(f"AI timeout for {symbol}: {e}")
        return None
    except AIConnectionError as e:
        logger.info(f"AI connection error for {symbol}: {e}")
        return None
    except AIBackendError as e:
        logger.info(f"AI backend error for {symbol}: {e}")
        return None
    except Exception as e:
        logger.warning(f"AI enhancement failed for {symbol}: {e}")
        return None


def _build_ai_narration_prompt(report) -> str:
    """Build prompt for AI to enhance the report.
    
    The AI receives the structured report and is asked to enhance
    the narrative while keeping all the same information.
    
    Parameters
    ----------
    report : TacticalReport
        Structured report from Tactical Engine
    
    Returns
    -------
    str
        Prompt for AI narration
    """
    prompt = f"""You are Uncle Tony, a professional trading analyst. Enhance the following market report with your natural language expertise.

SYMBOL: {report.symbol}
MARKET STATE: {report.market_state}
BIAS: {report.bias}
CONFIDENCE: {report.confidence}%
RECOMMENDATION: {report.recommendation}

KEY LEVELS:
- Support: {report.support}
- Resistance: {report.resistance}
- Stop Loss: {report.stop_loss}
- Take Profit: {report.take_profit_1}

INDICATORS:
- RSI: {report.rsi}
- EMA20: {report.ema20}
- EMA50: {report.ema50}
- Trend: {report.trend}

SCENARIOS:
- Bullish: {report.bullish_scenario}
- Bearish: {report.bearish_scenario}
- Sideways: {report.sideways_scenario}

RISK:
- Level: {report.risk_level}
- Factors: {', '.join(report.risk_factors) if report.risk_factors else 'None'}

Please generate a professional, actionable market analysis report. Keep it concise and focused on the key trading insights. Do NOT mention AI, bots, or technical systems - just provide the analysis directly.
"""
    return prompt


def _generate_error_report(symbol: str, error: str) -> str:
    """Generate error report when analysis fails.
    
    This is the absolute last resort. It should rarely be used
    because the Local Narrator should always succeed.
    """
    logger.error(f"Generating error report for {symbol}: {error}")
    
    return f"""⚠️ Temporary Issue

I encountered a temporary issue analyzing {symbol}. This is unusual and should resolve shortly.

Please try:
• /price {symbol} - Quick price check
• /intelligence {symbol} - Full analysis

If this persists, the market data feed may be temporarily unavailable."""


def _extract_symbol_from_prompt(prompt: str) -> str:
    """Extract trading symbol from prompt text.
    
    Parameters
    ----------
    prompt : str
        Prompt text that may contain symbol
    
    Returns
    -------
    str
        Extracted symbol or empty string
    """
    from services.okx_service import KNOWN_SYMBOLS
    
    # Try to find known symbols in prompt
    prompt_upper = prompt.upper()
    for symbol in KNOWN_SYMBOLS:
        if symbol in prompt_upper:
            return symbol
    
    return ""


def _generate_tactical_for_symbol(symbol: str, reason: str) -> str:
    """Generate tactical analysis for a specific symbol.
    
    Parameters
    ----------
    symbol : str
        Trading symbol
    reason : str
        Reason for failover
    
    Returns
    -------
    str
        Complete tactical analysis
    """
    from services.okx_service import get_market_overview
    from services.tactical_engine import generate_tactical_analysis
    
    try:
        logger.info(f"Generating tactical analysis for {symbol}")
        
        # Get market data
        overview = get_market_overview(symbol)
        
        # Generate tactical analysis
        tactical_report = generate_tactical_analysis(overview)
        
        # Prepend failover notice
        notice = (
            "⚠️ AI service unavailable. Switching to Uncle Tony Tactical Engine...\n\n"
        )
        
        return notice + tactical_report
    
    except Exception as e:
        logger.error(f"Failed to generate tactical analysis for {symbol}: {e}")
        return _generate_generic_tactical_response(reason)


def _generate_generic_tactical_response(reason: str) -> str:
    """Generate generic tactical response when symbol extraction fails.
    
    Parameters
    ----------
    reason : str
        Reason for failover
    
    Returns
    -------
    str
        Generic tactical message
    """
    return (
        "⚠️ AI service unavailable. Switching to Uncle Tony Tactical Engine...\n\n"
        "I'm currently running on my tactical analysis engine due to AI service issues. "
        "For detailed market analysis, please use:\n\n"
        "/intelligence <symbol> - Full tactical analysis\n"
        "/analysis <symbol> - Market overview\n"
        "/price <symbol> - Quick price check\n\n"
        "Example: /intelligence BTC"
    )

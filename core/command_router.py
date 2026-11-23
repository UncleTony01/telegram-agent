from handlers.message_handler import handle_message
from services.analysis_service import handle_analysis_command
from services.help_service import send_help
from services.price_service import handle_price_command
from services.market_intelligence import generate_intelligence
from services.telegram_service import send_message


def route_command(chat_id: str, text: str):
    text = text.strip()
    if not text:
        return

    normalized = text.lower()
    if normalized.startswith("/help"):
        return send_help(chat_id)

    if normalized.startswith("/price"):
        return handle_price_command(chat_id, text)

    if normalized.startswith("/analysis"):
        # The analysis card already includes "Your position".
        return handle_analysis_command(chat_id, text)

    if normalized.startswith("/portfolio"):
        from utils.chat_filter import is_owner

        if not is_owner(chat_id):
            return send_message(chat_id, "🔒 Portfolio is private to the bot owner.")
        from services.portfolio_service import handle_portfolio_command
        return handle_portfolio_command(chat_id)

    if normalized.startswith("/intelligence") or normalized.startswith("/market"):
        return handle_intelligence_command(chat_id, text)

    if normalized.startswith("/tactical"):
        return handle_tactical_command(chat_id, text)
    
    if normalized.startswith("/analyze"):
        handle_analyze_command(chat_id, text)
        return send_position_section(chat_id, text)

    if normalized.startswith("/check"):
        from services.reality_check import handle_check_command
        return handle_check_command(chat_id, text)

    if normalized.startswith("/xpost"):
        from services.x_poster import handle_xpost_command
        return handle_xpost_command(chat_id, text)

    if normalized.startswith("/ledger"):
        from services.hype_ledger import handle_ledger_command
        return handle_ledger_command(chat_id)

    if normalized.startswith("/status"):
        from services.heartbeat import handle_status_command
        return handle_status_command(chat_id)

    if normalized.startswith("/scan"):
        from services.auto_scanner import handle_scan_command
        return handle_scan_command(chat_id)

    return handle_message(chat_id, text)

def send_position_section(chat_id: str, text: str):
    """After an analysis, add a 'Your position' message if you hold that coin."""
    from utils.chat_filter import is_owner

    if not is_owner(chat_id):
        return
    parts = text.strip().split()
    if len(parts) < 2:
        return
    symbol = parts[1].upper()
    try:
        from services.portfolio_service import get_position, position_section

        if not get_position(symbol):
            return
        support = resistance = None
        try:
            from core.analysis_pipeline import analyze

            structure = analyze(symbol).market_structure
            support = getattr(structure, "nearest_support", None)
            resistance = getattr(structure, "nearest_resistance", None)
        except Exception:
            pass
        section = position_section(symbol, support, resistance)
        if section:
            send_message(chat_id, section)
    except Exception:
        # Portfolio is optional (e.g. no OKX key on this machine); never break analysis.
        return


def handle_intelligence_command(chat_id: str, text: str):
    """Handle /intelligence or /market command for full market intelligence reports."""
    parts = text.strip().split()
    if len(parts) < 2:
        send_message(
            chat_id,
            "Usage: /intelligence <symbol>\n"
            "Example: /intelligence BTC\n"
            "Example: /market ETH"
        )
        return

    symbol = parts[1].upper()
    
    try:
        from services.okx_service import get_market_overview
        from services.trend_engine import analyze_trend
        
        # Get market overview
        overview = get_market_overview(symbol)
        
        # Add trend analysis to overview for market_intelligence module
        trend_analysis = analyze_trend(overview)
        overview["trend_analysis"] = trend_analysis
        
        # Generate intelligence report
        intelligence = generate_intelligence(overview, symbol)
        
        # Build the dashboard
        dashboard = generate_dashboard(intelligence)
        
        send_message(chat_id, dashboard)
        
    except Exception as e:
        send_message(chat_id, f"Error generating intelligence report: {e}")


def generate_dashboard(intelligence):
    """Import locally to avoid circular dependency."""
    from services.market_intelligence import generate_dashboard as gen_dashboard
    return gen_dashboard(intelligence)


def handle_tactical_command(chat_id: str, text: str):
    """Handle /tactical command for Uncle Tony Tactical Engine analysis.
    
    This provides purely local rule-based analysis without AI dependency.
    """
    parts = text.strip().split()
    if len(parts) < 2:
        send_message(
            chat_id,
            "Usage: /tactical <symbol>\n"
            "Example: /tactical BTC\n"
            "Example: /tactical ETH\n\n"
            "Get pure local analysis without AI dependency."
        )
        return

    symbol = parts[1].upper()
    
    try:
        from services.okx_service import get_market_overview, KNOWN_SYMBOLS
        from services.tactical_engine import generate_tactical_analysis
        from utils.logger import get_logger
        
        logger = get_logger(__name__)
        
        if symbol not in KNOWN_SYMBOLS:
            send_message(chat_id, f"Unknown symbol: {symbol}. I don't have market data for it.")
            return
        
        logger.info(f"Generating tactical analysis for {symbol}")
        
        # Get market overview
        overview = get_market_overview(symbol)
        
        # Generate tactical analysis
        tactical_report = generate_tactical_analysis(overview)
        
        send_message(chat_id, tactical_report)
        
    except Exception as e:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.error(f"Tactical command failed for {symbol}: {e}")
        send_message(chat_id, f"Error generating tactical analysis: {e}")


def handle_analyze_command(chat_id: str, text: str):
    """Handle /analyze command using the new AnalysisObject pipeline.
    
    This command uses the unified AnalysisObject architecture that all
    future engines will use. It provides the same quality analysis but
    with better maintainability and extensibility.
    """
    parts = text.strip().split()
    if len(parts) < 2:
        send_message(
            chat_id,
            "Usage: /analyze <symbol>\n"
            "Example: /analyze BTC\n"
            "Example: /analyze ETH\n\n"
            "Uses the new AnalysisObject pipeline architecture."
        )
        return

    symbol = parts[1].upper()
    
    try:
        from core.analysis_pipeline import analyze
        from utils.logger import get_logger
        
        logger = get_logger(__name__)
        logger.info(f"Running AnalysisObject pipeline for {symbol}")
        
        # Run complete analysis through pipeline
        analysis = analyze(symbol)
        
        # Generate report from narrative section
        report = analysis.narrative.full_report
        
        # Add metadata
        metadata = f"\nEngines Used: {', '.join(analysis.engines_used)}\n"
        metadata += f"Analysis Version: {analysis.analysis_version}\n"
        metadata += "=" * 24
        
        send_message(chat_id, report + metadata)
        
    except Exception as e:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.error(f"Analyze command failed for {symbol}: {e}")
        send_message(chat_id, f"Error running analysis pipeline: {e}")

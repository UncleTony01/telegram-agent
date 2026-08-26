"""Analysis service - Phase 7.5 Architecture.

AI is completely optional. The Tactical Engine ALWAYS runs first,
generating a complete structured report. The Local Narrator ALWAYS
produces a complete text report. AI only enhances wording if available.

Users NEVER see "AI service unavailable" - they always receive a
complete analysis report.
"""

from services.okx_service import KNOWN_SYMBOLS
from services.telegram_service import send_message
from services.hermes_service import generate_analysis_with_optional_ai
from utils.logger import get_logger

logger = get_logger(__name__)


def handle_analysis_command(chat_id: str, text: str):
    """Handle /analysis command with Phase 7.5 architecture.
    
    Architecture:
        1. Get market data
        2. Run Tactical Engine (ALWAYS)
        3. Generate Local Narrative (ALWAYS)
        4. Optionally try AI enhancement
        5. Return complete report
    
    User NEVER sees "AI service unavailable".
    """
    parts = text.strip().split()
    if len(parts) < 2:
        send_message(
            chat_id,
            "Usage: /analysis <symbol> [your question]\n"
            "Example: /analysis BTC Should I long?\n"
            "Example: /analysis HYPE\n"
            "Example: /analysis ETH What's the outlook?"
        )
        return

    symbol = parts[1].upper()
    if symbol not in KNOWN_SYMBOLS:
        send_message(chat_id, f"Unknown symbol: {symbol}. I don't have market data for it.")
        return
    
    # Send thinking message
    send_message(chat_id, "Analyzing...")

    try:
        # Use new architecture - AI is optional
        response = generate_analysis_with_optional_ai(symbol)
        send_message(chat_id, response)
        
    except Exception as e:
        logger.error(f"Analysis command failed for {symbol}: {e}")
        
        # Last resort - should rarely reach here
        send_message(
            chat_id,
            f"I encountered a temporary issue analyzing {symbol}. "
            f"Please try again or use: /intelligence {symbol}"
        )
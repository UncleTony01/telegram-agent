"""Message handler - Phase 7.5 Architecture.

AI is completely optional. The system ALWAYS provides a complete response.
Users NEVER see "AI service unavailable".

Flow:
    1. Extract symbols from message
    2. If symbols found → Run full analysis (AI optional)
    3. If no symbols → Try AI chat (with graceful fallback)
"""

from memory.conversation_memory import (
    add_message,
    get_history,
    clear_history,
)

from services.hermes_service import ask_hermes, generate_analysis_with_optional_ai
from services.okx_service import extract_symbols
from services.telegram_service import send_message
from utils.logger import get_logger

logger = get_logger(__name__)


def handle_message(chat_id, text):
    """Handle user messages with Phase 7.5 architecture.

    AI is optional. The system always provides a response.
    """

    text = text.strip()

    if text == "/start":
        send_message(
            chat_id,
            "UNCLE TONY is online.\n\n"
            "Now with conversation memory 🧠\n"
            "Powered by Uncle Tony Intelligence Engine\n\n"
            "Never fails - always provides analysis!"
        )
        return

    if text.lower() == "ping":
        send_message(chat_id, "pong")
        return

    if text.lower() == "/clear":
        clear_history(chat_id)
        send_message(chat_id, "Conversation memory cleared.")
        return

    send_message(chat_id, "Analyzing...")

    try:
        # Extract symbols from message
        symbols = extract_symbols(text)
        
        # If symbols found, use analysis pipeline (AI optional)
        if symbols:
            logger.info(f"Detected symbols in message: {', '.join(symbols)}")
            
            # For simplicity, analyze the first symbol found
            # (Could be extended to analyze all symbols)
            symbol = symbols[0]
            response = generate_analysis_with_optional_ai(symbol)
            
            add_message(chat_id, "user", text)
            add_message(chat_id, "assistant", response)
            
            send_message(chat_id, response)
        else:
            # No symbols - try general chat with AI
            # This will gracefully degrade if AI unavailable
            history = get_history(chat_id)
            
            try:
                reply = ask_hermes(text, history)
                
                add_message(chat_id, "user", text)
                add_message(chat_id, "assistant", reply)
                
                send_message(chat_id, reply)
                
            except Exception as ai_error:
                logger.warning(f"AI chat failed: {ai_error}")
                
                # Fallback for general chat
                response = _generate_general_fallback(text)
                
                add_message(chat_id, "user", text)
                add_message(chat_id, "assistant", response)
                
                send_message(chat_id, response)
        
    except Exception as e:
        logger.error(f"Message handler failed: {e}")
        send_message(
            chat_id,
            "I'm ready to help! Try:\n\n"
            "• Mention a symbol: \"What about BTC?\"\n"
            "• /analysis BTC - Full analysis\n"
            "• /intelligence ETH - Market intelligence\n"
            "• /help - All commands"
        )


def _generate_general_fallback(text: str) -> str:
    """Generate fallback response when AI chat fails.
    
    This is for general conversation without market symbols.
    """
    text_lower = text.lower()
    
    # Try to be helpful based on keywords
    if "help" in text_lower or "how" in text_lower:
        return (
            "I'm Uncle Tony, your trading assistant.\n\n"
            "Here's what I can do:\n"
            "• Analyze any crypto symbol (just mention it)\n"
            "• /analysis BTC - Full market analysis\n"
            "• /intelligence ETH - Market intelligence\n"
            "• /tactical SOL - Local analysis (no AI)\n"
            "• /price BTC - Quick price check\n\n"
            "Just mention a symbol and I'll analyze it!"
        )
    
    if "thank" in text_lower:
        return "You're welcome! Let me know if you need any market analysis."
    
    if "hello" in text_lower or "hi" in text_lower:
        return "Hello! I'm ready to analyze any crypto. Just mention a symbol or use /analysis <symbol>"
    
    # Default helpful response
    return (
        "I'm here to help with crypto analysis.\n\n"
        "Try mentioning a symbol like:\n"
        "• \"What do you think about BTC?\"\n"
        "• \"Analyze ETH for me\"\n"
        "• \"Should I buy SOL?\"\n\n"
        "Or use commands:\n"
        "• /analysis BTC\n"
        "• /intelligence ETH\n"
        "• /help"
    )

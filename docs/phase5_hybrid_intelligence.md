# Phase 5 – Hybrid Intelligence & Failover Engine

## Overview

Phase 5 transforms Uncle Tony into a **resilient trading assistant** that never fails due to AI service unavailability. The system seamlessly combines AI intelligence with local rule-based analysis, automatically switching between them as needed.

---

## Architecture

### Hybrid Intelligence Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    User Request                              │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Hermes Service (services/hermes_service.py)     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Try: AI Backend (Hermes CLI)                        │   │
│  │    ↓                                                  │   │
│  │  Detect: 429, timeout, connection errors             │   │
│  │    ↓                                                  │   │
│  │  Catch: All AI failures                              │   │
│  │    ↓                                                  │   │
│  │  Failover: Uncle Tony Tactical Engine                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                        │
           ┌────────────┴────────────┐
           ▼                         ▼
┌──────────────────────┐  ┌──────────────────────┐
│   AI Analysis        │  │  Tactical Engine     │
│   (When Available)   │  │  (Always Available)  │
│                      │  │                      │
│ • Hermes CLI         │  │ • Local indicators   │
│ • Context-aware      │  │ • Rule-based logic   │
│ • Natural language   │  │ • Deterministic      │
│ • Conversational     │  │ • No dependencies    │
└──────────────────────┘  └──────────────────────┘
           │                         │
           └────────────┬────────────┘
                        ▼
              Complete Analysis Delivered
```

---

## Components

### 1. Enhanced AI Backend (core/backends.py)

**New Exception Classes:**
- `AIBackendError` – Base exception for all AI failures
- `AITimeoutError` – Command timeout (default: 180s)
- `AIConnectionError` – Network/connection issues
- `AIRateLimitError` – HTTP 429 rate limit

**Robust Error Detection:**
- Exit code checking
- stderr parsing for "429", "rate limit", "connection", "timeout"
- Structured exception hierarchy
- Comprehensive logging

### 2. Hybrid Hermes Service (services/hermes_service.py)

**Failover Logic:**
```python
try:
    # Attempt AI generation
    response = generate_reply(prompt, history)
    return response
except AIRateLimitError:
    return _failover_to_tactical("rate limited", prompt)
except AITimeoutError:
    return _failover_to_tactical("timeout", prompt)
except AIConnectionError:
    return _failover_to_tactical("connection failed", prompt)
except AIBackendError:
    return _failover_to_tactical("unavailable", prompt)
```

**Features:**
- Zero user-facing error exposure
- Automatic symbol extraction from prompts
- Contextual failover messages
- Maintains conversation flow

### 3. Uncle Tony Tactical Engine (services/tactical_engine.py)

**Decision Engine:**

Analyzes market using deterministic rules:
- **Bias determination**: Bullish/Bearish/Neutral
- **Confidence calculation**: 0-100 score
- **Scenario generation**: Bull/bear/sideways paths
- **Level identification**: Support/resistance
- **Recommendation**: BUY/SELL/WAIT with reasoning
- **Risk assessment**: HIGH/MODERATE/ACCEPTABLE

**Input Indicators:**
- Price vs EMA20/EMA50 alignment
- RSI zones (overbought/oversold/neutral)
- Market structure (bullish/bearish/range)
- Funding rate extremes
- Volume and open interest
- Probability engine output (if available)

**Narrative Builder:**

Generates natural language in Uncle Tony's style:
- Executive summary
- Market overview
- Key levels
- Technical indicators
- Scenarios (bull/bear/sideways)
- Trading plan with entry/stop/targets
- Risk warning

**Output Format:**
```
============================================================
UNCLE TONY TACTICAL ANALYSIS: BTC
============================================================

📊 EXECUTIVE SUMMARY

Market Bias:     Bullish
Confidence:      75/100
Recommendation:  BUY on support or breakout above resistance
Risk Level:      ACCEPTABLE RISK

📈 MARKET OVERVIEW
BTC is showing bullish structure with price at $45,000...

🎯 KEY LEVELS
Support:     $44,500
Resistance:  $46,200

[... complete analysis ...]
```

---

## Failover Triggers

| Condition | Detection | Action |
|-----------|-----------|--------|
| HTTP 429 | stderr contains "429" or "rate limit" | Tactical failover |
| Timeout | subprocess.TimeoutExpired after 180s | Tactical failover |
| Connection error | stderr contains "connection", "network", "timeout" | Tactical failover |
| Command not found | FileNotFoundError | Tactical failover |
| Non-zero exit | result.returncode != 0 | Tactical failover |
| No output | Empty stdout and stderr | Tactical failover |
| Unexpected exception | Any other exception | Tactical failover |

---

## User Commands

### Existing Commands (Now with Failover)

- `/analysis <symbol>` – AI analysis with tactical failover
- `/price <symbol>` – Price check
- `/intelligence <symbol>` – Market intelligence report
- Chat messages – Natural conversation with market context

### New Commands

- `/tactical <symbol>` – Explicit tactical engine analysis (bypasses AI)

Example:
```
/tactical BTC
```

Returns pure local analysis without attempting AI call.

---

## Benefits

### 1. **100% Uptime**
- Bot never fails due to AI unavailability
- Always provides actionable analysis
- Seamless user experience

### 2. **Transparent Failover**
- Users see: "⚠️ AI service unavailable. Switching to Uncle Tony Tactical Engine..."
- No stack traces or technical errors
- Maintains professional appearance

### 3. **Quality Consistency**
- Tactical engine matches AI report structure
- Same indicator coverage
- Same actionable recommendations
- Natural language narratives

### 4. **Debug Visibility**
- All failures logged internally
- Clear failure reasons in logs
- No user-facing technical details

### 5. **Modular Design**
- Easy to swap AI providers
- Tactical engine independent
- Clean separation of concerns

---

## Implementation Details

### Exception Handling Flow

```python
# Level 1: Backend (core/backends.py)
try:
    result = subprocess.run([HERMES_CMD, ...])
    # Check exit code, stderr, output
    if issues_detected:
        raise appropriate_exception
except subprocess.TimeoutExpired:
    raise AITimeoutError
except FileNotFoundError:
    raise AIConnectionError

# Level 2: Service (services/hermes_service.py)
try:
    response = generate_reply(...)
except AI_SPECIFIC_ERROR:
    return _failover_to_tactical(...)

# Level 3: Handlers (handlers/message_handler.py, services/analysis_service.py)
try:
    reply = ask_hermes(...)
except Exception:
    # Last resort failover
    return generate_tactical_analysis(...)
```

### Logging Strategy

**Internal logs (not shown to users):**
```python
logger.warning(f"Hermes rate limited: {e}")
logger.error(f"Unexpected Hermes error: {e}")
logger.info("Failing over to Tactical Engine due to: timeout")
```

**User messages (clean and actionable):**
```
⚠️ AI service unavailable. Switching to Uncle Tony Tactical Engine...
```

---

## Testing Scenarios

### Test 1: Simulate Rate Limit
```bash
# Mock stderr containing "429"
# Expected: Tactical failover with rate limit message
```

### Test 2: Simulate Timeout
```bash
# Set HERMES_TIMEOUT to 1 second
# Expected: Tactical failover after 1s
```

### Test 3: Simulate Connection Error
```bash
# Mock stderr containing "connection failed"
# Expected: Tactical failover with connection error message
```

### Test 4: Normal Operation
```bash
/analysis BTC
# Expected: AI-powered analysis (if Hermes available)
```

### Test 5: Explicit Tactical
```bash
/tactical BTC
# Expected: Tactical analysis (bypasses AI)
```

---

## Future Enhancements

### Phase 6 Candidates

1. **Multi-Provider Support**
   - OpenAI fallback
   - Anthropic fallback
   - Google Gemini fallback
   - Cascade through providers before tactical engine

2. **Performance Metrics**
   - Track AI success/failure rates
   - Measure failover frequency
   - Monitor response times

3. **Adaptive Timeouts**
   - Reduce timeout after repeated failures
   - Increase timeout after consistent success

4. **Hybrid Mode**
   - Use tactical engine for quick checks
   - Reserve AI for complex questions
   - Combine both for premium analysis

5. **Caching Layer**
   - Cache recent AI responses
   - Return cached + tactical update
   - Reduce API dependency

---

## Integration with Market Intelligence

The Tactical Engine seamlessly integrates with **Phase 5 Market Intelligence**:

- Uses market state classifications
- Leverages opportunity scoring
- Incorporates edge calculations
- Displays confidence breakdowns
- Reuses all existing indicators

No redundancy – just smart failover.

---

## File Changes

### New Files
- `services/tactical_engine.py` – Local rule-based analysis engine

### Modified Files
- `core/backends.py` – Exception hierarchy + robust error detection
- `services/hermes_service.py` – Failover logic + tactical integration
- `services/analysis_service.py` – Enhanced error handling
- `handlers/message_handler.py` – Failover support in chat handler
- `core/command_router.py` – New `/tactical` command
- `core/prompts.py` – Market intelligence explanation guidelines

### Documentation
- `docs/phase5_hybrid_intelligence.md` – This document

---

## Summary

Phase 5 delivers **unbreakable trading intelligence**:

✅ AI when available  
✅ Tactical when AI fails  
✅ Zero downtime  
✅ No user-facing errors  
✅ Complete analysis always  
✅ Professional appearance  
✅ Modular architecture  

**Uncle Tony never fails.**

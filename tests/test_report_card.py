import re

import pytest

import services.auto_scanner as scanner
import services.portfolio_service as ps
from services import report_card as rc
from services.local_narrator import TacticalReport

# Words and symbols that push fear or greed. Messages must stay calm and factual.
BANNED = re.compile(
    r"🔥|🔴|🟢|🚨|💀|🚀|crash|dump|moon|explode|panic|fomo|bloodbath|knife|squeeze|huge|massive|urgent|act now|don't miss",
    re.IGNORECASE,
)


def _report(rec="WAIT"):
    r = TacticalReport("AVAX")
    r.price, r.change_24h = 6.60, -2.3
    r.recommendation, r.bias, r.risk_level = rec, "Bearish", "MODERATE"
    r.confidence, r.opportunity_score = 61, 36
    r.rsi, r.ema20, r.ema50 = 29.1, 7.70, 8.69
    r.support, r.resistance = 6.01, 6.72
    r.bullish_probability, r.bearish_probability, r.sideways_probability = 9, 76, 15
    return r


POSITION = {"symbol": "AVAX", "qty": 5.6878, "value": 37.5, "price": 6.60, "avg_price": 8.37}


def test_bar_and_range_bar():
    assert rc.bar(61) == "▰▰▰▰▰▰▱▱▱▱"
    assert rc.bar(150) == "▰" * 10 and rc.bar(None) == "▱" * 10
    assert "●" in rc.range_bar(6.0, 7.0, 6.5)
    assert rc.range_bar(None, 7.0, 6.5) is None


def test_card_is_organized_and_includes_position():
    card = rc.render_card(_report(), position=POSITION, take="Calm take.", high_24h=6.72, low_24h=6.01)
    for section in ("VERDICT", "Momentum", "Key levels", "Possible paths", "Plan", "Your position", "Uncle Tony's take"):
        assert section in card
    assert "Your avg buy" in card and "Break-even is +26.8% away" in card
    # ladder is ordered high → low
    assert card.index("Your avg buy") < card.index("Resistance") < card.index("Now") < card.index("Support")
    # the AI text is escaped so it can't break Telegram HTML
    assert "&lt;b&gt;" in rc.render_card(_report(), take="<b>x</b>")


@pytest.mark.parametrize("rec", ["WAIT", "BUY", "SELL"])
def test_card_and_local_take_are_calm(rec):
    card = rc.render_card(_report(rec), position=POSITION, take=rc._local_take(_report(rec), POSITION))
    assert not BANNED.search(card), BANNED.search(card)


def test_alerts_briefs_and_portfolio_are_calm():
    texts = [
        scanner.format_alert({"symbol": "SOL", "score": 85, "confidence": 70, "recommendation": "BUY",
                              "support": 150.0, "resistance": 170.0}),
        scanner.format_brief([{"symbol": "SOL", "score": 85, "recommendation": "SELL"},
                              {"symbol": "BTC", "score": 20, "recommendation": "WAIT"}]),
    ]
    state = {}
    pf = lambda pct: {"positions": [{"symbol": "OKB", "qty": 1.0, "value": 100 + pct, "price": 100 + pct,
                                     "avg_price": 100.0, "pnl": pct, "pnl_pct": pct}]}
    ps.position_alerts(pf(-5), state)
    texts += ps.position_alerts(pf(-25), state) + ps.position_alerts(pf(1), state)
    texts.append(ps.format_portfolio({"total": 100.0, "cash": 5.0, "positions": pf(-25)["positions"]}))
    assert len(texts) == 5
    for t in texts:
        assert not BANNED.search(t), (BANNED.search(t), t)


def test_take_prompt_sets_calm_tone():
    prompt = rc._take_prompt(_report(), POSITION)
    assert "fear and greed" in prompt and "HOLDS this coin" in prompt

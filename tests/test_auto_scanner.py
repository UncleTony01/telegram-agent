from datetime import datetime

import pytest

import services.auto_scanner as scanner


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(scanner, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(scanner, "_last_alerts", {})
    monkeypatch.setattr(scanner, "_last_scan", {"ts": 0.0, "items": []})
    monkeypatch.setattr(scanner.config, "CHAT_ID", "123")
    monkeypatch.setattr(scanner, "_portfolio_block", lambda previous_total=None: (None, None))
    sent = []
    import services.telegram_service as tg

    monkeypatch.setattr(tg, "send_message", lambda chat_id, text: sent.append((chat_id, text)))
    return sent


ITEMS = [
    {"symbol": "BTC", "score": 45, "recommendation": "WAIT"},
    {"symbol": "SOL", "score": 82, "recommendation": "BUY"},
    {"symbol": "TRX", "score": 25, "recommendation": "SELL"},
]


def test_format_brief_ranks_and_flags_best_setup():
    text = scanner.format_brief(ITEMS, "Morning market check")
    assert text.index("SOL") < text.index("BTC") < text.index("TRX")
    assert "🟢 SOL: 82/100 · BUY" in text
    assert "Best setup: SOL (82)" in text
    assert "Not financial advice." in text


def test_format_brief_without_strong_setup():
    text = scanner.format_brief(ITEMS[:1])
    assert "No strong setups" in text


def test_format_brief_empty():
    assert "No market data" in scanner.format_brief([])


@pytest.mark.parametrize(
    "hour,expected",
    [(7, None), (8, "2026-11-21 08"), (9, "2026-11-21 08"), (10, None), (20, "2026-11-21 20"), (23, None)],
)
def test_due_brief_slot(hour, expected):
    assert scanner._due_brief_slot(datetime(2026, 11, 21, hour, 15)) == expected


def test_brief_sent_once_per_slot(isolated_state):
    scanner._last_scan["items"] = ITEMS
    at_8 = datetime(2026, 11, 21, 8, 5)
    assert scanner.maybe_send_brief(at_8) is True
    assert scanner.maybe_send_brief(datetime(2026, 11, 21, 9, 0)) is False
    assert len(isolated_state) == 1
    assert "Morning market check" in isolated_state[0][1]
    assert scanner.maybe_send_brief(datetime(2026, 11, 21, 20, 1)) is True
    assert "Evening market check" in isolated_state[1][1]


def test_brief_not_sent_outside_window(isolated_state):
    assert scanner.maybe_send_brief(datetime(2026, 11, 21, 14, 0)) is False
    assert isolated_state == []


def test_alert_cooldown_ignores_small_score_changes():
    assert scanner._should_alert("SOL", 82, "BUY") is True
    assert scanner._should_alert("SOL", 84, "BUY") is False


def test_alert_repeats_when_recommendation_changes():
    assert scanner._should_alert("SOL", 82, "BUY") is True
    assert scanner._should_alert("SOL", 81, "SELL") is True

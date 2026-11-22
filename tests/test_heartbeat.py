from datetime import datetime

import pytest

import services.heartbeat as hb


NOW = datetime(2026, 11, 22, 9, 0).timestamp()


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(hb, "STATE_FILE", tmp_path / "hb.json")
    monkeypatch.setattr(hb, "_problems", {})
    monkeypatch.setattr(hb, "_started_at", NOW - 3600)
    monkeypatch.setattr(hb, "_last_poll_ok", NOW - 5)
    monkeypatch.setattr(hb.config, "CHAT_ID", "123")
    monkeypatch.setattr(hb.config, "HEARTBEAT_HOUR", 7)
    sent = []
    monkeypatch.setattr(hb, "_send", lambda text: sent.append(text))
    return sent


def scanner(monkeypatch, last_scan_age):
    info = {"last_scan_ts": NOW - last_scan_age if last_scan_age is not None else 0.0, "interval": 900, "symbols": 9}
    monkeypatch.setattr(hb, "_scanner_info", lambda: info)


def test_healthy_bot_has_no_problems(monkeypatch):
    scanner(monkeypatch, 120)
    assert hb.find_problems(NOW) == {}
    assert "all systems OK" in hb.status_text(NOW)


def test_stalled_scanner_is_detected(monkeypatch):
    scanner(monkeypatch, 3 * 3600)
    problems = hb.find_problems(NOW)
    assert "scanner" in problems
    assert "needs attention" in hb.status_text(NOW)


def test_stalled_polling_is_detected(monkeypatch):
    scanner(monkeypatch, 60)
    monkeypatch.setattr(hb, "_last_poll_ok", NOW - 3600)
    assert "polling" in hb.find_problems(NOW)


def test_scanner_off_is_not_a_problem(monkeypatch):
    monkeypatch.setattr(hb, "_scanner_info", lambda: None)
    assert hb.find_problems(NOW) == {}
    assert "Scanner: off" in hb.status_text(NOW)


def test_warns_once_then_reports_recovery(monkeypatch, isolated):
    monkeypatch.setattr(hb, "maybe_send_daily", lambda now=None: None)
    scanner(monkeypatch, 3 * 3600)
    first = hb.check_once(NOW)
    second = hb.check_once(NOW + 300)
    assert len(first) == 1 and "warning" in first[0]
    assert second == []  # no repeated spam
    scanner(monkeypatch, 60)
    monkeypatch.setattr(hb, "_last_poll_ok", NOW + 590)
    third = hb.check_once(NOW + 600)
    assert len(third) == 1 and "Recovered" in third[0]


def test_daily_check_in_once_per_day(monkeypatch, isolated):
    scanner(monkeypatch, 60)
    assert hb.maybe_send_daily(NOW) is not None
    assert hb.maybe_send_daily(NOW + 3600) is None
    assert "Daily check-in" in isolated[0]


def test_daily_check_in_waits_for_hour(monkeypatch):
    scanner(monkeypatch, 60)
    early = datetime(2026, 11, 22, 5, 0).timestamp()
    assert hb.maybe_send_daily(early) is None


def test_ago_formatting():
    assert hb._ago(30) == "30s"
    assert hb._ago(600) == "10 min"
    assert hb._ago(3 * 3600 + 120) == "3h 2m"
    assert hb._ago(3 * 86400) == "3d 0h"

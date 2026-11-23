import json
from unittest.mock import patch

import pytest

import config
from services import hype_ledger as hl
from services import reality_check as rc
from tests.test_reality_check import INPUTS

DAY = 86400
T0 = 1_790_000_000.0


@pytest.fixture(autouse=True)
def tmp_ledger(tmp_path, monkeypatch):
    monkeypatch.setattr(hl, "LEDGER_FILE", tmp_path / "data" / "ledger.jsonl")


def report(text):
    return rc.analyse(rc.parse_claim(text), INPUTS)


def test_record_stores_claim_without_chat_ids():
    hl.record_check(report("/check AVAX $10"), now=T0)
    line = json.loads(hl.LEDGER_FILE.read_text().strip())
    assert line["symbol"] == "AVAX" and line["coin_id"] == "avalanche-2"
    assert line["price_then"] == 6.68 and line["target_price"] == 10
    assert not any("chat" in k for k in line)


def test_review_scores_only_old_enough_entries():
    hl.record_check(report("/check AVAX $10"), now=T0)               # 40 days old
    hl.record_check(report("/check AVAX 100B"), now=T0)              # 40 days old
    hl.record_check(report("/check AVAX $20"), now=T0 + 35 * DAY)   # 5 days old
    result = hl.review(now=T0 + 40 * DAY, prices={"avalanche-2": 11.0})
    assert result["total"] == 3
    assert len(result["reviewed"]) == 2
    assert result["hits"] == 1
    ten = next(s for s in result["reviewed"] if s["target_price"] == 10)
    assert ten["hit"] and ten["change_pct"] == pytest.approx((11 / 6.68 - 1) * 100)
    big = next(s for s in result["reviewed"] if s["kind"] == "mcap")
    assert not big["hit"] and 0 < big["progress_pct"] < 5


def test_format_review_empty_and_filled():
    assert "Nothing is 30+ days old" in hl.format_review(hl.review(now=T0, prices={}))
    hl.record_check(report("/check AVAX $10"), now=T0)
    text = hl.format_review(hl.review(now=T0 + 31 * DAY, prices={"avalanche-2": 12.0}))
    assert "1 reached their target" in text and "✅" in text


def test_ledger_command_is_owner_only(monkeypatch):
    monkeypatch.setattr(config, "OWNER_CHAT_ID", "111")
    with patch("services.telegram_service.send_message") as send:
        hl.handle_ledger_command("222")
    assert "private" in send.call_args[0][1]
    with patch("services.telegram_service.send_message") as send:
        hl.handle_ledger_command("111")
    assert "Hype ledger" in send.call_args[0][1]

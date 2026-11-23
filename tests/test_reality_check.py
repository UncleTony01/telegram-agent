from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from services import reality_check as rc

AVAX = {
    "id": "avalanche-2", "symbol": "avax", "name": "Avalanche",
    "current_price": 6.68, "market_cap": 2_983_818_065, "market_cap_rank": 25,
    "circulating_supply": 446_675_167, "max_supply": 720_000_000, "total_supply": 460_000_000,
    "ath": 144.96,
}
TOP = [
    {"id": "bitcoin", "symbol": "btc", "market_cap": 1_222e9},
    {"id": "ethereum", "symbol": "eth", "market_cap": 209.4e9},
    {"id": "tether", "symbol": "usdt", "market_cap": 174.6e9},
    {"id": "binancecoin", "symbol": "bnb", "market_cap": 73.2e9},
    {"id": "usd-coin", "symbol": "usdc", "market_cap": 68.4e9},
    {"id": "ripple", "symbol": "xrp", "market_cap": 58.9e9},
    {"id": "solana", "symbol": "sol", "market_cap": 41.6e9},
    {"id": "avalanche-2", "symbol": "avax", "market_cap": 2.98e9},
]


def ts(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc).timestamp() * 1000


PRICES = [[ts(2025, 11, 25), 13.2], [ts(2026, 3, 1), 9.0], [ts(2026, 9, 20), 11.3], [ts(2026, 11, 22), 6.68]]
INPUTS = {"coin": AVAX, "top": TOP, "prices": PRICES}


@pytest.mark.parametrize("text,kind,value", [
    ("/check AVAX 100B", "mcap", 100e9),
    ("/check avax $20", "price", 20.0),
    ("/check SOL 10x", "multiple", 10.0),
    ("/check AVAX to 100b", "mcap", 100e9),
    ("/check BTC 150K", "price", 150_000.0),
    ("/check $avax 1.5T", "mcap", 1.5e12),
])
def test_parse_claim(text, kind, value):
    claim = rc.parse_claim(text)
    assert claim.kind == kind and claim.value == pytest.approx(value)


@pytest.mark.parametrize("text", ["/check", "/check AVAX", "/check AVAX moon"])
def test_parse_rejects_bad_input(text):
    assert rc.parse_claim(text) is None


def test_mcap_claim_maths():
    r = rc.analyse(rc.parse_claim("/check AVAX 100B"), INPUTS)
    assert r["target_price"] == pytest.approx(100e9 / 446_675_167)  # ≈ $223.9
    assert r["multiple"] == pytest.approx(r["target_price"] / 6.68)
    assert r["rank_at_target"] == 4  # behind BTC, ETH, USDT
    assert r["passes"] == ["BNB", "USDC", "XRP", "SOL"]
    assert r["dilution"]["price_at_full_supply"] == pytest.approx(100e9 / 720e6)  # ≈ $139
    assert r["dilution"]["extra_pct"] == pytest.approx((720e6 / 446_675_167 - 1) * 100)
    assert r["year"]["last_at_target"] is None
    assert r["target_price"] > r["ath"]


def test_price_claim_finds_last_time_at_target():
    r = rc.analyse(rc.parse_claim("/check AVAX $10"), INPUTS)
    assert r["target_mcap"] == pytest.approx(10 * 446_675_167)
    assert r["year"]["last_at_target"].date().isoformat() == "2026-09-20"
    assert r["rank_at_target"] == 8


def test_multiple_claim():
    r = rc.analyse(rc.parse_claim("/check AVAX 3x"), INPUTS)
    assert r["target_price"] == pytest.approx(20.04)
    assert r["multiple"] == pytest.approx(3.0)


def test_report_is_neutral_and_complete():
    text = rc.format_report(rc.analyse(rc.parse_claim("/check AVAX 100B"), INPUTS))
    assert "#4" in text and "passing BNB, USDC, XRP, SOL" in text
    assert "$139" in text
    assert "Not reached in the past year" in text
    assert "not financial advice" in text.lower()
    for word in ("buy ", "sell now", "is impossible", "guaranteed to", "moon"):
        assert word not in text.lower()


def test_handle_check_sends_report_and_records():
    with patch.object(rc, "fetch_inputs", return_value=INPUTS), \
         patch("services.telegram_service.send_message") as send, \
         patch("services.hype_ledger.record_check") as record:
        rc.handle_check_command("1", "/check AVAX 100B")
    assert "Reality Check" in send.call_args[0][1]
    record.assert_called_once()


def test_handle_check_usage_and_unknown_coin():
    with patch("services.telegram_service.send_message") as send:
        rc.handle_check_command("1", "/check")
    assert "/check AVAX 100B" in send.call_args[0][1]
    with patch.object(rc, "fetch_inputs", return_value=None), \
         patch("services.telegram_service.send_message") as send:
        rc.handle_check_command("1", "/check ZZZ 10x")
    assert "couldn't find ZZZ" in send.call_args[0][1]


def test_ledger_failure_never_breaks_reply():
    with patch.object(rc, "fetch_inputs", return_value=INPUTS), \
         patch("services.telegram_service.send_message") as send, \
         patch("services.hype_ledger.record_check", side_effect=OSError("disk full")):
        rc.handle_check_command("1", "/check AVAX 100B")
    send.assert_called_once()


def test_small_target_outside_top_100():
    top = [{"id": f"c{i}", "symbol": f"c{i}", "market_cap": 10e9 - i * 1e7} for i in range(100)]
    r = rc.analyse(rc.parse_claim("/check AVAX $8"), {"coin": AVAX, "top": top, "prices": PRICES})
    assert r["rank_at_target"] > 100
    assert "outside today's top 100" in rc.format_report(r)

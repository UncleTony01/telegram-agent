import pytest

import services.portfolio_service as ps

RAW = [{
    "totalEq": "164.79",
    "details": [
        {"ccy": "BTC", "eq": "0.00123", "eqUsd": "73.80", "openAvgPx": "66402", "spotUpl": "-7.88"},
        {"ccy": "AVAX", "eq": "5.6878", "eqUsd": "37.72", "accAvgPx": "8.375", "spotUpl": ""},
        {"ccy": "USDT", "eq": "9.68", "eqUsd": "9.67"},
        {"ccy": "DOGE", "eq": "0.0000001", "eqUsd": "0.00000001"},
    ],
}]


@pytest.fixture
def portfolio():
    return ps.parse_balance(RAW)


def test_parse_balance_keeps_real_positions_and_cash(portfolio):
    assert [p["symbol"] for p in portfolio["positions"]] == ["BTC", "AVAX"]
    assert portfolio["cash"] == pytest.approx(9.67)
    assert portfolio["total"] == pytest.approx(164.79)


def test_parse_balance_computes_missing_pnl(portfolio):
    avax = portfolio["positions"][1]
    assert avax["price"] == pytest.approx(37.72 / 5.6878)
    assert avax["pnl"] == pytest.approx((avax["price"] - 8.375) * 5.6878)
    assert avax["pnl_pct"] < 0


def test_parse_balance_empty_raises():
    with pytest.raises(ps.PortfolioUnavailable):
        ps.parse_balance([])


def test_format_portfolio(portfolio):
    text = ps.format_portfolio(portfolio, previous_total=160.0)
    assert "Total: $164.79 (+$4.79 since last brief)" in text
    assert "▼ BTC: $73.80 · −$7.88" in text
    assert "Cash (USDT): $9.67" in text


def test_position_section(monkeypatch, portfolio):
    monkeypatch.setattr(ps, "get_portfolio", lambda force=False: portfolio)
    text = ps.position_section("btc", support=55134.0, resistance=61950.0)
    assert "Your BTC position" in text
    assert "Avg buy price: $66,402" in text
    assert "Break-even is +" in text
    assert "below your buy price" in text
    assert ps.position_section("SOL") is None


def _pf(pct):
    avg = 100.0
    price = avg * (1 + pct / 100)
    return {"positions": [{"symbol": "OKB", "qty": 1.0, "value": price, "price": price,
                           "avg_price": avg, "pnl": price - avg, "pnl_pct": pct}]}


def test_position_alerts_first_sighting_is_silent():
    state = {}
    assert ps.position_alerts(_pf(-21), state) == []
    assert state["coins"]["OKB"] == {"above": False, "level": 2}


def test_position_alerts_drawdown_steps_and_break_even():
    state = {}
    ps.position_alerts(_pf(-12), state)              # level 1, silent first time
    assert ps.position_alerts(_pf(-15), state) == []  # same step
    msgs = ps.position_alerts(_pf(-22), state)        # deeper step
    assert len(msgs) == 1 and "below your average buy price" in msgs[0]
    assert ps.position_alerts(_pf(-18), state) == []  # recovering a bit: no alert
    msgs = ps.position_alerts(_pf(1), state)          # back to break-even
    assert len(msgs) == 1 and "back at your average buy price" in msgs[0]
    assert ps.position_alerts(_pf(3), state) == []    # stays above: no repeat

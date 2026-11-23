from datetime import datetime

import pytest

from services import content_mix as cm
from tests.test_x_poster import BANNED


def coin(sym, price, ath, ath_chg, circ=None, mx=None, mcap=1e9, rank=50, week=None, name=None):
    return {"symbol": sym.lower(), "name": name or sym, "current_price": price, "ath": ath,
            "ath_change_percentage": ath_chg, "circulating_supply": circ, "max_supply": mx,
            "market_cap": mcap, "market_cap_rank": rank, "price_change_percentage_7d_in_currency": week}


COINS = [
    coin("AVAX", 6.68, 144.96, -95.4, circ=446e6, mx=720e6, mcap=2.98e9, rank=25, week=-11.5),
    coin("DOT", 3.0, 55.0, -94.5, circ=1.5e9, mx=None),
    coin("SUI", 2.0, 5.0, -60.0, circ=3e9, mx=10e9, mcap=6e9, week=12.3),
    coin("BTC", 60800, 126000, -51.7, circ=20.1e6, mx=21e6, mcap=1.22e12, rank=1, week=1.2),
]


@pytest.mark.parametrize("library", [cm.AI_TAKES, cm.GOVERNANCE_TAKES, cm.DEBATE_QUESTIONS])
def test_takes_fit_and_stay_calm(library):
    for take in library:
        assert len(take) <= 280, take
        assert not BANNED.search(take), (take, BANNED.search(take))


def test_week_has_seven_formats():
    days = [cm.format_for_day(datetime(2026, 11, 23 + i).weekday()) for i in range(7)]
    assert days == ["reality", "recovery", "ai", "dilution", "hype", "governance", "debate"]


def test_takes_rotate_without_repeats():
    state = {}
    seen = [cm.next_take("ai", state) for _ in range(len(cm.AI_TAKES))]
    assert len(set(seen)) == len(cm.AI_TAKES)
    assert cm.next_take("ai", state) in cm.AI_TAKES  # starts a new round


def test_recovery_post_maths_and_skips_recent():
    post = cm.recovery_post(COINS, recent=set())
    assert post["symbol"] == "AVAX"
    assert "95% below" in post["text"] and "+2,070%" in post["text"]
    assert cm.recovery_post(COINS, recent={"AVAX"})["symbol"] == "DOT"


def test_dilution_post_picks_biggest_gap():
    post = cm.dilution_post(COINS, recent=set())
    assert post["symbol"] == "SUI"  # 30% in circulation
    assert "Only 30%" in post["text"] and "233% more" in post["text"]
    assert "$0.60 a coin" in post["text"]


def test_hype_post_uses_trending():
    post = cm.hype_post(COINS, trending=["PEPE", "SUI"], recent=set())
    assert post["symbol"] == "SUI" and "+12.3%" in post["text"]
    assert cm.hype_post(COINS, trending=["PEPE"], recent=set()) is None


def test_all_data_posts_fit_and_stay_calm():
    for post in (cm.recovery_post(COINS, set()), cm.dilution_post(COINS, set()),
                 cm.hype_post(COINS, ["SUI"], set())):
        assert len(post["text"]) <= 280, post["text"]
        assert not BANNED.search(post["text"]), BANNED.search(post["text"])


def test_stablecoins_and_wrapped_are_ignored():
    assert not cm._is_real_coin(coin("USDT", 1.0, 1.3, -23))
    assert not cm._is_real_coin(coin("XYZ", 60000, 70000, -10, name="Wrapped Bitcoin"))
    assert cm._is_real_coin(COINS[0])


def test_build_post_follows_the_weekday(monkeypatch):
    from services import x_poster

    monkeypatch.setattr(cm, "_top_coins", lambda: COINS)
    tuesday = datetime(2026, 11, 24, 18).timestamp()
    post = x_poster.build_post(state={}, now=tuesday)
    assert post["format"] == "recovery" and post["report"] is None
    wednesday = datetime(2026, 11, 25, 18).timestamp()
    assert x_poster.build_post(state={}, now=wednesday)["text"] in cm.AI_TAKES


def test_named_format_and_fallback(monkeypatch):
    from services import x_poster

    monkeypatch.setattr(cm, "_top_coins", lambda: COINS)
    assert x_poster.build_post(claim_text="governance", state={})["text"] in cm.GOVERNANCE_TAKES

    # A data format that can't be built falls back to a Reality Check.
    monkeypatch.setattr(cm, "_top_coins", lambda: [])
    from tests.test_x_poster import _inputs

    monkeypatch.setattr("services.reality_check.fetch_inputs", lambda s: _inputs())
    monkeypatch.setattr(x_poster, "_trending_symbols", lambda: [])
    post = x_poster.build_post(claim_text="recovery", state={})
    assert post["format"] == "reality" and post["text"].startswith("Someone will tell you")

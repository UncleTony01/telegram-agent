import re
from datetime import datetime

import pytest

import config
from services import x_poster
from services.reality_check import analyse, parse_claim

BANNED = re.compile(
    r"🔥|🔴|🟢|🚨|💀|🚀|crash|dump|moon|explode|panic|fomo|bloodbath|knife|squeeze|huge|massive|urgent|act now|don't miss|buy|sell|https?://",
    re.IGNORECASE,
)


def _inputs(name="Avalanche", sym="avax", price=6.68, mcap=2.98e9, circ=446e6, max_supply=720e6, ath=144.96):
    top = [
        {"id": "bitcoin", "symbol": "btc", "market_cap": 1.7e12},
        {"id": "ethereum", "symbol": "eth", "market_cap": 3.6e11},
        {"id": "solana", "symbol": "sol", "market_cap": 4.27e10},
        {"id": "toncoin", "symbol": "ton", "market_cap": 5e9},
    ]
    coin = {"id": name.lower(), "name": name, "symbol": sym, "current_price": price, "market_cap": mcap,
            "market_cap_rank": 25, "circulating_supply": circ, "max_supply": max_supply, "ath": ath}
    return {"coin": coin, "top": top, "prices": [[0, 5.9], [1, 15.0]]}


@pytest.mark.parametrize("claim", ["AVAX 10x", "AVAX 100B", "AVAX $20", "AVAX 1000x"])
def test_post_fits_and_is_calm(claim):
    r = analyse(parse_claim("/check " + claim), _inputs())
    text = x_poster.format_post(r)
    assert len(text) <= 280
    assert text.startswith("Someone will tell you $AVAX")
    assert text.rstrip().endswith("(Data, not advice)")
    assert "Data, not advice" in text
    assert not BANNED.search(text), BANNED.search(text)


def test_long_post_drops_optional_lines():
    r = analyse(parse_claim("/check AVAX 10x"), _inputs(name="A" * 40))
    r["passes"] = ["VERYLONGTICKER" * 3] * 3
    text = x_poster.format_post(r)
    assert len(text) <= 280


def test_pick_symbol_prefers_trending_and_skips_recent():
    now = 1_000_000_000
    state = {"recent": {"PEPE": now - 3 * 86400}}
    assert x_poster.pick_symbol(state, now, trending=["PEPE", "SUI"]) == "SUI"
    # recent post older than 14 days may repeat
    state = {"recent": {"PEPE": now - 20 * 86400}}
    assert x_poster.pick_symbol(state, now, trending=["PEPE"]) == "PEPE"


def test_pick_symbol_rotates_fallback():
    state = {}
    first = x_poster.pick_symbol(state, 0, trending=[])
    second = x_poster.pick_symbol(state, 0, trending=[])
    assert first == x_poster.FALLBACK_COINS[0] and second == x_poster.FALLBACK_COINS[1]


@pytest.fixture
def daily(tmp_path, monkeypatch):
    monkeypatch.setattr(x_poster, "STATE_FILE", tmp_path / "state.json")
    sent, posted, ledger = [], [], []
    monkeypatch.setattr(x_poster, "_send_owner", sent.append)
    monkeypatch.setattr(x_poster, "send_draft", lambda c, t, h, **k: sent.append(h + "\n" + t))
    monkeypatch.setattr(config, "OWNER_CHAT_ID", "1", raising=False)
    monkeypatch.setattr(x_poster, "post_to_x", lambda t: posted.append(t) or "123")
    monkeypatch.setattr(x_poster, "_trending_symbols", lambda: ["AVAX"])
    monkeypatch.setattr("services.reality_check.fetch_inputs", lambda s: _inputs())
    monkeypatch.setattr("services.hype_ledger.record_check", lambda r: ledger.append(r))
    monkeypatch.setattr(config, "X_POST_HOUR", 18, raising=False)
    return sent, posted, ledger


def _ts(hour):
    return datetime(2026, 11, 23, hour, 5).timestamp()


def test_preview_mode_sends_draft_once_a_day(daily, monkeypatch):
    sent, posted, ledger = daily
    for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"):
        monkeypatch.setattr(config, k, None, raising=False)
    assert x_poster.maybe_post_daily(_ts(17)) is None  # too early
    assert x_poster.maybe_post_daily(_ts(18))
    assert x_poster.maybe_post_daily(_ts(19)) is None  # already done today
    assert posted == [] and len(sent) == 1 and "ready" in sent[0]
    assert len(ledger) == 1


def test_live_mode_posts(daily, monkeypatch):
    sent, posted, ledger = daily
    for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"):
        monkeypatch.setattr(config, k, "x", raising=False)
    x_poster.maybe_post_daily(_ts(18))
    assert len(posted) == 1 and "Posted" in sent[0]


def test_live_failure_does_not_repeat(daily, monkeypatch):
    sent, posted, ledger = daily
    for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"):
        monkeypatch.setattr(config, k, "x", raising=False)

    def boom(t):
        raise RuntimeError("X API 402: no credits")

    monkeypatch.setattr(x_poster, "post_to_x", boom)
    x_poster.maybe_post_daily(_ts(18))
    assert x_poster.maybe_post_daily(_ts(19)) is None
    assert len(sent) == 1 and "didn't go out" in sent[0]


def test_oauth_signature_matches_x_docs_example(monkeypatch):
    # Example from X's "Creating a signature" documentation.
    monkeypatch.setattr(x_poster.secrets, "token_hex", lambda n: "kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg")
    monkeypatch.setattr(x_poster.time, "time", lambda: 1318622958)
    keys = {"api_key": "xvz1evFS4wEEPTGEFPHBog", "api_secret": "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw",
            "access_token": "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb",
            "access_secret": "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE"}
    extra = {"status": "Hello Ladies + Gentlemen, a signed OAuth request!", "include_entities": "true"}
    header = x_poster._oauth_header("POST", "https://api.twitter.com/1.1/statuses/update.json", keys, extra)
    assert x_poster._oauth_header.last_signature == "hCtSmYh+iHYCEqBWrE7C7hYmtUk="
    assert header.startswith("OAuth ") and "oauth_signature=" in header


def test_xpost_is_owner_only(monkeypatch):
    sent = []
    monkeypatch.setattr("services.telegram_service.send_message", lambda c, t, **k: sent.append(t))
    monkeypatch.setattr(config, "OWNER_CHAT_ID", "1", raising=False)
    x_poster.handle_xpost_command("2", "/xpost")
    assert "owner" in sent[0]


def test_intent_link_prefills_post():
    from urllib.parse import parse_qs, urlparse

    text = "Reality Check: $AVAX at 10x = $66.8\nData, not advice."
    url = x_poster.intent_link(text)
    assert url.startswith("https://x.com/intent/post?")
    assert parse_qs(urlparse(url).query)["text"][0] == text


def test_send_draft_sends_card_with_caption_and_button(monkeypatch):
    photos, texts = [], []
    monkeypatch.setattr("services.telegram_service.send_photo",
                        lambda c, b, **k: photos.append((b, k)) or {"ok": True})
    monkeypatch.setattr("services.telegram_service.send_message", lambda c, t, **k: texts.append(t))
    x_poster.send_draft("1", "A < B & C", "📝 Draft", fmt="ai")
    png, kwargs = photos[0]
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and not texts
    assert "<pre>A &lt; B &amp; C</pre>" in kwargs["caption"] and kwargs["parse_mode"] == "HTML"
    button = kwargs["reply_markup"]["inline_keyboard"][0][0]
    assert button["text"] == "✍️ Post on X" and button["url"].startswith("https://x.com/intent/post?")


def test_send_draft_falls_back_to_text_when_photo_fails(monkeypatch):
    texts = []
    monkeypatch.setattr("services.telegram_service.send_photo", lambda c, b, **k: None)
    monkeypatch.setattr("services.telegram_service.send_message", lambda c, t, **k: texts.append(t))
    x_poster.send_draft("1", "hello", "📝 Draft")
    assert "<pre>hello</pre>" in texts[0]

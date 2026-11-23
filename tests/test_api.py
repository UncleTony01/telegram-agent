import pytest
from fastapi.testclient import TestClient

from api import server
from tests.test_x_poster import _inputs


@pytest.fixture
def client(monkeypatch):
    server._cache.clear()
    calls = []
    monkeypatch.setattr(
        "services.reality_check.fetch_inputs",
        lambda s: calls.append(s) or (_inputs() if s == "AVAX" else None),
    )
    monkeypatch.setattr("services.hype_ledger.record_check", lambda r: None)
    c = TestClient(server.create_app(with_payments=False))
    c.calls = calls
    return c


def test_info_and_health_are_free(client):
    assert client.get("/health").json() == {"ok": True}
    info = client.get("/").json()
    assert "x402" in info["payment"] and "/check" in info["paid_endpoint"]


def test_check_returns_maths(client):
    r = client.get("/check", params={"claim": "AVAX 100B"})
    assert r.status_code == 200
    body = r.json()
    assert body["coin"]["symbol"] == "AVAX"
    assert body["target"]["market_cap_usd"] == 100e9
    assert body["target"]["multiple_needed"] == pytest.approx(100e9 / 446e6 / 6.68)
    assert "<b>" not in body["summary"] and "Reality Check" in body["summary"]
    assert "buy or sell" in body["disclaimer"]


def test_errors_are_not_2xx_so_not_charged(client):
    assert client.get("/check", params={"claim": "nonsense"}).status_code == 400
    assert client.get("/check", params={"claim": "ZZZZ 10x"}).status_code == 404
    assert client.get("/check").status_code == 422


def test_market_data_down_is_503(client, monkeypatch):
    def boom(s):
        raise RuntimeError("429")

    monkeypatch.setattr("services.reality_check.fetch_inputs", boom)
    assert client.get("/check", params={"claim": "SOL 10x"}).status_code == 503


def test_cache_avoids_repeat_coingecko_calls(client):
    client.get("/check", params={"claim": "AVAX 100B"})
    client.get("/check", params={"claim": "AVAX 10x"})
    assert client.calls == ["AVAX"]


def test_rate_limit(client):
    codes = [client.get("/health").status_code for _ in range(server.RATE_LIMIT_PER_MINUTE + 2)]
    assert codes[0] == 200 and codes[-1] == 429


def test_payments_require_pay_to(monkeypatch):
    monkeypatch.setattr(server.config, "X402_PAY_TO", None, raising=False)
    with pytest.raises(RuntimeError):
        server.create_app(with_payments=True)

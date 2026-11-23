"""Uncle Tony Reality Check API, paid per request with x402.

    GET /                         free: what this is and how to pay
    GET /health                   free: liveness
    GET /check?claim=AVAX 100B    paid ($0.01 USDC by default): the Reality Check as JSON

How payment works (x402): a request without payment gets HTTP 402 and a
PAYMENT-REQUIRED header describing the price, network and address. An x402
client signs a USDC authorisation and repeats the request with a
PAYMENT-SIGNATURE header. The facilitator verifies it, the answer is built, and
only then is the payment settled. If the answer fails (bad claim, unknown coin,
market data down) the status is 4xx/5xx and nothing is settled, so the buyer
pays nothing.

It starts on Base Sepolia (test USDC, no real money) with the free x402.org
facilitator. Settings live in .env, see .env.example.

Run: .venv/bin/uvicorn api.server:app --host 127.0.0.1 --port 8402
"""
from __future__ import annotations

import html
import re
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Optional, Tuple

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import config
from utils.logger import get_logger

logger = get_logger("api")

NETWORK_NAMES = {"eip155:84532": "Base Sepolia (testnet, test USDC)", "eip155:8453": "Base (real USDC)"}
CACHE_SECONDS = 120
RATE_LIMIT_PER_MINUTE = 30
DISCLAIMER = "Maths on public market data. Not financial advice; it never says buy or sell."


# ------------------------------ Market data cache -------------------------
_cache: Dict[str, Tuple[float, Optional[Dict]]] = {}
_cache_lock = threading.Lock()


def _inputs_for(symbol: str) -> Optional[Dict]:
    """fetch_inputs with a short cache, to stay inside CoinGecko's free limits."""
    from services.reality_check import fetch_inputs

    now = time.time()
    with _cache_lock:
        hit = _cache.get(symbol)
        if hit and now - hit[0] < CACHE_SECONDS:
            return hit[1]
    data = fetch_inputs(symbol)
    with _cache_lock:
        _cache[symbol] = (now, data)
    return data


# ------------------------------ Report as JSON ----------------------------
def _plain(text: str) -> str:
    return html.unescape(re.sub(r"</?[a-z]+>", "", text))


def report_json(r: Dict) -> Dict[str, Any]:
    from services.reality_check import format_report

    year = None
    if r.get("year"):
        y = r["year"]
        year = {
            "low": y["low"],
            "high": y["high"],
            "last_at_or_above_target": y["last_at_target"].date().isoformat() if y.get("last_at_target") else None,
        }
    return {
        "claim": r["claim"].text,
        "claim_kind": r["claim"].kind,
        "coin": {"id": r.get("coin_id"), "symbol": r["symbol"], "name": r["name"]},
        "now": {"price_usd": r["price"], "market_cap_usd": r["mcap"], "rank": r["rank_now"]},
        "target": {
            "price_usd": r["target_price"],
            "market_cap_usd": r["target_mcap"],
            "multiple_needed": r["multiple"],
            "rank_today_at_target": r["rank_at_target"],
            "would_pass": r["passes"],
        },
        "supply": r["dilution"],
        "past_year": year,
        "all_time_high_usd": r["ath"],
        "summary": _plain(format_report(r)),
        "disclaimer": DISCLAIMER,
        "source": "CoinGecko",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


# ------------------------------ Rate limit ---------------------------------
class RateLimit(BaseHTTPMiddleware):
    """Simple per-IP limit, so fake payment headers can't flood the facilitator."""

    def __init__(self, app, per_minute: int = RATE_LIMIT_PER_MINUTE):
        super().__init__(app)
        self.per_minute = per_minute
        self.hits: Dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
            request.client.host if request.client else "?"
        )
        now = time.time()
        q = self.hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= self.per_minute:
            return JSONResponse({"error": "Too many requests. Try again in a minute."}, status_code=429)
        q.append(now)
        return await call_next(request)


# ------------------------------ App ---------------------------------------
def _price() -> str:
    return getattr(config, "X402_PRICE", "$0.01")


def _network() -> str:
    return getattr(config, "X402_NETWORK", "eip155:84532")


def create_app(with_payments: bool = True) -> FastAPI:
    app = FastAPI(title="Uncle Tony Reality Check API", docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/")
    def info():
        return {
            "name": "Uncle Tony Reality Check API",
            "what": "Checks a crypto price claim against the maths: implied market cap, the rank that "
                    "means today, coins it would pass, supply still to come, past-year range, all-time high.",
            "paid_endpoint": "GET /check?claim=AVAX%20100B   (also 'AVAX $20' or 'SOL 10x')",
            "price": f"{_price()} USDC per request",
            "network": NETWORK_NAMES.get(_network(), _network()),
            "pay_to": getattr(config, "X402_PAY_TO", None),
            "payment": "x402 (https://x402.org). Unpaid requests get HTTP 402 with the payment details. "
                       "Failed answers are not charged.",
            "disclaimer": DISCLAIMER,
        }

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/check")
    def check(claim: str = Query(..., max_length=60, description="e.g. AVAX 100B, AVAX $20, SOL 10x")):
        from services.reality_check import analyse, parse_claim

        parsed = parse_claim("/check " + claim)
        if not parsed:
            return JSONResponse(
                {"error": "Couldn't read the claim. Use e.g. 'AVAX 100B', 'AVAX $20' or 'SOL 10x'."},
                status_code=400,
            )
        try:
            inputs = _inputs_for(parsed.symbol)
        except Exception as e:
            logger.warning("API market data failed: %s", e)
            return JSONResponse({"error": "Market data is unavailable right now. Not charged."}, status_code=503)
        if not inputs:
            return JSONResponse({"error": f"Unknown coin: {parsed.symbol}. Not charged."}, status_code=404)
        report = analyse(parsed, inputs)
        try:
            from services.hype_ledger import record_check

            record_check(report)
        except Exception as e:
            logger.warning("Hype ledger write failed: %s", e)
        return report_json(report)

    if with_payments:
        _add_payments(app)
    app.add_middleware(RateLimit)  # added last = runs first
    return app


def _add_payments(app: FastAPI) -> None:
    from x402 import x402ResourceServer
    from x402.http import FacilitatorConfig, HTTPFacilitatorClient
    from x402.http.middleware.fastapi import PaymentMiddlewareASGI
    from x402.mechanisms.evm.exact import ExactEvmServerScheme

    pay_to = getattr(config, "X402_PAY_TO", None)
    if not pay_to:
        raise RuntimeError("X402_PAY_TO is not set: the wallet address that receives payments.")
    facilitator = HTTPFacilitatorClient(
        FacilitatorConfig(url=getattr(config, "X402_FACILITATOR_URL", "https://x402.org/facilitator"))
    )
    server = x402ResourceServer(facilitator)
    server.register("eip155:*", ExactEvmServerScheme())
    routes = {
        "GET /check": {
            "accepts": {"scheme": "exact", "payTo": pay_to, "price": _price(), "network": _network()},
            "description": "Reality Check of a crypto price claim (JSON).",
            "mimeType": "application/json",
        }
    }
    app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)


app = create_app(with_payments=bool(getattr(config, "X402_PAY_TO", None)))

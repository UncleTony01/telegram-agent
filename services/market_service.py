import re
from typing import List, Dict, Any

import requests


COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"


def extract_symbols(text: str) -> List[str]:
    pattern = r"\b(BTC|ETH|SOL|XRP|DOGE|ADA|BNB|AVAX|TRX|TON|LINK|DOT|MATIC|SHIB)\b"
    matches = re.findall(pattern, text.upper())
    return list(dict.fromkeys(matches))


def _fetch_json(url: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def get_price_data(symbol: str) -> Dict[str, Any]:
    symbol = symbol.upper()
    coin_id = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "XRP": "ripple",
        "DOGE": "dogecoin",
        "ADA": "cardano",
        "BNB": "binancecoin",
        "AVAX": "avalanche-2",
        "TRX": "tron",
        "TON": "the-open-network",
        "LINK": "chainlink",
        "DOT": "polkadot",
        "MATIC": "matic-network",
        "SHIB": "shiba-inu",
    }.get(symbol)

    if not coin_id:
        return {}

    payload = _fetch_json(
        f"{COINGECKO_BASE_URL}/simple/price",
        params={"ids": coin_id, "vs_currencies": "usd", "include_24hr_change": "true", "include_market_cap": "true"},
    )

    data = payload.get(coin_id, {})
    if not data:
        return {}

    return {
        "symbol": symbol,
        "price_usd": data.get("usd"),
        "change_24h": data.get("usd_24h_change"),
        "market_cap_usd": data.get("usd_market_cap"),
    }


def build_market_context(symbols: List[Any]) -> str:
    if not symbols:
        return ""

    entries = []
    for item in symbols:
        if isinstance(item, dict):
            data = item
            symbol = data.get("symbol", "")
        else:
            symbol = str(item).upper()
            data = get_price_data(symbol)

        if not data:
            continue
        change = data.get("change_24h")
        change_text = f"{change:+.1f}%" if isinstance(change, (int, float)) else "n/a"
        price_text = str(data['price_usd']) if data.get('price_usd') is not None else 'n/a'
        entries.append(f"- {data['symbol']}: {price_text} ({change_text})")

    return "Current market data:\n" + "\n".join(entries) if entries else ""

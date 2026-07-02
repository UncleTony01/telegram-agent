import re
from typing import List, Dict, Any, Optional

import requests


COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# Maps common ticker symbols to CoinGecko coin IDs
SYMBOL_TO_COIN_ID: Dict[str, str] = {
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
    "HYPE": "hyperliquid",
    "SUI": "sui",
    "OKB": "okb",
    "ARB": "arbitrum",
    "APT": "aptos",
    "SEI": "sei-network",
    "PEPE": "pepe",
    "OP": "optimism",
    "INJ": "injective-protocol",
    "RUNE": "thorchain",
    "WIF": "dogwifcoin",
    "NOT": "notcoin",
}

# Build a regex from all known symbols, sorted longest-first to match multi-char tokens
_SYMBOLS_SORTED = sorted(SYMBOL_TO_COIN_ID.keys(), key=len, reverse=True)
_SYMBOL_PATTERN = re.compile(r"\b(" + "|".join(_SYMBOLS_SORTED) + r")\b", re.IGNORECASE)


def extract_symbols(text: str) -> List[str]:
    """Extract known crypto symbols from text, preserving order of first appearance."""
    matches = _SYMBOL_PATTERN.findall(text)
    seen: set = set()
    result: list[str] = []
    for m in matches:
        upper = m.upper()
        if upper not in seen:
            seen.add(upper)
            result.append(upper)
    return result


def resolve_coin_id(symbol: str) -> Optional[str]:
    """Return the CoinGecko coin ID for a symbol, or None if unknown."""
    return SYMBOL_TO_COIN_ID.get(symbol.upper())


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def _fetch_json(url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def get_price_data(symbol: str) -> Dict[str, Any]:
    """Quick price snapshot via /simple/price (lightweight)."""
    coin_id = resolve_coin_id(symbol)
    if not coin_id:
        return {}

    payload = _fetch_json(
        f"{COINGECKO_BASE_URL}/simple/price",
        params={
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_market_cap": "true",
        },
    )

    data = payload.get(coin_id, {})
    if not data:
        return {}

    return {
        "symbol": symbol.upper(),
        "price_usd": data.get("usd"),
        "change_24h": data.get("usd_24h_change"),
        "market_cap_usd": data.get("usd_market_cap"),
    }


def get_rich_market_data(symbol: str) -> Dict[str, Any]:
    """Detailed market data via /coins/{id} (richer, one request per symbol)."""
    coin_id = resolve_coin_id(symbol)
    if not coin_id:
        return {}

    payload = _fetch_json(
        f"{COINGECKO_BASE_URL}/coins/{coin_id}",
        params={
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false",
        },
    )

    md = payload.get("market_data") or {}
    if not md:
        return {}

    def _usd(key: str) -> Optional[float]:
        """Extract the ``usd`` value from a nested dict, or return the raw value
        if it is already a scalar (e.g. ``price_change_percentage_24h``)."""
        val = md.get(key)
        if isinstance(val, dict):
            return val.get("usd")
        return val

    return {
        "symbol": symbol.upper(),
        "name": payload.get("name", ""),
        "price_usd": _usd("current_price"),
        "change_24h": _usd("price_change_percentage_24h"),
        "high_24h_usd": _usd("high_24h"),
        "low_24h_usd": _usd("low_24h"),
        "volume_usd": _usd("total_volume"),
        "market_cap_usd": _usd("market_cap"),
        "market_cap_rank": md.get("market_cap_rank"),
    }


def _fmt_price(val) -> str:
    if val is None:
        return "n/a"
    if isinstance(val, float) and val < 1:
        return f"${val:.6f}"
    return f"${val:,.2f}"


def _fmt_change(val) -> str:
    if val is None:
        return "n/a"
    return f"{val:+.2f}%"


def _fmt_big(val) -> str:
    """Format large numbers (volume, market cap) as compact strings."""
    if val is None:
        return "n/a"
    val = float(val)
    if val >= 1_000_000_000_000:
        return f"${val / 1_000_000_000_000:.1f}T"
    if val >= 1_000_000_000:
        return f"${val / 1_000_000_000:.1f}B"
    if val >= 1_000_000:
        return f"${val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"${val / 1_000:.1f}K"
    return f"${val:,.0f}"


def build_market_context(symbols: List[Any]) -> str:
    """Build a readable market data block for Hermes.

    Accepts either raw symbol strings (fetches rich data) or pre-fetched dicts
    returned by ``get_rich_market_data()``.
    """
    if not symbols:
        return ""

    blocks: list[str] = []

    for item in symbols:
        if isinstance(item, dict):
            data = item
        else:
            data = get_rich_market_data(item)

        if not data or data.get("price_usd") is None:
            continue

        name = data.get("name", data["symbol"])
        rank = data.get("market_cap_rank")

        rank_str = f"  #{rank}" if rank else ""
        lines = [
            f"── {name} ({data['symbol']}) ──{rank_str}",
            "",
            f"Price:         {_fmt_price(data.get('price_usd'))}",
            f"24h Change:    {_fmt_change(data.get('change_24h'))}",
            f"24h High:      {_fmt_price(data.get('high_24h_usd'))}",
            f"24h Low:       {_fmt_price(data.get('low_24h_usd'))}",
            f"24h Volume:    {_fmt_big(data.get('volume_usd'))}",
            f"Market Cap:    {_fmt_big(data.get('market_cap_usd'))}",
        ]

        if rank:
            lines.append(f"Rank:          #{rank}")

        blocks.append("\n".join(lines))

    return "Live Market Data\n\n" + "\n\n".join(blocks) if blocks else ""

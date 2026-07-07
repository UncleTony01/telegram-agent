"""OKX market data service.

Wraps the local ``okx`` CLI (``@okx_ai/okx-trade-cli``) via ``subprocess``
and returns parsed JSON as Python dictionaries.

Every method uses ``--json`` for machine-readable output and raises
``OKXError`` on non-zero exit codes.
"""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import get_logger

logger = get_logger(__name__)

# -- Constants -----------------------------------------------------------

OKX_CMD = "okx"

# Default instrument ID template for spot tickers
DEFAULT_INST_ID_TEMPLATE = "{symbol}-USDT"

# Number of decimal places for prices < 1 in _fmt_price
SMALL_PRICE_DIGITS = 6

# Known crypto symbols for recognition in user text
KNOWN_SYMBOLS = frozenset({
    "BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "BNB", "AVAX", "TRX",
    "TON", "LINK", "DOT", "MATIC", "SHIB", "HYPE", "SUI", "OKB", "ARB",
    "APT", "SEI", "PEPE", "OP", "INJ", "RUNE", "WIF", "NOT",
})

# Build a regex from all known symbols, sorted longest-first to match multi-char tokens
_SYMBOLS_SORTED = sorted(KNOWN_SYMBOLS, key=len, reverse=True)
_SYMBOL_PATTERN = re.compile(r"\b(" + "|".join(_SYMBOLS_SORTED) + r")\b", re.IGNORECASE)

# -- Exception -----------------------------------------------------------


class OKXError(Exception):
    """Raised when the ``okx`` CLI exits with a non-zero code."""


# -- Internal helpers ----------------------------------------------------


def _run_okx(args: List[str]) -> Any:
    """Run ``okx --json <args>`` and return the parsed JSON output.

    Raises
    ------
    OKXError
        If the CLI returns a non-zero exit code.
    FileNotFoundError
        If the ``okx`` binary is not installed.
    """
    cmd = [OKX_CMD, "--json"] + args
    logger.debug("Running: %s", " ".join(cmd))

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        raise OKXError(
            f"OKX CLI not found. Install it via: npx @okx_ai/okx-trade-cli"
        ) from None

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        stdout = proc.stdout.strip()
        detail = stderr or stdout or "unknown error"
        raise OKXError(f"okx CLI error (exit={proc.returncode}): {detail}")

    # The CLI may return an empty body on some endpoints
    if not proc.stdout.strip():
        return None

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise OKXError(f"Failed to parse OKX JSON output: {exc}") from exc


def _to_inst_id(symbol: str, *, template: str = DEFAULT_INST_ID_TEMPLATE) -> str:
    """Convert a short symbol (``BTC``) to an OKX instrument ID (``BTC-USDT``)."""
    return template.format(symbol=symbol.upper())


def _float(val: Any) -> Optional[float]:
    """Safely cast a value to float, returning None on failure."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _fmt_price(val: Optional[float]) -> str:
    """Format a price value for display."""
    if val is None:
        return "n/a"
    if val < 1:
        return f"${val:.{SMALL_PRICE_DIGITS}f}"
    return f"${val:,.2f}"


def _fmt_change(val: Optional[float]) -> str:
    """Format a 24h change percentage for display."""
    if val is None:
        return "n/a"
    return f"{val:+.2f}%"


def _fmt_big(val: Optional[float]) -> str:
    """Format large numbers (volume, OI) as compact strings."""
    if val is None:
        return "n/a"
    if val >= 1_000_000_000_000:
        return f"${val / 1_000_000_000_000:.1f}T"
    if val >= 1_000_000_000:
        return f"${val / 1_000_000_000:.1f}B"
    if val >= 1_000_000:
        return f"${val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"${val / 1_000:.1f}K"
    return f"${val:,.0f}"


# -- Symbol extraction ---------------------------------------------------


def extract_symbols(text: str) -> List[str]:
    """Extract known crypto symbols from text, preserving order of first appearance."""
    if not text:
        return []
    matches = _SYMBOL_PATTERN.findall(text)
    seen: set = set()
    result: list[str] = []
    for m in matches:
        upper = m.upper()
        if upper not in seen:
            seen.add(upper)
            result.append(upper)
    return result


# -- Public API ----------------------------------------------------------


def get_ticker(symbol: str, *, inst_id: Optional[str] = None) -> Dict[str, Any]:
    """Fetch the latest ticker for an instrument.

    Parameters
    ----------
    symbol : str
        Short symbol such as ``BTC``, ``ETH``. Ignored when ``inst_id`` is set.
    inst_id : str, optional
        Full OKX instrument ID (e.g. ``BTC-USDT``). If given, ``symbol`` is
        ignored.

    Returns
    -------
    dict
        A dict with keys:
        ``symbol``, ``price_usd``, ``change_24h``, ``high_24h_usd``,
        ``low_24h_usd``, ``volume_usd``, ``bid_price``, ``ask_price``,
        ``spread``, ``raw``.
    """
    inst = inst_id or _to_inst_id(symbol)
    data = _run_okx(["market", "ticker", inst])

    if not data or not isinstance(data, list) or len(data) == 0:
        return {}

    row = data[0]
    last = _float(row.get("last"))
    open24h = _float(row.get("open24h"))
    high = _float(row.get("high24h"))
    low = _float(row.get("low24h"))
    volume = _float(row.get("volCcy24h"))
    bid = _float(row.get("bidPx"))
    ask = _float(row.get("askPx"))

    change_24h = None
    if last is not None and open24h is not None and open24h != 0:
        change_24h = ((last - open24h) / open24h) * 100

    spread = None
    if bid is not None and ask is not None:
        spread = ask - bid

    return {
        "symbol": symbol.upper(),
        "price_usd": last,
        "change_24h": change_24h,
        "high_24h_usd": high,
        "low_24h_usd": low,
        "volume_usd": volume,
        "bid_price": bid,
        "ask_price": ask,
        "spread": spread,
        "source": "okx",
        "raw": row,
    }


def get_orderbook(
    symbol: str,
    *,
    inst_id: Optional[str] = None,
    depth: int = 25,
) -> Dict[str, Any]:
    """Fetch order book depth for an instrument.

    Parameters
    ----------
    symbol : str
        Short symbol such as ``BTC``.
    inst_id : str, optional
        Full OKX instrument ID.
    depth : int
        Number of asks/bids to return (max 400). Default 25.

    Returns
    -------
    dict
        ``asks``, ``bids`` (each a list of ``[price, size, num_orders]``),
        ``ts``, ``symbol``.
    """
    inst = inst_id or _to_inst_id(symbol)
    data = _run_okx(["market", "orderbook", inst, "--sz", str(depth)])

    if not data or not isinstance(data, list) or len(data) == 0:
        return {}

    row = data[0]

    def _format_side(entries: List[List[str]]) -> List[Dict[str, Any]]:
        return [
            {
                "price": _float(e[0]),
                "size": _float(e[1]),
                "orders": int(e[3]) if len(e) > 3 and e[3] else 0,
            }
            for e in entries
        ]

    return {
        "symbol": symbol.upper(),
        "asks": _format_side(row.get("asks", [])),
        "bids": _format_side(row.get("bids", [])),
        "ts": row.get("ts"),
        "source": "okx",
    }


def get_candles(
    symbol: str,
    *,
    inst_id: Optional[str] = None,
    bar: str = "1H",
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Fetch candlestick (OHLCV) data.

    Parameters
    ----------
    symbol : str
        Short symbol such as ``BTC``.
    inst_id : str, optional
        Full OKX instrument ID.
    bar : str
        Candle size: ``1m``, ``5m``, ``15m``, ``30m``, ``1H``, ``4H``, ``1D``,
        ``1W``, ``1M``. Default ``1H``.
    limit : int
        Number of candles (max 300). Default 50.

    Returns
    -------
    list of dict
        Each candle: ``ts`` (iso millis), ``o``, ``h``, ``l``, ``c``, ``vol``,
        ``vol_ccy``.
    """
    inst = inst_id or _to_inst_id(symbol)
    data = _run_okx(
        ["market", "candles", inst, "--bar", bar, "--limit", str(limit)]
    )

    if not data or not isinstance(data, list) or len(data) == 0:
        return []

    # Candles come as arrays of strings: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
    candles = []
    for row in data:
        if isinstance(row, dict):
            # Some newer CLI versions may return dicts
            candles.append(row)
        elif isinstance(row, list) and len(row) >= 7:
            candles.append(
                {
                    "ts": row[0],
                    "o": _float(row[1]),
                    "h": _float(row[2]),
                    "l": _float(row[3]),
                    "c": _float(row[4]),
                    "vol": _float(row[5]),
                    "vol_ccy": _float(row[6]),
                }
            )

    return candles


def get_funding(
    symbol: str,
    *,
    inst_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch current funding rate for a perpetual swap instrument.

    The instrument ID must be a SWAP, e.g. ``BTC-USDT-SWAP``.

    Parameters
    ----------
    symbol : str
        Short symbol such as ``BTC``. Converted to ``BTC-USDT-SWAP`` by
        default.
    inst_id : str, optional
        Full OKX swap instrument ID (e.g. ``BTC-USDT-SWAP``).

    Returns
    -------
    dict
        ``funding_rate``, ``next_funding_time``, ``funding_time``,
        ``sett_funding_rate``, ``symbol``.
    """
    inst = inst_id or f"{symbol.upper()}-USDT-SWAP"
    data = _run_okx(["market", "funding-rate", inst])

    if not data or not isinstance(data, list) or len(data) == 0:
        return {}

    row = data[0]
    return {
        "symbol": symbol.upper(),
        "inst_id": inst,
        "funding_rate": _float(row.get("fundingRate")),
        "funding_time": row.get("fundingTime"),
        "next_funding_rate": row.get("nextFundingRate") or None,
        "next_funding_time": row.get("nextFundingTime"),
        "sett_funding_rate": _float(row.get("settFundingRate")),
        "premium": _float(row.get("premium")),
        "source": "okx",
        "raw": row,
    }


def get_open_interest(
    symbol: str,
    *,
    inst_id: Optional[str] = None,
    inst_type: str = "SWAP",
) -> Dict[str, Any]:
    """Fetch open interest for a perpetual swap instrument.

    Parameters
    ----------
    symbol : str
        Short symbol such as ``BTC``.
    inst_id : str, optional
        Full OKX instrument ID (e.g. ``BTC-USDT-SWAP``).
    inst_type : str
        Instrument type: ``SWAP``, ``FUTURES``, or ``OPTION``. Default ``SWAP``.

    Returns
    -------
    dict
        ``oi`` (open interest in contract units), ``oi_usd`` (in USD),
        ``oi_ccy`` (in settlement currency), ``symbol``.
    """
    inst = inst_id or f"{symbol.upper()}-USDT-SWAP"
    data = _run_okx(
        ["market", "open-interest", "--instType", inst_type, "--instId", inst]
    )

    if not data or not isinstance(data, list) or len(data) == 0:
        return {}

    row = data[0]
    return {
        "symbol": symbol.upper(),
        "inst_id": inst,
        "oi": _float(row.get("oi")),
        "oi_usd": _float(row.get("oiUsd")),
        "oi_ccy": _float(row.get("oiCcy")),
        "ts": row.get("ts"),
        "source": "okx",
        "raw": row,
    }


def _extract_indicator_value(
    payload: Any,
    indicator_name: str,
    *,
    period: Optional[int] = None,
) -> Optional[float]:
    """Extract the latest numeric value from an OKX indicator CLI payload."""
    if not isinstance(payload, list):
        return None

    for item in payload:
        if not isinstance(item, dict):
            continue

        data_items = item.get("data")
        if not isinstance(data_items, list):
            continue

        for data_item in data_items:
            if not isinstance(data_item, dict):
                continue

            timeframes = data_item.get("timeframes")
            if not isinstance(timeframes, dict):
                continue

            for timeframe in timeframes.values():
                if not isinstance(timeframe, dict):
                    continue

                indicators = timeframe.get("indicators")
                if not isinstance(indicators, dict):
                    continue

                series = indicators.get(indicator_name)
                if not isinstance(series, list):
                    continue

                for entry in reversed(series):
                    if not isinstance(entry, dict):
                        continue

                    values = entry.get("values")
                    if not isinstance(values, dict):
                        continue

                    if period is not None:
                        period_key = str(period)
                        if period_key in values:
                            return _float(values[period_key])

                    numeric_values: List[float] = []
                    for value in values.values():
                        parsed = _float(value)
                        if parsed is not None:
                            numeric_values.append(parsed)

                    if numeric_values:
                        return numeric_values[-1]

    return None


def get_market_indicators(symbol: str) -> Dict[str, Any]:
    """Fetch RSI and EMA indicators for a symbol via the OKX CLI."""
    inst = _to_inst_id(symbol)
    indicators: Dict[str, Any] = {
        "rsi": None,
        "ema20": None,
        "ema50": None,
        "trend": "",
    }

    try:
        rsi_payload = _run_okx(
            [
                "market",
                "indicator",
                "rsi",
                inst,
                "--bar",
                "1Dutc",
                "--limit",
                "1",
            ]
        )
        indicators["rsi"] = _extract_indicator_value(rsi_payload, "RSI", period=14)
    except OKXError as exc:
        logger.warning("get_market_indicators RSI failed: %s", exc)

    try:
        ema20_payload = _run_okx(
            [
                "market",
                "indicator",
                "ema",
                inst,
                "--bar",
                "1Dutc",
                "--limit",
                "1",
                "--params",
                "20",
            ]
        )
        indicators["ema20"] = _extract_indicator_value(
            ema20_payload, "EMA", period=20
        )
    except OKXError as exc:
        logger.warning("get_market_indicators EMA20 failed: %s", exc)

    try:
        ema50_payload = _run_okx(
            [
                "market",
                "indicator",
                "ema",
                inst,
                "--bar",
                "1Dutc",
                "--limit",
                "1",
                "--params",
                "50",
            ]
        )
        indicators["ema50"] = _extract_indicator_value(
            ema50_payload, "EMA", period=50
        )
    except OKXError as exc:
        logger.warning("get_market_indicators EMA50 failed: %s", exc)

    price = None
    try:
        ticker = get_ticker(symbol)
        price = ticker.get("price_usd")
    except OKXError as exc:
        logger.warning("get_market_indicators ticker failed: %s", exc)

    ema20 = indicators.get("ema20")
    ema50 = indicators.get("ema50")
    if price is not None and ema20 is not None and ema50 is not None:
        if price > ema20 > ema50:
            indicators["trend"] = "Bullish"
        elif price < ema20 < ema50:
            indicators["trend"] = "Bearish"
        else:
            indicators["trend"] = "Neutral"

    return indicators


def get_market_overview(symbol: str) -> Dict[str, Any]:
    """Aggregate ticker + funding + OI + indicators into a single overview dict.

    This is a convenience method that calls several endpoints and merges the
    results. If any sub-call fails, the missing keys are simply ``None``
    rather than raising.

    Parameters
    ----------
    symbol : str
        Short symbol such as ``BTC``.

    Returns
    -------
    dict
        Top-level keys: ``symbol``, ``price_usd``, ``change_24h``,
        ``high_24h_usd``, ``low_24h_usd``, ``volume_usd``, ``bid_price``,
        ``ask_price``, ``spread``, ``funding_rate``, ``open_interest_usd``,
        ``source``.
    """
    overview: Dict[str, Any] = {
        "symbol": symbol.upper(),
        "source": "okx",
    }

    # Ticker (spot)
    try:
        ticker = get_ticker(symbol)
        overview.update(
            {
                "price_usd": ticker.get("price_usd"),
                "change_24h": ticker.get("change_24h"),
                "high_24h_usd": ticker.get("high_24h_usd"),
                "low_24h_usd": ticker.get("low_24h_usd"),
                "volume_usd": ticker.get("volume_usd"),
                "bid_price": ticker.get("bid_price"),
                "ask_price": ticker.get("ask_price"),
                "spread": ticker.get("spread"),
            }
        )
    except OKXError as exc:
        logger.warning("get_market_overview ticker failed: %s", exc)

    # Funding rate (swap)
    try:
        funding = get_funding(symbol)
        overview["funding_rate"] = funding.get("funding_rate")
    except OKXError as exc:
        logger.warning("get_market_overview funding failed: %s", exc)

    # Open interest (swap)
    try:
        oi = get_open_interest(symbol)
        overview["open_interest_usd"] = oi.get("oi_usd")
    except OKXError as exc:
        logger.warning("get_market_overview OI failed: %s", exc)

    # Technical indicators
    try:
        indicators = get_market_indicators(symbol)
        overview.update(
            {
                "rsi": indicators.get("rsi"),
                "ema20": indicators.get("ema20"),
                "ema50": indicators.get("ema50"),
                "trend": indicators.get("trend"),
            }
        )
    except OKXError as exc:
        logger.warning("get_market_overview indicators failed: %s", exc)

    return overview


def build_market_context(symbols: List[str]) -> str:
    """Build a human-readable market data block for multiple symbols.

    Accepts a list of symbol strings. It iterates
    over each symbol and concatenates the formatted blocks.

    Parameters
    ----------
    symbols : list of str
        Symbol strings such as ``["BTC", "ETH"]``.

    Returns
    -------
    str
        Formatted multi-line string, or empty string if no data.
    """
    if not symbols:
        return ""

    blocks: list[str] = []
    for sym in symbols:
        block = build_okx_context(sym)
        if block:
            blocks.append(block)

    return "Live Market Data\n\n" + "\n\n".join(blocks) if blocks else ""


def build_okx_context(symbol: str) -> str:
    """Build a human-readable market data block for an OKX instrument.

    Parameters
    ----------
    symbol : str
        Short symbol such as ``BTC``.

    Returns
    -------
    str
        Formatted multi-line string, or empty string if no data.
    """
    overview = get_market_overview(symbol)
    if not overview or overview.get("price_usd") is None:
        return ""

    lines = [
        f"── {symbol.upper()}-USDT (OKX) ──",
        "",
        f"Price:           {_fmt_price(overview.get('price_usd'))}",
        f"24h Change:      {_fmt_change(overview.get('change_24h'))}",
        f"24h High:        {_fmt_price(overview.get('high_24h_usd'))}",
        f"24h Low:         {_fmt_price(overview.get('low_24h_usd'))}",
        f"24h Volume:      {_fmt_big(overview.get('volume_usd'))}",
        f"RSI:             {overview.get('rsi') if overview.get('rsi') is not None else 'n/a'}",
        f"EMA20:           {_fmt_price(overview.get('ema20'))}",
        f"EMA50:           {_fmt_price(overview.get('ema50'))}",
        f"Trend:           {overview.get('trend') if overview.get('trend') else 'n/a'}",
    ]

    bid = overview.get("bid_price")
    ask = overview.get("ask_price")
    spread = overview.get("spread")
    if bid is not None and ask is not None:
        lines.append(f"Bid:             {_fmt_price(bid)}")
        lines.append(f"Ask:             {_fmt_price(ask)}")
        if spread is not None:
            lines.append(f"Spread:          {_fmt_price(spread)}")

    fr = overview.get("funding_rate")
    if fr is not None:
        lines.append(f"Funding Rate:    {fr:.6%}")

    oi = overview.get("open_interest_usd")
    if oi is not None:
        lines.append(f"Open Interest:   {_fmt_big(oi)}")

    return "\n".join(lines)

"""Unit tests for the OKX market data service.

All tests mock ``subprocess.run`` so no real CLI calls are made.
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from services.okx_service import (
    OKXError,
    build_okx_context,
    get_candles,
    get_funding,
    get_market_overview,
    get_open_interest,
    get_orderbook,
    get_ticker,
    _fmt_big,
    _fmt_change,
    _fmt_price,
    _float,
    _run_okx,
    _to_inst_id,
)

# ---------------------------------------------------------------------------
# Fake CLI responses
# ---------------------------------------------------------------------------

TICKER_RESPONSE = [
    {
        "instType": "SPOT",
        "instId": "BTC-USDT",
        "last": "58569",
        "lastSz": "0.0005",
        "askPx": "58571.1",
        "askSz": "0.8030151",
        "bidPx": "58571",
        "bidSz": "1.65941875",
        "open24h": "59794.9",
        "high24h": "60688",
        "low24h": "58200",
        "volCcy24h": "1272409632.265621266",
        "vol24h": "21470.09600677",
        "ts": "1782835781966",
        "sodUtc0": "60259",
        "sodUtc8": "58384.1",
    }
]

ORDERBOOK_RESPONSE = [
    {
        "asks": [
            ["58585.9", "2.52359751", "0", "10"],
            ["58586", "0.00055807", "0", "1"],
        ],
        "bids": [
            ["58585.8", "0.78675517", "0", "4"],
            ["58580.2", "0.00001716", "0", "1"],
        ],
        "ts": "1782835794505",
        "seqId": 78220561468,
    }
]

CANDLES_RESPONSE = [
    [
        "1782835200000",
        "58384.1",
        "58636.2",
        "58360.3",
        "58572",
        "107.1515398",
        "6268987.551364333",
        "6268987.551364333",
        "0",
    ],
    [
        "1782831600000",
        "58650",
        "58700",
        "58350",
        "58390",
        "150.0",
        "8775000.0",
        "8775000.0",
        "1",
    ],
]

FUNDING_RESPONSE = [
    {
        "formulaType": "withRate",
        "fundingRate": "0.0000667065786819",
        "fundingTime": "1782864000000",
        "impactValue": "20000.0000000000000000",
        "instId": "BTC-USDT-SWAP",
        "instType": "SWAP",
        "interestRate": "0.0001000000000000",
        "maxFundingRate": "0.00375",
        "method": "current_period",
        "minFundingRate": "-0.00375",
        "nextFundingRate": "",
        "nextFundingTime": "1782892800000",
        "premium": "-0.0003481228668942",
        "prevFundingTime": "1782835200000",
        "settFundingRate": "0.0000641177716092",
        "settState": "settled",
        "ts": "1782835823317",
    }
]

OPEN_INTEREST_RESPONSE = [
    {
        "instId": "BTC-USDT-SWAP",
        "instType": "SWAP",
        "oi": "127850",
        "oiCcy": "127850",
        "oiUsd": "7485678900",
        "ts": "1782835823000",
    }
]


def _mock_run(return_data, returncode=0, stderr=""):
    """Create a mock ``subprocess.run`` that returns the given data."""
    return MagicMock(
        returncode=returncode,
        stdout=json.dumps(return_data),
        stderr=stderr,
    )


class TestHelpers(unittest.TestCase):
    """Test internal helper functions."""

    def test_float_success(self):
        self.assertEqual(_float("58569"), 58569.0)
        self.assertEqual(_float("0.0005"), 0.0005)
        self.assertEqual(_float(65000), 65000.0)

    def test_float_none(self):
        self.assertIsNone(_float(None))

    def test_float_invalid(self):
        self.assertIsNone(_float("not-a-number"))

    def test_to_inst_id(self):
        self.assertEqual(_to_inst_id("BTC"), "BTC-USDT")
        self.assertEqual(_to_inst_id("eth"), "ETH-USDT")
        self.assertEqual(_to_inst_id("SOL"), "SOL-USDT")

    def test_fmt_price_normal(self):
        self.assertEqual(_fmt_price(58569.0), "$58,569.00")

    def test_fmt_price_small(self):
        self.assertEqual(_fmt_price(0.0045), "$0.004500")

    def test_fmt_price_none(self):
        self.assertEqual(_fmt_price(None), "n/a")

    def test_fmt_change_positive(self):
        self.assertEqual(_fmt_change(1.18), "+1.18%")

    def test_fmt_change_negative(self):
        self.assertEqual(_fmt_change(-2.5), "-2.50%")

    def test_fmt_change_none(self):
        self.assertEqual(_fmt_change(None), "n/a")

    def test_fmt_big_trillions(self):
        self.assertEqual(_fmt_big(1_200_000_000_000), "$1.2T")

    def test_fmt_big_billions(self):
        self.assertEqual(_fmt_big(7_485_678_900), "$7.5B")

    def test_fmt_big_millions(self):
        self.assertEqual(_fmt_big(38_200_000), "$38.2M")

    def test_fmt_big_thousands(self):
        self.assertEqual(_fmt_big(382_000), "$382.0K")

    def test_fmt_big_none(self):
        self.assertEqual(_fmt_big(None), "n/a")

    def test_run_okx_success(self):
        """_run_okx should parse JSON from stdout."""
        with patch("services.okx_service.subprocess.run") as mock_run:
            mock_run.return_value = _mock_run(TICKER_RESPONSE)
            result = _run_okx(["market", "ticker", "BTC-USDT"])
            self.assertEqual(result, TICKER_RESPONSE)

    def test_run_okx_nonzero_exit(self):
        """_run_okx should raise OKXError on non-zero exit."""
        with patch("services.okx_service.subprocess.run") as mock_run:
            mock_run.return_value = _mock_run(
                [], returncode=1, stderr="some error"
            )
            with self.assertRaises(OKXError) as ctx:
                _run_okx(["market", "ticker", "BTC-USDT"])
            self.assertIn("some error", str(ctx.exception))

    def test_run_okx_empty_stdout(self):
        """_run_okx should return None for empty stdout."""
        with patch("services.okx_service.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="", stderr=""
            )
            result = _run_okx(["market", "funding-rate", "BTC-USDT-SWAP"])
            self.assertIsNone(result)

    def test_run_okx_file_not_found(self):
        """_run_okx should raise OKXError when binary is missing."""
        with patch("services.okx_service.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            with self.assertRaises(OKXError) as ctx:
                _run_okx(["market", "ticker", "BTC-USDT"])
            self.assertIn("not found", str(ctx.exception).lower())

    def test_run_okx_invalid_json(self):
        """_run_okx should raise OKXError on invalid JSON."""
        with patch("services.okx_service.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="not json", stderr=""
            )
            with self.assertRaises(OKXError) as ctx:
                _run_okx(["market", "ticker", "BTC-USDT"])
            self.assertIn("parse", str(ctx.exception).lower())


class TestGetTicker(unittest.TestCase):
    """Test ``get_ticker``."""

    @patch("services.okx_service.subprocess.run")
    def test_get_ticker_success(self, mock_run):
        mock_run.return_value = _mock_run(TICKER_RESPONSE)
        result = get_ticker("BTC")
        self.assertEqual(result["symbol"], "BTC")
        self.assertEqual(result["price_usd"], 58569.0)
        self.assertAlmostEqual(result["change_24h"], -2.049, places=2)
        self.assertEqual(result["high_24h_usd"], 60688.0)
        self.assertEqual(result["low_24h_usd"], 58200.0)
        self.assertEqual(result["volume_usd"], 1272409632.2656213)
        self.assertEqual(result["bid_price"], 58571.0)
        self.assertEqual(result["ask_price"], 58571.1)
        self.assertAlmostEqual(result["spread"], 0.1)
        self.assertEqual(result["source"], "okx")
        self.assertIn("raw", result)

    @patch("services.okx_service.subprocess.run")
    def test_get_ticker_with_inst_id(self, mock_run):
        mock_run.return_value = _mock_run(TICKER_RESPONSE)
        result = get_ticker("BTC", inst_id="BTC-USDT")
        self.assertEqual(result["symbol"], "BTC")
        mock_run.assert_called_once()

    @patch("services.okx_service.subprocess.run")
    def test_get_ticker_empty_response(self, mock_run):
        mock_run.return_value = _mock_run([])
        result = get_ticker("FAKE")
        self.assertEqual(result, {})

    @patch("services.okx_service.subprocess.run")
    def test_get_ticker_error_response(self, mock_run):
        mock_run.return_value = _mock_run([], returncode=1, stderr="error")
        with self.assertRaises(OKXError):
            get_ticker("BTC")


class TestGetOrderbook(unittest.TestCase):
    """Test ``get_orderbook``."""

    @patch("services.okx_service.subprocess.run")
    def test_get_orderbook_success(self, mock_run):
        mock_run.return_value = _mock_run(ORDERBOOK_RESPONSE)
        result = get_orderbook("BTC", depth=5)
        self.assertEqual(result["symbol"], "BTC")
        self.assertEqual(len(result["asks"]), 2)
        self.assertEqual(len(result["bids"]), 2)
        self.assertEqual(result["asks"][0]["price"], 58585.9)
        self.assertEqual(result["asks"][0]["size"], 2.52359751)
        self.assertEqual(result["asks"][0]["orders"], 10)
        self.assertEqual(result["bids"][0]["price"], 58585.8)
        self.assertEqual(result["bids"][0]["size"], 0.78675517)
        self.assertEqual(result["bids"][0]["orders"], 4)
        self.assertEqual(result["ts"], "1782835794505")
        self.assertEqual(result["source"], "okx")

    @patch("services.okx_service.subprocess.run")
    def test_get_orderbook_empty(self, mock_run):
        mock_run.return_value = _mock_run([])
        result = get_orderbook("FAKE")
        self.assertEqual(result, {})


class TestGetCandles(unittest.TestCase):
    """Test ``get_candles``."""

    @patch("services.okx_service.subprocess.run")
    def test_get_candles_success(self, mock_run):
        mock_run.return_value = _mock_run(CANDLES_RESPONSE)
        result = get_candles("BTC", bar="1H", limit=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["ts"], "1782835200000")
        self.assertEqual(result[0]["o"], 58384.1)
        self.assertEqual(result[0]["h"], 58636.2)
        self.assertEqual(result[0]["l"], 58360.3)
        self.assertEqual(result[0]["c"], 58572.0)
        self.assertEqual(result[0]["vol"], 107.1515398)
        self.assertEqual(result[0]["vol_ccy"], 6268987.551364333)

    @patch("services.okx_service.subprocess.run")
    def test_get_candles_empty(self, mock_run):
        mock_run.return_value = _mock_run([])
        result = get_candles("FAKE")
        self.assertEqual(result, [])

    @patch("services.okx_service.subprocess.run")
    def test_get_candles_dict_format(self, mock_run):
        """Some CLI versions return dicts instead of arrays."""
        dict_response = [
            {"ts": "1000", "o": "100", "h": "110", "l": "90", "c": "105"}
        ]
        mock_run.return_value = _mock_run(dict_response)
        result = get_candles("BTC", limit=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["ts"], "1000")


class TestGetFunding(unittest.TestCase):
    """Test ``get_funding``."""

    @patch("services.okx_service.subprocess.run")
    def test_get_funding_success(self, mock_run):
        mock_run.return_value = _mock_run(FUNDING_RESPONSE)
        result = get_funding("BTC")
        self.assertEqual(result["symbol"], "BTC")
        self.assertEqual(result["inst_id"], "BTC-USDT-SWAP")
        self.assertAlmostEqual(result["funding_rate"], 6.67065786819e-05)
        self.assertEqual(result["funding_time"], "1782864000000")
        self.assertEqual(result["next_funding_time"], "1782892800000")
        self.assertAlmostEqual(result["sett_funding_rate"], 6.41177716092e-05)
        self.assertIsNone(result["next_funding_rate"])  # empty string → None

    @patch("services.okx_service.subprocess.run")
    def test_get_funding_empty(self, mock_run):
        mock_run.return_value = _mock_run([])
        result = get_funding("FAKE")
        self.assertEqual(result, {})


class TestGetOpenInterest(unittest.TestCase):
    """Test ``get_open_interest``."""

    @patch("services.okx_service.subprocess.run")
    def test_get_open_interest_success(self, mock_run):
        mock_run.return_value = _mock_run(OPEN_INTEREST_RESPONSE)
        result = get_open_interest("BTC")
        self.assertEqual(result["symbol"], "BTC")
        self.assertEqual(result["inst_id"], "BTC-USDT-SWAP")
        self.assertEqual(result["oi"], 127850.0)
        self.assertEqual(result["oi_usd"], 7485678900.0)
        self.assertEqual(result["oi_ccy"], 127850.0)
        self.assertEqual(result["source"], "okx")

    @patch("services.okx_service.subprocess.run")
    def test_get_open_interest_empty(self, mock_run):
        mock_run.return_value = _mock_run([])
        result = get_open_interest("FAKE")
        self.assertEqual(result, {})


class TestGetMarketOverview(unittest.TestCase):
    """Test ``get_market_overview`` (composite endpoint)."""

    @patch("services.okx_service.get_ticker")
    @patch("services.okx_service.get_funding")
    @patch("services.okx_service.get_open_interest")
    def test_market_overview_success(
        self, mock_oi, mock_funding, mock_ticker
    ):
        mock_ticker.return_value = {
            "price_usd": 58569.0,
            "change_24h": -2.05,
            "high_24h_usd": 60688.0,
            "low_24h_usd": 58200.0,
            "volume_usd": 1272409632.27,
            "bid_price": 58571.0,
            "ask_price": 58571.1,
            "spread": 0.1,
        }
        mock_funding.return_value = {
            "funding_rate": 6.67065786819e-05,
        }
        mock_oi.return_value = {
            "oi_usd": 7485678900.0,
        }

        result = get_market_overview("BTC")
        self.assertEqual(result["symbol"], "BTC")
        self.assertEqual(result["price_usd"], 58569.0)
        self.assertEqual(result["change_24h"], -2.05)
        self.assertEqual(result["funding_rate"], 6.67065786819e-05)
        self.assertEqual(result["open_interest_usd"], 7485678900.0)
        self.assertEqual(result["source"], "okx")

    @patch("services.okx_service.get_ticker")
    @patch("services.okx_service.get_funding")
    @patch("services.okx_service.get_open_interest")
    def test_market_overview_partial_failure(
        self, mock_oi, mock_funding, mock_ticker
    ):
        """If funding or OI fail, the overview should still contain ticker data."""
        mock_ticker.return_value = {
            "price_usd": 58569.0,
            "change_24h": -2.05,
            "high_24h_usd": 60688.0,
            "low_24h_usd": 58200.0,
            "volume_usd": 1272409632.27,
        }
        mock_funding.side_effect = OKXError("funding rate unavailable")
        mock_oi.side_effect = OKXError("OI unavailable")

        result = get_market_overview("BTC")
        self.assertEqual(result["symbol"], "BTC")
        self.assertEqual(result["price_usd"], 58569.0)
        self.assertIsNone(result.get("funding_rate"))
        self.assertIsNone(result.get("open_interest_usd"))

    @patch("services.okx_service.get_ticker")
    def test_market_overview_ticker_failure(self, mock_ticker):
        """If ticker fails, the overview should still have symbol and source."""
        mock_ticker.side_effect = OKXError("ticker error")

        result = get_market_overview("BTC")
        self.assertEqual(result["symbol"], "BTC")
        self.assertEqual(result["source"], "okx")
        self.assertIsNone(result.get("price_usd"))


class TestBuildOkxContext(unittest.TestCase):
    """Test ``build_okx_context``."""

    @patch("services.okx_service.get_market_overview")
    def test_build_okx_context_success(self, mock_overview):
        mock_overview.return_value = {
            "symbol": "BTC",
            "source": "okx",
            "price_usd": 58569.0,
            "change_24h": -2.05,
            "high_24h_usd": 60688.0,
            "low_24h_usd": 58200.0,
            "volume_usd": 1272409632.27,
            "bid_price": 58571.0,
            "ask_price": 58571.1,
            "spread": 0.1,
            "funding_rate": 6.67065786819e-05,
            "open_interest_usd": 7485678900.0,
        }
        result = build_okx_context("BTC")
        self.assertIn("BTC-USDT", result)
        self.assertIn("OKX", result)
        self.assertIn("$58,569.00", result)
        self.assertIn("-2.05%", result)
        self.assertIn("$58,571.00", result)  # bid
        self.assertIn("$58,571.10", result)  # ask
        self.assertIn("$0.10", result)  # spread
        self.assertIn("0.006671%", result)  # funding rate as %
        self.assertIn("$7.5B", result)  # OI

    @patch("services.okx_service.get_market_overview")
    def test_build_okx_context_no_price(self, mock_overview):
        mock_overview.return_value = {
            "symbol": "FAKE",
            "source": "okx",
        }
        result = build_okx_context("FAKE")
        self.assertEqual(result, "")

    @patch("services.okx_service.get_market_overview")
    def test_build_okx_context_empty(self, mock_overview):
        mock_overview.return_value = {}
        result = build_okx_context("FAKE")
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()

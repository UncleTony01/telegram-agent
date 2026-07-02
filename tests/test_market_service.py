import unittest
from unittest.mock import patch, MagicMock

from services.market_service import (
    build_market_context,
    extract_symbols,
    get_price_data,
    get_rich_market_data,
    resolve_coin_id,
    _fmt_price,
    _fmt_change,
    _fmt_big,
)


class MarketServiceTests(unittest.TestCase):
    def test_extract_symbols_legacy_symbols(self):
        self.assertEqual(extract_symbols("BTC analysis"), ["BTC"])
        self.assertEqual(extract_symbols("What is the price of ETH and SOL?"), ["ETH", "SOL"])
        self.assertEqual(extract_symbols("hello there"), [])

    def test_extract_symbols_new_symbols(self):
        self.assertEqual(extract_symbols("HYPE analysis"), ["HYPE"])
        self.assertEqual(extract_symbols("Should I long HYPE?"), ["HYPE"])
        self.assertEqual(extract_symbols("SUI and APT both look good"), ["SUI", "APT"])

    def test_extract_symbols_no_duplicates(self):
        result = extract_symbols("BTC and BTC again and ETH and BTC")
        self.assertEqual(result, ["BTC", "ETH"])

    def test_resolve_coin_id(self):
        self.assertEqual(resolve_coin_id("btc"), "bitcoin")
        self.assertEqual(resolve_coin_id("HYPE"), "hyperliquid")
        self.assertEqual(resolve_coin_id("SUI"), "sui")
        self.assertEqual(resolve_coin_id("PEPE"), "pepe")
        self.assertIsNone(resolve_coin_id("FAKE"))

    @patch("services.market_service._fetch_json")
    def test_get_price_data_returns_expected_fields(self, fetch_json_mock):
        fetch_json_mock.return_value = {
            "bitcoin": {
                "usd": 65000,
                "usd_24h_change": 3.2,
                "usd_market_cap": 1280000000000,
            }
        }

        data = get_price_data("btc")

        self.assertEqual(data["symbol"], "BTC")
        self.assertEqual(data["price_usd"], 65000)
        self.assertEqual(data["change_24h"], 3.2)

    @patch("services.market_service._fetch_json")
    def test_get_price_data_unknown_symbol(self, fetch_json_mock):
        data = get_price_data("FAKE")
        self.assertEqual(data, {})

    @patch("services.market_service._fetch_json")
    def test_get_rich_market_data(self, fetch_json_mock):
        fetch_json_mock.return_value = {
            "name": "Hyperliquid",
            "market_data": {
                "current_price": {"usd": 42.15},
                "price_change_percentage_24h": 3.82,
                "high_24h": {"usd": 43.10},
                "low_24h": {"usd": 40.88},
                "total_volume": {"usd": 686256704},
                "market_cap": {"usd": 14494550369},
                "market_cap_rank": 10,
            },
        }

        data = get_rich_market_data("HYPE")

        self.assertEqual(data["symbol"], "HYPE")
        self.assertEqual(data["name"], "Hyperliquid")
        self.assertEqual(data["price_usd"], 42.15)
        self.assertEqual(data["change_24h"], 3.82)
        self.assertEqual(data["high_24h_usd"], 43.10)
        self.assertEqual(data["low_24h_usd"], 40.88)
        self.assertEqual(data["volume_usd"], 686256704)
        self.assertEqual(data["market_cap_usd"], 14494550369)
        self.assertEqual(data["market_cap_rank"], 10)

    def test_build_market_context_with_dicts(self):
        context = build_market_context([
            {"symbol": "BTC", "name": "Bitcoin", "price_usd": 60145, "change_24h": 1.18,
             "high_24h_usd": 60870, "low_24h_usd": 58990, "volume_usd": 38200000000,
             "market_cap_usd": 1190000000000, "market_cap_rank": 1},
        ])
        self.assertIn("Bitcoin", context)
        self.assertIn("BTC", context)
        self.assertIn("$60,145", context)
        self.assertIn("+1.18%", context)
        self.assertIn("$60,870", context)
        self.assertIn("$58,990", context)
        self.assertIn("$38.2B", context)
        self.assertIn("$1.2T", context)
        self.assertIn("#1", context)

    def test_build_market_context_empty(self):
        self.assertEqual(build_market_context([]), "")
        self.assertEqual(build_market_context([{}]), "")

    def test_fmt_price_below_one(self):
        self.assertEqual(_fmt_price(0.0045), "$0.004500")

    def test_fmt_price_large(self):
        self.assertEqual(_fmt_price(60145), "$60,145.00")

    def test_fmt_change_positive(self):
        self.assertEqual(_fmt_change(1.18), "+1.18%")

    def test_fmt_change_negative(self):
        self.assertEqual(_fmt_change(-2.5), "-2.50%")

    def test_fmt_big_billions(self):
        self.assertEqual(_fmt_big(1190000000000), "$1.2T")

    def test_fmt_big_millions(self):
        self.assertEqual(_fmt_big(38200000), "$38.2M")

    def test_fmt_big_thousands(self):
        self.assertEqual(_fmt_big(382000), "$382.0K")

    @patch("services.market_service._fetch_json")
    def test_get_price_data_hype(self, mock_fetch):
        mock_fetch.return_value = {
            "hyperliquid": {
                "usd": 42.15,
                "usd_24h_change": 3.82,
                "usd_market_cap": 14494550369,
            }
        }
        data = get_price_data("HYPE")
        self.assertEqual(data["symbol"], "HYPE")
        self.assertEqual(data["price_usd"], 42.15)
        self.assertEqual(data["change_24h"], 3.82)


if __name__ == "__main__":
    unittest.main()

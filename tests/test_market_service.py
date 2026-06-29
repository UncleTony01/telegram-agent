import unittest
from unittest.mock import patch

from services.market_service import build_market_context, extract_symbols, get_price_data


class MarketServiceTests(unittest.TestCase):
    def test_extract_symbols_from_message(self):
        self.assertEqual(extract_symbols("BTC analysis"), ["BTC"])
        self.assertEqual(extract_symbols("What is the price of ETH and SOL?"), ["ETH", "SOL"])
        self.assertEqual(extract_symbols("hello there"), [])

    @patch("services.market_service._fetch_json")
    def test_get_price_data_returns_expected_fields(self, fetch_json_mock):
        fetch_json_mock.return_value = {
            "bitcoin": {
                "usd": 65000,
                "usd_24h_change": 3.2,
                "usd_market_cap": 1280000000000,
                "last_updated_at": 1712345678,
            }
        }

        data = get_price_data("btc")

        self.assertEqual(data["symbol"], "BTC")
        self.assertEqual(data["price_usd"], 65000)
        self.assertEqual(data["change_24h"], 3.2)

    def test_build_market_context_formats_multiple_symbols(self):
        context = build_market_context([{"symbol": "BTC", "price_usd": 65000, "change_24h": 3.2}])
        self.assertIn("BTC", context)
        self.assertIn("65000", context)
        self.assertIn("3.2%", context)


if __name__ == "__main__":
    unittest.main()

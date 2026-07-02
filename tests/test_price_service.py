import unittest
from unittest.mock import patch

from services.price_service import handle_price_command


class PriceServiceTests(unittest.TestCase):
    @patch("services.price_service.send_message")
    @patch("services.price_service.get_ticker")
    def test_handle_price_command_no_symbol(self, get_ticker_mock, send_message_mock):
        handle_price_command("123", "/price")
        send_message_mock.assert_called_once()
        get_ticker_mock.assert_not_called()

    @patch("services.price_service.send_message")
    @patch("services.price_service.get_ticker")
    def test_handle_price_command_unknown_symbol(self, get_ticker_mock, send_message_mock):
        get_ticker_mock.return_value = {}
        handle_price_command("123", "/price ABC")
        send_message_mock.assert_called_once_with("123", "No price data available for ABC.")

    @patch("services.price_service.send_message")
    @patch("services.price_service.get_ticker")
    def test_handle_price_command_success(self, get_ticker_mock, send_message_mock):
        get_ticker_mock.return_value = {
            "symbol": "BTC",
            "price_usd": 65000,
            "change_24h": 2.5,
            "bid_price": 64999,
            "ask_price": 65001,
        }
        handle_price_command("123", "/price BTC")
        send_message_mock.assert_called_once()
        message = send_message_mock.call_args[0][1]
        self.assertIn("BTC price", message)
        self.assertIn("24h change", message)


if __name__ == "__main__":
    unittest.main()

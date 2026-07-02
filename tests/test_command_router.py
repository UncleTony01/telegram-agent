import unittest
from unittest.mock import patch

from core.command_router import route_command


class CommandRouterTests(unittest.TestCase):
    @patch("core.command_router.send_help")
    def test_route_help_command(self, send_help_mock):
        route_command("123", "/help")
        send_help_mock.assert_called_once_with("123")

    @patch("core.command_router.handle_price_command")
    def test_route_price_command(self, price_mock):
        route_command("123", "/price BTC")
        price_mock.assert_called_once_with("123", "/price BTC")

    @patch("core.command_router.handle_analysis_command")
    def test_route_analysis_command(self, analysis_mock):
        route_command("123", "/analysis BTC")
        analysis_mock.assert_called_once_with("123", "/analysis BTC")

    @patch("core.command_router.handle_message")
    def test_route_fall_back_to_message_handler(self, message_mock):
        route_command("123", "BTC analysis")
        message_mock.assert_called_once_with("123", "BTC analysis")


if __name__ == "__main__":
    unittest.main()

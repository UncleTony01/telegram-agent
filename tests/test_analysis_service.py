import unittest
from unittest.mock import patch

from services.analysis_service import handle_analysis_command


class AnalysisServiceTests(unittest.TestCase):
    @patch("services.analysis_service.send_message")
    @patch("services.analysis_service.KNOWN_SYMBOLS")
    def test_handle_analysis_no_symbol(self, known_mock, send_message_mock):
        known_mock.__contains__.return_value = False
        handle_analysis_command("123", "/analysis BTC")
        send_message_mock.assert_called_once()

    @patch("services.analysis_service.send_message")
    @patch("services.analysis_service.KNOWN_SYMBOLS")
    def test_handle_analysis_unknown_symbol(self, known_mock, send_message_mock):
        known_mock.__contains__.return_value = False
        handle_analysis_command("123", "/analysis FAKE")
        send_message_mock.assert_called_once_with(
            "123", "Unknown symbol: FAKE. I don't have market data for it."
        )

    @patch("services.analysis_service.ask_hermes")
    @patch("services.analysis_service.send_message")
    @patch("services.analysis_service.build_market_context")
    @patch("services.analysis_service.KNOWN_SYMBOLS")
    def test_handle_analysis_success(
        self, known_mock, context_mock, send_message_mock, ask_hermes_mock
    ):
        known_mock.__contains__.return_value = True
        context_mock.return_value = (
            "Live Market Data\n\n"
            "── HYPE-USDT (OKX) ──\n\n"
            "Price:           $42.15\n"
            "24h Change:      +3.82%\n"
            "24h High:        $43.10\n"
            "24h Low:         $40.88\n"
            "24h Volume:      $686.3M\n"
        )
        ask_hermes_mock.return_value = "Here is the analysis..."

        handle_analysis_command("123", "/analysis HYPE Should I long?")

        # Verify Hermes received a prompt with market data
        call_args = ask_hermes_mock.call_args[0][0]
        self.assertIn("HYPE", call_args)
        self.assertIn("$42.15", call_args)
        self.assertIn("+3.82%", call_args)
        self.assertIn("Should I long?", call_args)

        send_message_mock.assert_called_once_with("123", "Here is the analysis...")

    @patch("services.analysis_service.send_message")
    @patch("services.analysis_service.KNOWN_SYMBOLS")
    def test_handle_analysis_too_few_args(self, known_mock, send_message_mock):
        known_mock.__contains__.return_value = False
        handle_analysis_command("123", "/analysis")
        send_message_mock.assert_called_once()
        self.assertIn("Usage", send_message_mock.call_args[0][1])


if __name__ == "__main__":
    unittest.main()

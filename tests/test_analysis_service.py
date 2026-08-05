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

    @patch("services.analysis_service.generate_analysis_with_optional_ai")
    @patch("services.analysis_service.send_message")
    @patch("services.analysis_service.KNOWN_SYMBOLS")
    def test_handle_analysis_success(
        self, known_mock, send_message_mock, gen_analysis_mock
    ):
        known_mock.__contains__.return_value = True
        gen_analysis_mock.return_value = "Here is the analysis..."

        handle_analysis_command("123", "/analysis HYPE Should I long?")

        gen_analysis_mock.assert_called_once_with("HYPE")
        send_message_mock.assert_any_call("123", "Here is the analysis...")

    @patch("services.analysis_service.send_message")
    @patch("services.analysis_service.KNOWN_SYMBOLS")
    def test_handle_analysis_too_few_args(self, known_mock, send_message_mock):
        known_mock.__contains__.return_value = False
        handle_analysis_command("123", "/analysis")
        send_message_mock.assert_called_once()
        self.assertIn("Usage", send_message_mock.call_args[0][1])


if __name__ == "__main__":
    unittest.main()

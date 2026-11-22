import unittest
from unittest.mock import patch

from handlers.message_handler import handle_message


class MessageHandlerTests(unittest.TestCase):
    @patch("handlers.message_handler.add_message")
    @patch("handlers.message_handler.generate_analysis_with_optional_ai")
    @patch("handlers.message_handler.send_message")
    @patch("handlers.message_handler.extract_symbols")
    def test_injects_market_context_for_crypto_messages(
        self,
        extract_symbols_mock,
        send_message_mock,
        gen_analysis_mock,
        add_message_mock,
    ):
        extract_symbols_mock.return_value = ["BTC"]
        gen_analysis_mock.return_value = "BTC analysis report"

        with patch("services.report_card.build_analysis_card", return_value="<b>BTC card</b>") as card_mock:
            handle_message("123", "Analyze BTC")

        card_mock.assert_called_once_with("BTC", include_position=False)
        send_message_mock.assert_any_call("123", "<b>BTC card</b>", parse_mode="HTML")
        gen_analysis_mock.assert_not_called()

        # If the card can't be built, the text report is still sent.
        send_message_mock.reset_mock()
        with patch("services.report_card.build_analysis_card", side_effect=RuntimeError("boom")):
            handle_message("123", "Analyze BTC")
        gen_analysis_mock.assert_called_once_with("BTC")
        send_message_mock.assert_any_call("123", "BTC analysis report")

    @patch("handlers.message_handler.add_message")
    @patch("handlers.message_handler.ask_hermes")
    @patch("handlers.message_handler.send_message")
    @patch("handlers.message_handler.get_history")
    @patch("handlers.message_handler.extract_symbols")
    def test_leaves_non_crypto_messages_unchanged(
        self,
        extract_symbols_mock,
        get_history_mock,
        send_message_mock,
        ask_hermes_mock,
        add_message_mock,
    ):
        extract_symbols_mock.return_value = []
        get_history_mock.return_value = []
        ask_hermes_mock.return_value = "reply"

        handle_message("123", "Hello Uncle Tony")

        ask_hermes_mock.assert_called_once_with("Hello Uncle Tony", [])
        send_message_mock.assert_any_call("123", "reply")


if __name__ == "__main__":
    unittest.main()

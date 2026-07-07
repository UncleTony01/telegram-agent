import unittest
from unittest.mock import patch

from handlers.message_handler import handle_message


class MessageHandlerTests(unittest.TestCase):
    @patch("handlers.message_handler.add_message")
    @patch("handlers.message_handler.ask_hermes")
    @patch("handlers.message_handler.send_message")
    @patch("handlers.message_handler.get_history")
    @patch("handlers.message_handler.build_market_context")
    @patch("handlers.message_handler.extract_symbols")
    def test_injects_market_context_for_crypto_messages(
        self,
        extract_symbols_mock,
        build_market_context_mock,
        get_history_mock,
        send_message_mock,
        ask_hermes_mock,
        add_message_mock,
    ):
        extract_symbols_mock.return_value = ["BTC"]
        build_market_context_mock.return_value = "Price: $60,000"
        get_history_mock.return_value = []
        ask_hermes_mock.return_value = "reply"

        handle_message("123", "Analyze BTC")

        prompt = ask_hermes_mock.call_args[0][0]
        self.assertIn("User Question", prompt)
        self.assertIn("Analyze BTC", prompt)
        self.assertIn("LIVE MARKET DATA", prompt)
        self.assertIn("Price: $60,000", prompt)
        self.assertIn("Explain your reasoning.", prompt)

    @patch("handlers.message_handler.add_message")
    @patch("handlers.message_handler.ask_hermes")
    @patch("handlers.message_handler.send_message")
    @patch("handlers.message_handler.get_history")
    @patch("handlers.message_handler.build_market_context")
    @patch("handlers.message_handler.extract_symbols")
    def test_leaves_non_crypto_messages_unchanged(
        self,
        extract_symbols_mock,
        build_market_context_mock,
        get_history_mock,
        send_message_mock,
        ask_hermes_mock,
        add_message_mock,
    ):
        extract_symbols_mock.return_value = []
        build_market_context_mock.return_value = ""
        get_history_mock.return_value = []
        ask_hermes_mock.return_value = "reply"

        handle_message("123", "Hello Uncle Tony")

        prompt = ask_hermes_mock.call_args[0][0]
        self.assertEqual(prompt, "Hello Uncle Tony")


if __name__ == "__main__":
    unittest.main()

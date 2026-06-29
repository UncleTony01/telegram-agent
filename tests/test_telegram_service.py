import unittest
from unittest.mock import patch

import requests

from services import telegram_service


class TelegramServiceTests(unittest.TestCase):
    @patch("services.telegram_service.time.sleep")
    @patch("services.telegram_service.session.request")
    def test_send_message_retries_with_backoff_and_resolved_endpoint(self, request_mock, sleep_mock):
        request_mock.side_effect = [
            requests.exceptions.ConnectionError("primary failed"),
            requests.exceptions.ConnectionError("fallback failed"),
            requests.exceptions.ConnectionError("backup failed"),
            requests.exceptions.ConnectionError("backup-2 failed"),
            type("Response", (), {"status_code": 200, "ok": True, "json": lambda self: {}})(),
        ]

        telegram_service.send_message("123", "hello")

        self.assertEqual(request_mock.call_count, 5)
        self.assertEqual(sleep_mock.call_count, 1)
        self.assertIn("https://api.telegram.org/bot", request_mock.call_args_list[0][0][1])

    @patch("services.telegram_service.time.sleep")
    @patch("services.telegram_service.session.request")
    def test_get_updates_returns_json_from_fallback_endpoint(self, request_mock, sleep_mock):
        request_mock.side_effect = [
            requests.exceptions.Timeout("primary timed out"),
            requests.exceptions.Timeout("fallback timed out"),
            requests.exceptions.Timeout("backup timed out"),
            requests.exceptions.Timeout("backup-2 timed out"),
            type("Response", (), {"status_code": 200, "ok": True, "json": lambda self: {"ok": True, "result": []}})(),
        ]

        result = telegram_service.get_updates(offset=5)

        self.assertEqual(result, {"ok": True, "result": []})
        self.assertEqual(request_mock.call_count, 5)
        self.assertEqual(sleep_mock.call_count, 1)


if __name__ == "__main__":
    unittest.main()

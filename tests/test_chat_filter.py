import unittest

from utils.chat_filter import should_process_chat


class ChatFilterTests(unittest.TestCase):
    def test_allows_messages_when_chat_id_is_not_configured(self):
        self.assertTrue(should_process_chat("12345", None, None))

    def test_allows_messages_when_configured_chat_matches_bot_id(self):
        self.assertTrue(should_process_chat("98765", "12345", "12345"))

    def test_restricts_messages_to_configured_chat_id(self):
        self.assertTrue(should_process_chat("12345", "12345", "99999"))
        self.assertFalse(should_process_chat("67890", "12345", "99999"))


if __name__ == "__main__":
    unittest.main()

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.ai import generate_reply
from core.backends import HermesBackendFactory


class HermesBackendTests(unittest.TestCase):
    def test_factory_uses_cli_backend_by_default(self):
        backend = HermesBackendFactory.create()
        self.assertEqual(type(backend).__name__, "HermesCLIBackend")

    @patch("core.backends.subprocess.run")
    def test_generate_reply_uses_backend_and_returns_stdout(self, run_mock):
        run_mock.return_value = SimpleNamespace(stdout="hello from hermes", stderr="", returncode=0)

        with patch("core.backends.HERMES_CMD", "/usr/bin/hermes"), patch("core.backends.HERMES_TIMEOUT", 10):
            backend = HermesBackendFactory.create()
            result = backend.generate("hello")

        self.assertEqual(result, "hello from hermes")
        self.assertEqual(run_mock.call_args[0][0][0], "/usr/bin/hermes")

    @patch("core.ai.HermesBackendFactory.create")
    def test_generate_reply_wrapper_keeps_public_interface(self, factory_mock):
        backend = SimpleNamespace(generate=lambda prompt, history=None: "wrapped")
        factory_mock.return_value = backend
        self.assertEqual(generate_reply("hello", []), "wrapped")


if __name__ == "__main__":
    unittest.main()

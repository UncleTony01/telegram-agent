import subprocess
import time
from abc import ABC, abstractmethod

from config import HERMES_CMD

HERMES_TIMEOUT = 180


class AIBackend(ABC):
    @abstractmethod
    def generate(self, prompt, history=None):
        raise NotImplementedError


class HermesCLIBackend(AIBackend):
    def generate(self, prompt, history=None):
        from core.prompts import build_prompt

        full_prompt = build_prompt(prompt, history)
        start = time.perf_counter()
        result = subprocess.run(
            [
                HERMES_CMD,
                "chat",
                "-q",
                full_prompt,
                "-Q",
                "--ignore-user-config",
                "--ignore-rules",
                "--safe-mode",
                "--source",
                "tool",
            ],
            capture_output=True,
            text=True,
            timeout=HERMES_TIMEOUT,
        )
        elapsed = time.perf_counter() - start
        print(f"Hermes took {elapsed:.2f} seconds")

        output = result.stdout.strip()
        if not output:
            output = result.stderr.strip()
        if not output:
            output = "Hermes returned no output."
        return output


class HermesBackendFactory:
    @staticmethod
    def create():
        return HermesCLIBackend()

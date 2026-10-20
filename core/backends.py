import subprocess
import time
from abc import ABC, abstractmethod
from typing import Optional

import requests

from config import HERMES_CMD, OPENROUTER_API_KEY, OPENROUTER_MODEL

HERMES_TIMEOUT = 180
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_TIMEOUT = 60


class AIBackendError(Exception):
    """Base exception for AI backend failures."""
    pass


class AITimeoutError(AIBackendError):
    """AI backend timed out."""
    pass


class AIConnectionError(AIBackendError):
    """AI backend connection failed."""
    pass


class AIRateLimitError(AIBackendError):
    """AI backend returned HTTP 429 (rate limit)."""
    pass


class AIBackend(ABC):
    @abstractmethod
    def generate(self, prompt, history=None):
        raise NotImplementedError


class HermesCLIBackend(AIBackend):
    def generate(self, prompt, history=None):
        """Generate response using Hermes CLI with robust error handling.
        
        Raises
        ------
        AITimeoutError
            If the command times out
        AIConnectionError
            If the command fails to execute or returns error
        AIBackendError
            For other unexpected failures
        """
        from core.prompts import build_prompt
        from utils.logger import get_logger
        
        logger = get_logger(__name__)

        try:
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
            logger.info(f"Hermes completed in {elapsed:.2f} seconds")

            # Check for rate limit errors in stderr
            stderr = result.stderr.strip().lower()
            if "429" in stderr or "rate limit" in stderr or "too many requests" in stderr:
                logger.warning("Hermes rate limit detected")
                raise AIRateLimitError("Rate limit exceeded")
            
            # Check for connection errors
            if "connection" in stderr or "network" in stderr or "timeout" in stderr:
                logger.warning(f"Hermes connection error: {stderr}")
                raise AIConnectionError(f"Connection failed: {stderr}")
            
            # Check exit code
            if result.returncode != 0:
                logger.warning(f"Hermes exited with code {result.returncode}: {stderr}")
                raise AIBackendError(f"Command failed with exit code {result.returncode}")

            output = result.stdout.strip()
            if not output:
                output = result.stderr.strip()
            if not output:
                logger.warning("Hermes returned no output")
                raise AIBackendError("No output returned")
            
            return output
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"Hermes timeout after {HERMES_TIMEOUT}s")
            raise AITimeoutError(f"Timeout after {HERMES_TIMEOUT}s") from e
        
        except (AITimeoutError, AIConnectionError, AIRateLimitError):
            # Re-raise AI-specific errors
            raise
        
        except FileNotFoundError as e:
            logger.error(f"Hermes command not found: {HERMES_CMD}")
            raise AIConnectionError(f"Command not found: {HERMES_CMD}") from e
        
        except Exception as e:
            logger.error(f"Unexpected Hermes error: {e}")
            raise AIBackendError(f"Unexpected error: {e}") from e


class OpenRouterBackend(AIBackend):
    def generate(self, prompt, history=None):
        """Generate response via the OpenRouter chat completions API.

        Raises the same AI* errors as HermesCLIBackend so callers can fall back.
        """
        from core.prompts import build_prompt
        from utils.logger import get_logger

        logger = get_logger(__name__)
        full_prompt = build_prompt(prompt, history)
        start = time.perf_counter()

        try:
            response = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "X-Title": "Uncle Tony Telegram Bot",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": full_prompt}],
                },
                timeout=OPENROUTER_TIMEOUT,
            )
        except requests.Timeout as e:
            logger.error(f"OpenRouter timeout after {OPENROUTER_TIMEOUT}s")
            raise AITimeoutError(f"Timeout after {OPENROUTER_TIMEOUT}s") from e
        except requests.RequestException as e:
            logger.warning(f"OpenRouter connection error: {e}")
            raise AIConnectionError(f"Connection failed: {e}") from e

        logger.info(f"OpenRouter ({OPENROUTER_MODEL}) completed in {time.perf_counter() - start:.2f} seconds")

        if response.status_code == 429:
            logger.warning("OpenRouter rate limit detected")
            raise AIRateLimitError("Rate limit exceeded")

        if not response.ok:
            logger.warning(f"OpenRouter returned {response.status_code}: {response.text[:200]}")
            raise AIBackendError(f"OpenRouter returned {response.status_code}")

        try:
            output = response.json()["choices"][0]["message"]["content"].strip()
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as e:
            logger.warning(f"Unexpected OpenRouter response: {response.text[:200]}")
            raise AIBackendError("Unexpected response format") from e

        if not output:
            logger.warning("OpenRouter returned no output")
            raise AIBackendError("No output returned")

        return output


class HermesBackendFactory:
    @staticmethod
    def create():
        if OPENROUTER_API_KEY:
            return OpenRouterBackend()
        return HermesCLIBackend()

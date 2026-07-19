import subprocess
import time
from abc import ABC, abstractmethod
from typing import Optional

from config import HERMES_CMD

HERMES_TIMEOUT = 180


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


class HermesBackendFactory:
    @staticmethod
    def create():
        return HermesCLIBackend()

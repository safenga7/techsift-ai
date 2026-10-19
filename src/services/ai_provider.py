"""
TechSift AI - Abstract AI Provider & Google Gemini Free-Tier Implementation.
Equipped with production safeguards: rate limiting, request timeouts, and error handling.
"""

from abc import ABC, abstractmethod
import asyncio
import logging
import time
from typing import Optional
from src.core.config import settings
from src.core.rate_limiter import gemini_rate_limiter

logger = logging.getLogger(__name__)


from src.core.exceptions import (
    AIAuthenticationError,
    AIModelUnavailableError,
    AIProviderException,
    AITimeoutError,
    RateLimitExceededError,
)



def mask_secret(text: str, secret: str) -> str:
    if secret and secret in text:
        return text.replace(secret, "[REDACTED_API_KEY]")
    return text


class AIProvider(ABC):
    """Abstract interface decoupling business logic from concrete LLM vendors."""

    @abstractmethod
    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Generate text given a prompt and optional system instruction."""
        pass


class GeminiProvider(AIProvider):
    """
    Google Gemini Free-Tier AI Provider.
    Adheres strictly to zero-cost rules, rate-limiting, and timeout limits.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self.timeout = settings.GEMINI_TIMEOUT_SECONDS
        self.max_retries = settings.GEMINI_MAX_RETRIES
        self.initial_backoff = settings.GEMINI_INITIAL_BACKOFF_SECONDS
        self.backoff_factor = settings.GEMINI_BACKOFF_FACTOR
        self._client = None

    def _get_client(self):
        if not self._client:
            if not self.api_key:
                raise AIAuthenticationError(
                    "GEMINI_API_KEY is not configured in .env. "
                    "Obtain a free key at https://aistudio.google.com/app/apikey"
                )
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        Generate text asynchronously with rate limiting, timeouts, structured timing logs,
        bounded exponential backoff for transient failures, and fallback models.
        """
        client = self._get_client()

        # Build execution callable
        def _call_api(model: str) -> str:
            config = {}
            if system_instruction:
                config["system_instruction"] = system_instruction

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config if config else None,
            )
            return response.text.strip() if response and response.text else ""

        models_to_try = [self.model_name] + [
            m for m in settings.fallback_models_list if m != self.model_name
        ]

        total_start = time.monotonic()
        max_attempts = max(1, 1 + self.max_retries)
        last_error = None

        for model_idx, target_model in enumerate(models_to_try):
            for attempt in range(1, max_attempts + 1):
                # Safeguard 1: In-memory token bucket rate limiting (preserves 15 RPM free tier)
                wait_time = await gemini_rate_limiter.acquire()
                if wait_time > 0.05:
                    logger.info(
                        f"[Timing] RateLimiter throttled request for {wait_time:.2f}s "
                        f"(model='{target_model}', attempt={attempt}/{max_attempts})."
                    )

                logger.info(
                    f"[Timing] [Model {model_idx + 1}/{len(models_to_try)}] Calling Gemini model '{target_model}' "
                    f"(attempt {attempt}/{max_attempts}, prompt_chars={len(prompt)}, timeout={self.timeout:.1f}s)..."
                )
                attempt_start = time.monotonic()

                try:
                    # Run synchronous SDK call in background thread pool to prevent blocking event loop
                    text = await asyncio.wait_for(
                        asyncio.to_thread(_call_api, target_model),
                        timeout=self.timeout,
                    )
                    elapsed = time.monotonic() - attempt_start
                    logger.info(
                        f"[Timing] Gemini model '{target_model}' completed successfully in {elapsed:.2f}s "
                        f"(output_chars={len(text)}, total_pipeline_elapsed={time.monotonic() - total_start:.2f}s)."
                    )
                    return text

                except asyncio.TimeoutError as timeout_exc:
                    elapsed = time.monotonic() - attempt_start
                    logger.warning(
                        f"[Timing] Gemini model '{target_model}' timed out after {elapsed:.2f}s "
                        f"(configured timeout={self.timeout:.1f}s, attempt {attempt}/{max_attempts})."
                    )
                    last_error = timeout_exc

                    if attempt < max_attempts:
                        backoff = self.initial_backoff * (self.backoff_factor ** (attempt - 1))
                        logger.info(
                            f"[Timing] Applying bounded exponential backoff: waiting {backoff:.1f}s before retry on '{target_model}'..."
                        )
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        logger.warning(
                            f"Timeout retries exhausted on model '{target_model}' ({max_attempts} attempts)."
                        )
                        break  # Proceed to next fallback model if available

                except Exception as exc:
                    elapsed = time.monotonic() - attempt_start
                    raw_err = mask_secret(str(exc), self.api_key)
                    last_error = exc

                    # 1. Rate Limit: 429 RESOURCE_EXHAUSTED -> DO NOT RETRY (protect free-tier quota)
                    if "429" in raw_err or "RESOURCE_EXHAUSTED" in raw_err:
                        logger.warning(
                            f"[Timing] Gemini rate limit 429 encountered after {elapsed:.2f}s on '{target_model}'. "
                            "Failing immediately without retry to avoid quota drain."
                        )
                        raise RateLimitExceededError(
                            "Google Gemini free-tier rate limit reached (RPM/RPD exhausted). "
                            "Please wait a moment before sending another request."
                        ) from exc

                    # 2. Authentication: 401 / 403 PERMISSION_DENIED -> DO NOT RETRY
                    elif "403" in raw_err or "PERMISSION_DENIED" in raw_err or "401" in raw_err:
                        logger.error(
                            f"Gemini authentication failure on '{target_model}'. Failing immediately without retry."
                        )
                        raise AIAuthenticationError(
                            "Google Gemini API authentication failed. Verify your key in .env."
                        ) from exc

                    # 3. Model not found: 404 NOT_FOUND -> Move to next candidate model
                    elif "404" in raw_err or "NOT_FOUND" in raw_err:
                        logger.warning(
                            f"Model '{target_model}' returned 404 NOT_FOUND after {elapsed:.2f}s. "
                            "Switching to fallback model..."
                        )
                        break  # Next model

                    # 4. Transient Server Errors: 503 UNAVAILABLE / 502 / 504 / network reset -> Retry with backoff
                    elif any(k in raw_err for k in ("503", "UNAVAILABLE", "502", "504", "ConnectionResetError", "RemoteDisconnected")):
                        logger.warning(
                            f"Model '{target_model}' returned transient error after {elapsed:.2f}s: {raw_err} "
                            f"(attempt {attempt}/{max_attempts})."
                        )
                        if attempt < max_attempts:
                            backoff = self.initial_backoff * (self.backoff_factor ** (attempt - 1))
                            logger.info(f"[Timing] Retrying transient error in {backoff:.1f}s with backoff...")
                            await asyncio.sleep(backoff)
                            continue
                        else:
                            logger.warning(f"Transient retries exhausted on model '{target_model}'.")
                            break  # Next model

                    # 5. Non-retriable provider error (e.g. 400 Bad Request)
                    else:
                        logger.error(f"Non-retriable Gemini generation error on '{target_model}': {raw_err}")
                        raise AIProviderException(f"Gemini generation error: {raw_err}") from exc

        # All candidate models and retries exhausted
        if isinstance(last_error, asyncio.TimeoutError):
            raise AITimeoutError(
                f"Gemini API request timed out after {self.timeout}s on model '{self.model_name}' "
                f"(retries exhausted across {len(models_to_try)} candidate models)."
            ) from last_error

        raise AIModelUnavailableError(
            f"All candidate models exhausted. Last error: {mask_secret(str(last_error), self.api_key)}"
        )

"""
Unit tests for AIProvider architecture, safeguards, and rate limiting.
Runs 100% offline without consuming API quota or making network calls.
"""

import asyncio
import time
import pytest
from src.core.rate_limiter import FreeTierRateLimiter
from src.services.ai_provider import (
    AIProvider,
    GeminiProvider,
    mask_secret,
    AIAuthenticationError,
    AITimeoutError,
)


def test_mask_secret():
    secret = "AIzaSySecretKey12345"
    text = f"Error in request with key {secret}: unauthorized."
    masked = mask_secret(text, secret)
    assert secret not in masked
    assert "[REDACTED_API_KEY]" in masked


@pytest.mark.asyncio
async def test_rate_limiter_throttling():
    limiter = FreeTierRateLimiter(max_rpm=60)  # 1 request per second
    
    # First request should have minimal wait
    wait1 = await limiter.acquire()
    assert wait1 == 0.0

    # Second immediate request must be throttled
    start = asyncio.get_event_loop().time()
    wait2 = await limiter.acquire()
    elapsed = asyncio.get_event_loop().time() - start
    
    assert wait2 > 0.0
    assert elapsed >= 0.8  # Throttled ~1.0s


def test_missing_api_key_raises_auth_error(monkeypatch):
    monkeypatch.setattr("src.services.ai_provider.settings.GEMINI_API_KEY", "")
    provider = GeminiProvider()
    with pytest.raises(AIAuthenticationError):
        provider._get_client()


class MockAIProvider(AIProvider):
    async def generate_text(self, prompt: str, system_instruction=None) -> str:
        return f"Mocked summary for: {prompt[:20]}"


@pytest.mark.asyncio
async def test_mock_ai_provider_conformance():
    provider = MockAIProvider()
    res = await provider.generate_text("Distributed consensus overview")
    assert "Mocked summary" in res


@pytest.mark.asyncio
async def test_gemini_provider_timeout_raises_ai_timeout_error(monkeypatch):
    """Verifies that exceeding the configured timeout raises AITimeoutError after retries."""
    from unittest.mock import AsyncMock, MagicMock
    from src.core.config import Settings
    from src.core.exceptions import AITimeoutError

    provider = GeminiProvider()
    provider.api_key = "test_key"
    provider.timeout = 0.05
    provider.max_retries = 1
    provider.initial_backoff = 0.005

    # Bypass rate limiter wait in unit tests
    monkeypatch.setattr("src.services.ai_provider.gemini_rate_limiter.acquire", AsyncMock(return_value=0.0))

    mock_client = MagicMock()

    def slow_generate(*args, **kwargs):
        time.sleep(0.1)
        mock_resp = MagicMock()
        mock_resp.text = "Should not reach here"
        return mock_resp

    mock_client.models.generate_content.side_effect = slow_generate
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)
    monkeypatch.setattr(Settings, "fallback_models_list", property(lambda self: [provider.model_name]))

    with pytest.raises(AITimeoutError) as exc_info:
        await provider.generate_text("Test prompt")

    assert "timed out after 0.05s" in str(exc_info.value)
    # Verifies retry occurred (initial attempt + 1 retry = 2 attempts)
    assert mock_client.models.generate_content.call_count == 2


@pytest.mark.asyncio
async def test_gemini_provider_transient_failure_succeeds_on_retry(monkeypatch):
    """Verifies that a transient 503 error is recovered by bounded exponential backoff retry."""
    from unittest.mock import AsyncMock, MagicMock

    provider = GeminiProvider()
    provider.api_key = "test_key"
    provider.timeout = 2.0
    provider.max_retries = 2
    provider.initial_backoff = 0.005

    monkeypatch.setattr("src.services.ai_provider.gemini_rate_limiter.acquire", AsyncMock(return_value=0.0))

    mock_client = MagicMock()
    mock_success = MagicMock()
    mock_success.text = '{"executive_summary": "Recovered from transient error"}'

    # First call: 503 UNAVAILABLE, Second call: Success
    mock_client.models.generate_content.side_effect = [
        RuntimeError("503 UNAVAILABLE: The service is temporarily overloaded."),
        mock_success,
    ]
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    result = await provider.generate_text("Test prompt")
    assert "Recovered from transient error" in result
    assert mock_client.models.generate_content.call_count == 2


@pytest.mark.asyncio
async def test_gemini_provider_rate_limit_fails_fast_without_retrying(monkeypatch):
    """Verifies that 429 RESOURCE_EXHAUSTED fails immediately without retrying to protect quota."""
    from unittest.mock import AsyncMock, MagicMock
    from src.core.exceptions import RateLimitExceededError

    provider = GeminiProvider()
    provider.api_key = "test_key"
    provider.timeout = 2.0
    provider.max_retries = 2
    provider.initial_backoff = 0.005

    monkeypatch.setattr("src.services.ai_provider.gemini_rate_limiter.acquire", AsyncMock(return_value=0.0))

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError(
        "429 RESOURCE_EXHAUSTED: Free tier quota reached for model."
    )
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    with pytest.raises(RateLimitExceededError):
        await provider.generate_text("Test prompt")

    # MUST fail fast on attempt 1 without retry
    assert mock_client.models.generate_content.call_count == 1


@pytest.mark.asyncio
async def test_gemini_provider_auth_error_fails_fast_without_retrying(monkeypatch):
    """Verifies that 403 PERMISSION_DENIED fails immediately without retrying."""
    from unittest.mock import AsyncMock, MagicMock
    from src.core.exceptions import AIAuthenticationError

    provider = GeminiProvider()
    provider.api_key = "test_key"
    provider.timeout = 2.0
    provider.max_retries = 2
    provider.initial_backoff = 0.005

    monkeypatch.setattr("src.services.ai_provider.gemini_rate_limiter.acquire", AsyncMock(return_value=0.0))

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError(
        "403 PERMISSION_DENIED: The caller does not have permission."
    )
    monkeypatch.setattr(provider, "_get_client", lambda: mock_client)

    with pytest.raises(AIAuthenticationError):
        await provider.generate_text("Test prompt")

    # MUST fail fast on attempt 1 without retry
    assert mock_client.models.generate_content.call_count == 1


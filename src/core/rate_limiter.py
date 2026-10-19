"""
TechSift AI - In-Memory Token Bucket Rate Limiter for Free-Tier AI Safeguards.
Protects against 429 RESOURCE_EXHAUSTED errors on Google AI Studio Free Tier.
"""

import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class FreeTierRateLimiter:
    """
    Token-bucket rate limiter designed for Google Gemini Free Tier.
    Enforces a strict Requests-Per-Minute (RPM) cap and minimum inter-request interval.
    Zero external dependencies (no Redis or external cache needed).
    """

    def __init__(self, max_rpm: int = 10):
        self.max_rpm = max_rpm
        self.interval_seconds = 60.0 / max_rpm
        self._lock = asyncio.Lock()
        self._last_request_time: float = 0.0

    async def acquire(self) -> float:
        """
        Wait until capacity is available to send a request within quota.
        Returns the duration waited in seconds.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            wait_time = 0.0

            if elapsed < self.interval_seconds:
                wait_time = self.interval_seconds - elapsed
                logger.info(f"RateLimiter: Throttling request for {wait_time:.2f}s to preserve free-tier quota.")
                await asyncio.sleep(wait_time)

            self._last_request_time = time.monotonic()
            return wait_time


# Global instance configured for Free Tier
gemini_rate_limiter = FreeTierRateLimiter(max_rpm=10)

import time
import asyncio
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from fastapi import HTTPException, status
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class TokenBucketRateLimiter:
    """
    Per-user in-memory sliding window rate limiter for AI inference endpoints.
    Enforces per-minute limit (default 20) and per-hour limit (default 200).
    Returns HTTP 429 with 'Retry-After' header upon exhaustion.
    """
    def __init__(self, per_minute: int = 20, per_hour: int = 200):
        self.per_minute = per_minute
        self.per_hour = per_hour
        self._user_requests: Dict[int, List[float]] = {}
        self._lock = asyncio.Lock()

    async def check_rate_limit(self, user_id: int):
        now = time.time()
        async with self._lock:
            history = self._user_requests.setdefault(user_id, [])
            # Prune timestamps older than 3600 seconds
            history = [t for t in history if now - t < 3600]
            self._user_requests[user_id] = history

            # Check 1-minute window (last 60s)
            recent_minute = [t for t in history if now - t < 60]
            if len(recent_minute) >= self.per_minute:
                oldest_in_window = recent_minute[0]
                retry_after = max(1, int(60 - (now - oldest_in_window)) + 1)
                logger.warning(
                    f"User {user_id} exceeded AI rate limit (per minute: {len(recent_minute)}/{self.per_minute}). "
                    f"Retry-After: {retry_after}s"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Too many AI requests in one minute (limit: {self.per_minute}).",
                    headers={"Retry-After": str(retry_after)}
                )

            # Check 1-hour window (last 3600s)
            if len(history) >= self.per_hour:
                oldest_in_hour = history[0]
                retry_after = max(1, int(3600 - (now - oldest_in_hour)) + 1)
                logger.warning(
                    f"User {user_id} exceeded AI rate limit (per hour: {len(history)}/{self.per_hour}). "
                    f"Retry-After: {retry_after}s"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Too many AI requests in one hour (limit: {self.per_hour}).",
                    headers={"Retry-After": str(retry_after)}
                )

            history.append(now)

    def reset(self):
        """Reset limits for test isolation."""
        self._user_requests.clear()


class InvestigationConcurrencyLimiter:
    """
    Ensures maximum 1 in-flight AI request per active investigation.
    Raises HTTP 409 'AI is already working on this investigation' if concurrent request arrives.
    """
    def __init__(self):
        self._in_flight: set = set()
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self, investigation_id: Optional[int]):
        if investigation_id is None:
            yield
            return

        async with self._lock:
            if investigation_id in self._in_flight:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="AI is already working on this investigation"
                )
            self._in_flight.add(investigation_id)

        try:
            yield
        finally:
            async with self._lock:
                self._in_flight.discard(investigation_id)

    def reset(self):
        """Reset locks for test isolation."""
        self._in_flight.clear()


ai_rate_limiter = TokenBucketRateLimiter(
    per_minute=getattr(settings, "AI_RATE_LIMIT_PER_MINUTE", 20),
    per_hour=getattr(settings, "AI_RATE_LIMIT_PER_HOUR", 200)
)
investigation_concurrency_limiter = InvestigationConcurrencyLimiter()


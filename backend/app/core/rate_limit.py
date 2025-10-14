"""
Rate Limiting Middleware for API Keys
Implements per-key rate limiting with Redis-backed sliding window
"""

from fastapi import HTTPException, status, Request
from typing import Optional
import time
from datetime import datetime, timedelta
import redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Rate limiter using Redis sliding window algorithm
    Tracks API key usage and enforces per-key rate limits
    """

    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )

    def _get_key(self, api_key_id: str, window: str = "minute") -> str:
        """Generate Redis key for rate limit tracking"""
        timestamp = int(time.time())

        if window == "minute":
            bucket = timestamp // 60  # 1-minute buckets
        elif window == "hour":
            bucket = timestamp // 3600  # 1-hour buckets
        else:
            bucket = timestamp // 60

        return f"rate_limit:{api_key_id}:{window}:{bucket}"

    async def check_rate_limit(
        self,
        api_key_id: str,
        rate_limit: int,
        window: str = "minute",
    ) -> bool:
        """
        Check if request is within rate limit

        Args:
            api_key_id: The API key ID
            rate_limit: Maximum requests allowed in the window
            window: Time window ("minute" or "hour")

        Returns:
            True if within limit, raises HTTPException if exceeded
        """
        try:
            key = self._get_key(api_key_id, window)

            # Increment counter
            current = self.redis_client.incr(key)

            # Set expiration on first request
            if current == 1:
                if window == "minute":
                    self.redis_client.expire(key, 120)  # 2 minutes to account for clock skew
                elif window == "hour":
                    self.redis_client.expire(key, 7200)  # 2 hours
                else:
                    self.redis_client.expire(key, 120)

            # Check if limit exceeded
            if current > rate_limit:
                logger.warning(
                    f"Rate limit exceeded",
                    api_key_id=api_key_id,
                    current=current,
                    limit=rate_limit,
                    window=window,
                )

                # Calculate retry-after time
                retry_after = 60 if window == "minute" else 3600

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {rate_limit} requests per {window}.",
                    headers={"Retry-After": str(retry_after)},
                )

            return True

        except redis.RedisError as e:
            logger.error(f"Redis error in rate limiting", error=str(e))
            # Fail open - allow request if Redis is down
            return True

    async def get_remaining_requests(
        self,
        api_key_id: str,
        rate_limit: int,
        window: str = "minute",
    ) -> int:
        """Get remaining requests in current window"""
        try:
            key = self._get_key(api_key_id, window)
            current = int(self.redis_client.get(key) or 0)
            return max(0, rate_limit - current)
        except redis.RedisError:
            return rate_limit  # Return full limit if Redis is down


# Global rate limiter instance
rate_limiter = RateLimiter()


async def apply_api_key_rate_limit(
    request: Request,
    api_key_id: str,
    rate_limit: int,
):
    """
    Apply rate limiting to an API key request

    Args:
        request: FastAPI request object
        api_key_id: The API key ID
        rate_limit: Maximum requests per minute

    Raises:
        HTTPException: If rate limit is exceeded
    """
    # Check per-minute rate limit
    await rate_limiter.check_rate_limit(api_key_id, rate_limit, window="minute")

    # Get remaining requests for headers
    remaining = await rate_limiter.get_remaining_requests(
        api_key_id, rate_limit, window="minute"
    )

    # Add rate limit headers to response
    request.state.rate_limit_limit = rate_limit
    request.state.rate_limit_remaining = remaining
    request.state.rate_limit_reset = int(time.time()) + 60

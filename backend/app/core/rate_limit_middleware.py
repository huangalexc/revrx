"""
Rate Limit Response Middleware
Adds rate limit headers to API responses
"""

from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response


class RateLimitHeaderMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add rate limit headers to responses

    Headers added:
    - X-RateLimit-Limit: The rate limit ceiling for that given endpoint
    - X-RateLimit-Remaining: The number of requests remaining in the current window
    - X-RateLimit-Reset: The time at which the rate limit window resets (Unix timestamp)
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add rate limit headers if they were set by the rate limiter
        if hasattr(request.state, "rate_limit_limit"):
            response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit_limit)
            response.headers["X-RateLimit-Remaining"] = str(
                request.state.rate_limit_remaining
            )
            response.headers["X-RateLimit-Reset"] = str(request.state.rate_limit_reset)

        return response

"""
RevRx SDK Exceptions
"""


class RevRxError(Exception):
    """Base exception for all RevRx SDK errors"""

    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class AuthenticationError(RevRxError):
    """Raised when API authentication fails"""

    pass


class RateLimitError(RevRxError):
    """Raised when rate limit is exceeded"""

    def __init__(
        self,
        message: str,
        retry_after: int = None,
        limit: int = None,
        remaining: int = None,
        reset: int = None,
    ):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining
        self.reset = reset


class ValidationError(RevRxError):
    """Raised when request validation fails"""

    pass


class NotFoundError(RevRxError):
    """Raised when resource is not found"""

    pass


class ServerError(RevRxError):
    """Raised when server returns 5xx error"""

    pass

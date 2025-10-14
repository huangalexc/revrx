"""
Dependency injection for FastAPI endpoints
Provides reusable dependencies for authentication and authorization
"""

from typing import Optional, Union
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from prisma.models import User, ApiKey

from app.core.database import prisma, get_db
from app.core.security import jwt_manager
from app.services.api_key_service import ApiKeyService
from app.core.rate_limit import apply_api_key_rate_limit


# HTTP Bearer token authentication scheme
security = HTTPBearer()

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer token from request header

    Returns:
        User model instance

    Raises:
        HTTPException: If token is invalid or user not found
    """
    import structlog
    logger = structlog.get_logger(__name__)

    token = credentials.credentials
    logger.info("Authenticating user", token_preview=token[:20] if token else None)

    # Decode and validate token
    payload = jwt_manager.decode_token(token)
    logger.info("Token decoded", user_id=payload.get("sub"), email=payload.get("email"))

    # Verify it's an access token
    if not jwt_manager.verify_token_type(payload, "access"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user ID from token
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user from database
    user = await prisma.user.find_unique(where={"id": user_id})

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if email is verified
    if not user.emailVerified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email before accessing this resource.",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get current user and verify they have an active subscription

    Args:
        current_user: Current authenticated user

    Returns:
        User model instance

    Raises:
        HTTPException: If subscription is not active
    """
    # Check if user has active subscription or trial
    if current_user.subscriptionStatus not in ["ACTIVE", "TRIAL"]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required. Your subscription has expired or is inactive.",
        )

    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to verify current user has admin role

    Args:
        current_user: Current authenticated user

    Returns:
        User model instance

    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. You do not have permission to access this resource.",
        )

    return current_user


async def verify_resource_ownership(
    resource_user_id: str,
    current_user: User = Depends(get_current_user)
) -> bool:
    """
    Verify that the current user owns the resource or is an admin

    Args:
        resource_user_id: User ID that owns the resource
        current_user: Current authenticated user

    Returns:
        True if user owns resource or is admin

    Raises:
        HTTPException: If user doesn't own resource and is not admin
    """
    if current_user.role == "ADMIN":
        return True

    if current_user.id != resource_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You do not have permission to access this resource.",
        )

    return True


class OptionalAuth:
    """Optional authentication - doesn't raise exception if no token provided"""

    async def __call__(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(
            HTTPBearer(auto_error=False)
        )
    ) -> Optional[User]:
        """
        Get current user if token is provided, otherwise return None

        Args:
            credentials: Optional HTTP Bearer token

        Returns:
            User model instance or None
        """
        if credentials is None:
            return None

        try:
            token = credentials.credentials
            payload = jwt_manager.decode_token(token)

            if not jwt_manager.verify_token_type(payload, "access"):
                return None

            user_id: Optional[str] = payload.get("sub")
            if user_id is None:
                return None

            user = await prisma.user.find_unique(where={"id": user_id})
            return user

        except Exception:
            return None


# Export optional auth instance
optional_auth = OptionalAuth()


def require_role(*allowed_roles: str):
    """
    Decorator to require specific role(s) for endpoint access

    Usage:
        @router.get("/admin/users")
        @require_role("ADMIN")
        async def list_users(current_user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func):
        from functools import wraps

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs
            current_user = kwargs.get("current_user")

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            if current_user.role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required role: {', '.join(allowed_roles)}",
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


async def get_api_key_user(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
) -> User:
    """
    Dependency to authenticate via API key with rate limiting

    Args:
        request: FastAPI request object
        api_key: API key from X-API-Key header

    Returns:
        User model instance

    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "X-API-Key"},
        )

    # Validate API key
    api_key_record = await ApiKeyService.validate_api_key(api_key, prisma)

    if not api_key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "X-API-Key"},
        )

    # Apply rate limiting
    await apply_api_key_rate_limit(
        request=request,
        api_key_id=api_key_record.id,
        rate_limit=api_key_record.rateLimit,
    )

    return api_key_record.user


async def get_current_user_or_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    api_key: Optional[str] = Depends(api_key_header),
) -> User:
    """
    Dependency that accepts either JWT token or API key for authentication

    Tries JWT first, then API key. Applies rate limiting for API key auth.

    Args:
        request: FastAPI request object
        credentials: Optional HTTP Bearer token
        api_key: Optional API key from X-API-Key header

    Returns:
        User model instance

    Raises:
        HTTPException: If both authentication methods fail
    """
    # Try JWT authentication first
    if credentials:
        try:
            token = credentials.credentials
            payload = jwt_manager.decode_token(token)

            if jwt_manager.verify_token_type(payload, "access"):
                user_id: Optional[str] = payload.get("sub")
                if user_id:
                    user = await prisma.user.find_unique(where={"id": user_id})
                    if user:
                        return user
        except Exception:
            pass  # Try API key next

    # Try API key authentication
    if api_key:
        api_key_record = await ApiKeyService.validate_api_key(api_key, prisma)
        if api_key_record:
            # Apply rate limiting for API key
            await apply_api_key_rate_limit(
                request=request,
                api_key_id=api_key_record.id,
                rate_limit=api_key_record.rateLimit,
            )
            return api_key_record.user

    # Both methods failed
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide either Bearer token or X-API-Key header",
        headers={"WWW-Authenticate": "Bearer, X-API-Key"},
    )

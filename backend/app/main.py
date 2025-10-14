"""
FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import structlog

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.database import prisma
from app.api.v1.router import api_router
from app.core.rate_limit_middleware import RateLimitHeaderMiddleware

# Configure structured logging
configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting application", version=app.version)

    # Connect to database
    await prisma.connect()
    logger.info("Database connected")

    yield

    # Disconnect from database
    await prisma.disconnect()
    logger.info("Database disconnected")


# Create FastAPI application
app = FastAPI(
    title="Post-Facto Coding Review API",
    description="""
# Post-Facto Coding Review API

HIPAA-compliant healthcare coding review system powered by AI.

## Features

- **Encounter Analysis**: Submit clinical notes and billing codes for AI-powered review
- **Code Suggestions**: Receive additional CPT/ICD code recommendations with justifications
- **Revenue Analysis**: Calculate potential incremental revenue from suggested codes
- **Webhook Notifications**: Real-time event notifications for encounter status changes
- **API Key Management**: Programmatic access with rate-limited API keys

## Authentication

This API supports two authentication methods:

1. **JWT Bearer Token**: For user-based authentication
   - Header: `Authorization: Bearer <token>`
   - Obtain tokens via `/api/v1/auth/login` endpoint

2. **API Key**: For programmatic access
   - Header: `X-API-Key: <api_key>`
   - Manage keys via `/api/v1/api-keys` endpoints
   - Rate limited per key (default 100 requests/minute)

## Rate Limiting

API key requests are rate limited. Response headers include:
- `X-RateLimit-Limit`: Maximum requests per minute
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when the window resets

## Webhooks

Configure webhooks to receive real-time notifications for:
- `encounter.submitted`: New encounter submitted
- `encounter.processing`: Processing started
- `encounter.completed`: Analysis complete
- `encounter.failed`: Processing failed

Webhook payloads are signed with HMAC-SHA256 for verification.
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.APP_DEBUG else None,
    redoc_url="/api/redoc" if settings.APP_DEBUG else None,
    openapi_tags=[
        {"name": "Authentication", "description": "User registration, login, and token management"},
        {"name": "Users", "description": "User profile management"},
        {"name": "Encounters", "description": "Clinical encounter submission and retrieval"},
        {"name": "Reports", "description": "Coding review reports and analysis"},
        {"name": "WebSocket", "description": "Real-time report status updates via WebSocket"},
        {"name": "Subscriptions", "description": "Subscription and billing management"},
        {"name": "API Keys", "description": "API key creation and management"},
        {"name": "Integrations", "description": "Programmatic encounter submission"},
        {"name": "Webhooks", "description": "Webhook configuration and delivery logs"},
        {"name": "Admin", "description": "Administrative operations"},
    ],
    contact={
        "name": "API Support",
        "email": "support@example.com",
    },
    license_info={
        "name": "Proprietary",
    },
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

# Security Headers
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.APP_DEBUG else settings.ALLOWED_HOSTS
)

# Rate Limit Headers
app.add_middleware(RateLimitHeaderMiddleware)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": app.version,
        "environment": settings.APP_ENV
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Post-Facto Coding Review API",
        "version": app.version,
        "docs": "/api/docs" if settings.APP_DEBUG else None
    }

"""
Application Configuration
Loads and validates environment variables
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Application
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    SECRET_KEY: str
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]

    # Database
    DATABASE_URL: str

    # JWT Configuration
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_S3_BUCKET_NAME: str
    AWS_S3_ENCRYPTION: str = "AES256"
    AWS_COMPREHEND_MEDICAL_REGION: str = "us-east-1"

    # OpenAI Configuration
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_MAX_TOKENS: int = 2000
    OPENAI_TEMPERATURE: float = 0.3

    # Stripe Configuration
    STRIPE_SECRET_KEY: str
    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    STRIPE_PRICE_ID_MONTHLY: str

    # Email Configuration
    RESEND_API_KEY: str
    FROM_EMAIL: str
    FRONTEND_URL: str = "http://localhost:3000"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None

    # Async Processing Feature Flags
    ENABLE_ASYNC_REPORTS: bool = True  # Master toggle for async report processing
    ASYNC_ROLLOUT_PERCENTAGE: int = 100  # Percentage of reports to process async (0-100)

    # Celery Configuration
    ENABLE_CELERY: bool = False  # Toggle between asyncio (False) and Celery (True)
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None
    CELERY_WORKER_CONCURRENCY: int = 4
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 2
    CELERY_TASK_TIME_LIMIT: int = 300  # 5 minutes
    CELERY_TASK_SOFT_TIME_LIMIT: int = 240  # 4 minutes
    CELERY_RESULT_EXPIRES: int = 3600  # 1 hour

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # File Upload Limits
    MAX_FILE_SIZE_MB: int = 5
    MAX_FILES_PER_ENCOUNTER: int = 2

    # HIPAA Compliance
    PHI_ENCRYPTION_KEY: str  # Must be 32 bytes for AES-256
    DATA_RETENTION_DAYS: int = 2555  # 7 years

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60

    # Monitoring
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()

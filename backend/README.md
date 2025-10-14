# Post-Facto Coding Review MVP - Backend

HIPAA-compliant healthcare coding review system backend built with FastAPI.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- AWS Account (for Comprehend Medical and S3)
- OpenAI API Key
- Stripe Account

### Installation

1. **Clone and navigate to backend**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Generate Prisma client**
   ```bash
   prisma generate
   ```

6. **Run database migrations**
   ```bash
   prisma migrate dev
   ```

7. **Start the development server**
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/api/docs`

## 🐳 Docker Setup

### Development with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

Services:
- Backend API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

### Production Docker Build

```bash
docker build -t revrx-backend .
docker run -p 8000:8000 --env-file .env revrx-backend
```

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/              # API endpoints
│   │   └── v1/
│   │       ├── endpoints/  # Route handlers
│   │       └── router.py
│   ├── core/             # Core functionality
│   │   ├── config.py       # Configuration
│   │   ├── database.py     # Database connection
│   │   ├── logging.py      # Structured logging
│   │   └── storage.py      # S3 storage service
│   ├── models/           # Prisma models (generated)
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   │   ├── auth/          # Authentication
│   │   ├── phi/           # PHI detection/de-identification
│   │   ├── processing/    # File processing
│   │   ├── ai/            # AI/NLP integration
│   │   └── payment/       # Stripe integration
│   ├── tasks/            # Celery background tasks
│   ├── utils/            # Utility functions
│   └── main.py           # FastAPI application
├── prisma/
│   └── schema.prisma     # Database schema
├── tests/                # Test suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## 🔧 Configuration

Key environment variables (see `.env.example`):

### Database
- `DATABASE_URL`: PostgreSQL connection string

### AWS Services
- `AWS_REGION`: AWS region
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_S3_BUCKET_NAME`: S3 bucket for file storage

### OpenAI
- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_MODEL`: Model to use (default: gpt-4)

### Stripe
- `STRIPE_SECRET_KEY`: Stripe secret key
- `STRIPE_WEBHOOK_SECRET`: Stripe webhook secret

### Security
- `SECRET_KEY`: Application secret key
- `JWT_SECRET_KEY`: JWT signing key
- `PHI_ENCRYPTION_KEY`: 32-byte key for PHI encryption

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py
```

## 📊 Database Migrations

```bash
# Create a new migration
prisma migrate dev --name migration_name

# Apply migrations
prisma migrate deploy

# Reset database (dev only)
prisma migrate reset
```

## 🔒 Security Features

- **HIPAA Compliance**: PHI detection and de-identification using AWS Comprehend Medical
- **Encryption at Rest**: AES-256 encryption for S3 storage and PHI data
- **Encryption in Transit**: TLS 1.3 for all API communication
- **Audit Logging**: Comprehensive audit trail for all operations
- **JWT Authentication**: Secure token-based authentication
- **Rate Limiting**: Protection against abuse
- **Input Validation**: Pydantic schemas for request validation

## 📝 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/verify` - Email verification
- `POST /api/v1/auth/forgot-password` - Password reset request

### Encounters
- `POST /api/v1/encounters/upload-note` - Upload clinical note
- `POST /api/v1/encounters/{id}/upload-codes` - Upload billing codes
- `GET /api/v1/encounters` - List encounters
- `GET /api/v1/encounters/{id}` - Get encounter details

### Reports
- `GET /api/v1/reports/{encounter_id}` - Get coding review report
- `GET /api/v1/reports/summary` - Get revenue summary
- `GET /api/v1/reports/{id}/export` - Export report (YAML/JSON/PDF)

### Subscriptions
- `POST /api/v1/subscriptions/start-trial` - Start free trial
- `GET /api/v1/subscriptions/me` - Get subscription status
- `POST /api/v1/subscriptions/cancel` - Cancel subscription

### Admin
- `GET /api/v1/admin/users` - List users
- `GET /api/v1/admin/audit-logs` - View audit logs
- `GET /api/v1/admin/metrics` - System metrics

## 🚦 Health Checks

- `GET /health` - Basic health check
- `GET /api/v1/health` - API health check

## 📈 Monitoring

The application uses structured JSON logging for easy integration with log aggregation systems (ELK, CloudWatch, etc.).

Log levels:
- `INFO`: Normal operations
- `WARNING`: Potential issues
- `ERROR`: Errors requiring attention
- `CRITICAL`: Critical failures

## 🤝 Development

### Code Style

```bash
# Format code
black .

# Lint code
flake8

# Type checking
mypy app/
```

### Database Schema Changes

1. Update `prisma/schema.prisma`
2. Generate migration: `prisma migrate dev --name change_description`
3. Apply migration: `prisma migrate deploy`

## 📄 License

Proprietary - All rights reserved

## 🆘 Support

For issues and questions, contact the development team.

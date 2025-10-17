# RevRx Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Technology Stack](#technology-stack)
3. [Architecture Diagram](#architecture-diagram)
4. [Frontend Architecture](#frontend-architecture)
5. [Backend Architecture](#backend-architecture)
6. [Database Schema](#database-schema)
7. [Authentication & Authorization](#authentication--authorization)
8. [Key Features & Workflows](#key-features--workflows)
9. [External Integrations](#external-integrations)
10. [Security & Compliance](#security--compliance)
11. [Deployment Architecture](#deployment-architecture)

---

## System Overview

RevRx is a HIPAA-compliant healthcare coding review system that uses AI to analyze clinical notes and identify missed billing opportunities. The application helps healthcare providers maximize revenue by suggesting additional CPT/ICD codes based on clinical documentation.

### Key Capabilities
- **Clinical Note Analysis**: Upload and process clinical notes (TXT, PDF, DOCX)
- **Billing Code Review**: Submit existing billing codes for comparison
- **AI-Powered Suggestions**: Receive additional code recommendations with justifications
- **Revenue Analysis**: Calculate potential incremental revenue
- **HIPAA Compliance**: PHI detection, de-identification, and secure storage
- **Bulk Processing**: Handle multiple encounters simultaneously
- **FHIR Integration**: Connect with EHR systems via FHIR APIs
- **Real-time Updates**: WebSocket support for live report status
- **Webhook Notifications**: Event-driven integrations

---

## Technology Stack

### Frontend
- **Framework**: Next.js 15.5.4 (App Router, React 19, TypeScript 5)
- **UI Library**: HeroUI (NextUI fork) v2.8.4
- **Styling**: Tailwind CSS v4.1.13
- **State Management**: Zustand v5.0.8
- **Form Handling**: React Hook Form v7.63.0 + Zod v4.1.11
- **HTTP Client**: Axios v1.12.2
- **Icons**: Lucide React v0.544.0
- **Animations**: Framer Motion v12.23.22

### Backend
- **Framework**: FastAPI 0.115.6
- **Runtime**: Python 3.11+ with Uvicorn 0.34.0
- **Database**: PostgreSQL 16+ with Prisma 0.15.0 (Python)
- **Background Tasks**: Celery 5.4.0 with Redis 5.2.1
- **Authentication**: JWT (PyJWT 2.10.1, python-jose 3.3.0)
- **Password Hashing**: Bcrypt 4.2.1, Passlib 1.7.4
- **Logging**: Structlog 24.4.0

### AI/ML Services
- **NLP**: AWS Comprehend Medical (via boto3 1.35.99)
- **AI Analysis**: OpenAI GPT-4 (openai 1.59.9)
- **Medical Coding**: SNOMED CT to CPT crosswalk mapping

### Infrastructure & Services
- **File Storage**: AWS S3
- **Email**: Resend 2.5.1
- **Payments**: Stripe 11.3.0
- **FHIR Integration**: fhir.resources 7.1.0
- **Document Processing**: PyPDF2, python-docx, python-magic

### Development & Testing
- **Testing**: Jest (frontend), Pytest 8.3.4 (backend)
- **Linting**: ESLint (frontend), Flake8 (backend)
- **Type Checking**: TypeScript (frontend), MyPy (backend)
- **Code Formatting**: Prettier (frontend), Black (backend)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Client Layer                                │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Next.js Frontend (React 19 + TypeScript)                  │    │
│  │  - App Router (RSC + Client Components)                    │    │
│  │  - HeroUI Component Library                                │    │
│  │  - Zustand State Management                                │    │
│  │  - React Hook Form + Zod Validation                        │    │
│  └────────────────────────────────────────────────────────────┘    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS/REST API
                               │ (JWT Bearer Token)
┌──────────────────────────────▼──────────────────────────────────────┐
│                      API Gateway Layer                               │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  FastAPI Backend (Python)                                  │    │
│  │  - RESTful API Endpoints (/api/v1/*)                       │    │
│  │  - JWT Authentication                                      │    │
│  │  - Rate Limiting                                           │    │
│  │  - CORS Middleware                                         │    │
│  │  - WebSocket Support                                       │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────┬────────────────────────────────────────────────────────────┘
          │
          ├──────────────────────────────────────────────────────┐
          │                                                      │
┌─────────▼──────────────┐                          ┌──────────▼────────┐
│  Background Processing │                          │  Real-time Layer  │
│  ┌──────────────────┐  │                          │  ┌──────────────┐ │
│  │  Celery Workers  │  │                          │  │  WebSocket   │ │
│  │  - PHI Detection │  │                          │  │  - Status    │ │
│  │  - FHIR Sync     │  │                          │  │    Updates   │ │
│  │  - Report Gen    │  │                          │  │  - Progress  │ │
│  │  - Webhooks      │  │                          │  └──────────────┘ │
│  └──────────────────┘  │                          └───────────────────┘
│  ┌──────────────────┐  │
│  │  Redis Queue     │  │
│  └──────────────────┘  │
└────────────────────────┘
          │
          │
┌─────────▼──────────────────────────────────────────────────────────┐
│                      Data & Storage Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐   ��
│  │   PostgreSQL    │  │    AWS S3       │  │  Redis Cache     │   │
│  │   - Users       │  │  - Documents    │  │  - Sessions      │   │
│  │   - Encounters  │  │  - Files        │  │  - Task Queue    │   │
│  │   - Reports     │  │  - PHI Storage  │  │  - Rate Limits   │   │
│  │   - Audit Logs  │  │                 │  │                  │   │
│  └─────────────────┘  └─────────────────┘  └──────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
          │
          │
┌─────────▼──────────────────────────────────────────────────────────┐
│                    External Services Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   OpenAI     │  │     AWS      │  │    Stripe    │             │
│  │   - GPT-4    │  │  Comprehend  │  │  - Payments  │             │
│  │   - Analysis │  │   Medical    │  │  - Subs      │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│  ┌──────────────┐  ┌──────────────┐                               │
│  │    Resend    │  │     FHIR     │                               │
│  │   - Email    │  │     EHR      │                               │
│  └──────────────┘  └──────────────┘                               │
└────────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture

### Directory Structure

```
src/
├── app/                          # Next.js App Router
│   ├── (auth)/                   # Authentication routes (grouped)
│   │   ├── login/
│   │   ├── register/
│   │   ├── verify-email/
│   │   └── forgot-password/
│   ├── (dashboard)/              # Protected dashboard routes
│   │   ├── summary/              # Dashboard summary
│   │   ├── encounters/           # Encounter management
│   │   │   ├── new/              # Single encounter upload
│   │   │   └── bulk-upload/      # Bulk upload interface
│   │   ├── reports/              # Report viewing
│   │   ├── settings/             # User settings
│   │   ├── subscription/         # Subscription management
│   │   └── admin/                # Admin panel
│   ├── reports/                  # Public report status pages
│   ├── api/                      # Next.js API routes
│   │   ├── auth/
│   │   │   └── set-cookie/       # Cookie management
│   │   └── health/               # Health check
│   ├── layout.tsx                # Root layout
│   ├── page.tsx                  # Landing page
│   └── globals.css               # Global styles
├── components/                   # React components
│   ├── auth/                     # Auth-related components
│   ├── encounters/               # Encounter components
│   ├── reports/                  # Report display components
│   ├── analysis/                 # Analysis visualizations
│   ├── ui/                       # Base UI components
│   ├── forms/                    # Form components
│   ├── layout/                   # Layout components
│   ├── upload/                   # File upload components
│   ├── settings/                 # Settings components
│   ├── ErrorBoundary.tsx         # Error boundary wrapper
│   ├── ErrorFallback.tsx         # Error fallback UI
│   ├── CookieSync.tsx            # Cookie synchronization
│   └── Providers.tsx             # Context providers
├── store/                        # Zustand state stores
│   ├── authStore.ts              # Authentication state
│   ├── encounterStore.ts         # Encounter state
│   └── useBulkUploadStore.ts     # Bulk upload state
├── lib/                          # Utilities and configs
│   ├── api/                      # API client
│   │   ├── client.ts             # Axios instance
│   │   ├── endpoints.ts          # API endpoints
│   │   └── users.ts              # User API calls
│   ├── schemas/                  # Zod validation schemas
│   ├── notifications.ts          # Notification utilities
│   └── utils.ts                  # Helper functions
├── hooks/                        # Custom React hooks
├── types/                        # TypeScript type definitions
└── middleware.ts                 # Next.js middleware (auth)
```

### State Management

#### Zustand Stores

**authStore.ts** - Authentication state
- Manages user session, JWT token
- Syncs token to localStorage and cookies
- Handles logout and session cleanup

**encounterStore.ts** - Encounter state
- Tracks encounter submissions
- Manages encounter list and filters

**useBulkUploadStore.ts** - Bulk upload state
- File queue management
- Upload progress tracking
- Duplicate detection handling

### Routing & Navigation

#### Route Groups
- **(auth)**: Public authentication pages
- **(dashboard)**: Protected dashboard pages (requires authentication)

#### Middleware Protection
- Checks for `auth_token` cookie
- Redirects unauthenticated users to `/login`
- Public routes: `/`, `/login`, `/register`, `/verify-email`, `/forgot-password`
- Admin routes: `/admin/*` (future role-based protection)

### API Communication

#### Client Configuration ([src/lib/api/client.ts](src/lib/api/client.ts))
```typescript
baseURL: http://localhost:8000/api (dev)
timeout: 120000ms (2 minutes for long-running reports)
```

**Request Interceptor**:
- Attaches JWT token from localStorage to `Authorization` header
- Handles FormData content type

**Response Interceptor**:
- Redirects to `/login` on 401 Unauthorized
- Clears auth token from localStorage

### Form Handling

- **React Hook Form** for form state management
- **Zod** schemas for validation
- Centralized schemas in [src/lib/schemas/](src/lib/schemas/)
- Consistent error display patterns

### Error Handling

#### ErrorBoundary Component
- Wraps complex data-display components
- Prevents crashes from breaking entire page
- Development mode error details
- Custom fallback UI options

**Usage Pattern**:
```tsx
<ErrorBoundary>
  <ComplexComponent />
</ErrorBoundary>
```

#### ErrorFallback Variants
- `default` - Full error display with actions
- `minimal` - Compact inline error message
- `detailed` - Includes error stack trace (development)

### Cookie Synchronization

**CookieSync Component** ([src/components/CookieSync.tsx](src/components/CookieSync.tsx))
- Syncs auth token from Zustand store to cookies
- Ensures middleware can access authentication state
- Handles SSR/client hydration edge cases

---

## Backend Architecture

### Directory Structure

```
backend/
├── app/
│   ├── api/                      # API endpoints
│   │   └── v1/                   # API version 1
│   │       ├── admin.py          # Admin operations
│   │       ├── auth.py           # Authentication endpoints
│   │       ├── users.py          # User management
│   │       ├── encounters.py     # Encounter submission/retrieval
│   │       ├── reports.py        # Report generation/viewing
│   │       ├── fhir.py           # FHIR webhook receiver
│   │       ├── fhir_connections.py  # FHIR connection management
│   │       ├── monitoring.py     # System monitoring
│   │       ├── websocket.py      # WebSocket connections
│   │       ├── audit_logs.py     # Audit log retrieval
│   │       └── router.py         # Route aggregation
│   ├── core/                     # Core functionality
│   │   ├── config.py             # Settings (Pydantic)
│   │   ├── database.py           # Prisma client
│   │   ├── logging.py            # Structured logging
│   │   ├── security.py           # Auth utilities
│   │   ├── storage.py            # S3 storage
│   │   └── rate_limit_middleware.py  # Rate limiting
│   ├── schemas/                  # Pydantic models
│   │   ├── auth.py               # Auth request/response
│   │   ├── user.py               # User schemas
│   │   ├── encounter.py          # Encounter schemas
│   │   ├── report.py             # Report schemas
│   │   └── ...
│   ├── services/                 # Business logic
│   │   ├── openai_service.py    # OpenAI integration
│   │   ├── comprehend_medical.py  # AWS Comprehend Medical
│   │   ├── phi_handler.py       # PHI detection/de-identification
│   │   ├── report_generator.py  # Report creation
│   │   ├── report_processor.py  # Report processing pipeline
│   │   ├── code_extraction.py   # Code extraction logic
│   │   ├── code_comparison.py   # Code comparison
│   │   ├── snomed_crosswalk.py  # SNOMED to CPT mapping
│   │   ├── stripe_service.py    # Payment processing
│   │   ├── email.py             # Email notifications
│   │   ├── webhook_service.py   # Webhook delivery
│   │   ├── api_key_service.py   # API key management
│   │   ├── duplicate_detection.py  # File deduplication
│   │   ├── data_retention.py    # Data retention policies
│   │   └── fhir/                # FHIR integration services
│   ├── tasks/                    # Celery background tasks
│   │   ├── encounter_tasks.py   # Encounter processing
│   │   ├── phi_processing.py    # PHI detection tasks
│   │   ├── fhir_processing.py   # FHIR sync tasks
│   │   ├── report_tasks.py      # Report generation tasks
│   │   ├── webhook_tasks.py     # Webhook delivery tasks
│   │   ├── subscription_tasks.py  # Subscription management
│   │   └── retention_tasks.py   # Data retention tasks
│   ├── utils/                    # Utility functions
│   ├── celery_app.py            # Celery configuration
│   └── main.py                  # FastAPI app entry point
├── prisma/
│   └── schema.prisma            # Database schema
├── tests/                       # Test suite
│   ├── unit/
│   └── integration/
├── scripts/                     # Utility scripts
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pytest.ini
```

### API Architecture

#### RESTful API Design
- **Base URL**: `/api/v1`
- **Authentication**: JWT Bearer Token or API Key
- **Rate Limiting**: API key-based (default 100 req/min)
- **Response Format**: JSON
- **Error Format**: Consistent error responses

#### Key Endpoints

**Authentication** (`/api/v1/auth/`)
- `POST /register` - User registration
- `POST /login` - User login (returns JWT)
- `POST /verify-email` - Email verification
- `POST /forgot-password` - Password reset request
- `POST /reset-password` - Password reset

**Users** (`/api/v1/users/`)
- `GET /me` - Get current user
- `PUT /me` - Update user profile
- `GET /subscription-status` - Check subscription

**Encounters** (`/api/v1/encounters/`)
- `POST /` - Submit single encounter
- `POST /bulk` - Bulk encounter submission
- `GET /` - List user encounters
- `GET /{encounter_id}` - Get encounter details
- `DELETE /{encounter_id}` - Delete encounter

**Reports** (`/api/v1/reports/`)
- `GET /{encounter_id}` - Get report for encounter
- `GET /{encounter_id}/status` - Get processing status
- `GET /{encounter_id}/download` - Download report (YAML/JSON)

**FHIR** (`/api/v1/fhir/`)
- `POST /webhook` - Receive FHIR webhooks
- `POST /connections` - Configure FHIR connection
- `GET /connections` - List FHIR connections

**WebSocket** (`/api/v1/ws/reports/{encounter_id}`)
- Real-time report status updates

**Admin** (`/api/v1/admin/`)
- `GET /users` - List all users
- `GET /stats` - System statistics

### Background Task Processing

#### Celery Workers
- **Queue**: Redis-based message broker
- **Concurrency**: Multiple workers for parallel processing
- **Retry Logic**: Exponential backoff for failed tasks
- **Dead Letter Queue**: Failed task handling

#### Task Categories

**Encounter Processing** ([tasks/encounter_tasks.py](backend/app/tasks/encounter_tasks.py))
1. File upload to S3
2. Virus scanning
3. Text extraction (PDF, DOCX)
4. Trigger PHI detection

**PHI Processing** ([tasks/phi_processing.py](backend/app/tasks/phi_processing.py))
1. Detect PHI entities using AWS Comprehend Medical
2. De-identify clinical notes
3. Encrypt and store PHI mappings
4. Trigger report generation

**Report Generation** ([tasks/report_tasks.py](backend/app/tasks/report_tasks.py))
1. Extract ICD-10 codes (AWS Comprehend Medical)
2. Extract SNOMED codes (AWS Comprehend Medical)
3. Map SNOMED to CPT codes (crosswalk)
4. Analyze with OpenAI GPT-4
5. Compare billed vs. suggested codes
6. Calculate incremental revenue
7. Generate report (YAML/JSON)

**FHIR Sync** ([tasks/fhir_processing.py](backend/app/tasks/fhir_processing.py))
1. Poll FHIR server for encounters
2. Transform FHIR resources to internal format
3. Create encounters from FHIR data

**Webhook Delivery** ([tasks/webhook_tasks.py](backend/app/tasks/webhook_tasks.py))
1. Sign payloads with HMAC-SHA256
2. Deliver to configured endpoints
3. Retry failed deliveries (exponential backoff)
4. Log delivery status

### Service Layer

#### AI/ML Services

**OpenAI Service** ([services/openai_service.py](backend/app/services/openai_service.py))
- GPT-4 integration for code analysis
- Structured prompt engineering
- Confidence scoring
- Token usage tracking

**AWS Comprehend Medical** ([services/comprehend_medical.py](backend/app/services/comprehend_medical.py))
- Medical entity detection
- ICD-10 code extraction
- SNOMED code extraction
- RxNorm medication codes
- Protected Health Information (PHI) detection

**SNOMED Crosswalk** ([services/snomed_crosswalk.py](backend/app/services/snomed_crosswalk.py))
- SNOMED CT to CPT mapping
- CMS crosswalk database
- Mapping confidence scores

#### PHI Handling

**PHI Handler** ([services/phi_handler.py](backend/app/services/phi_handler.py))
1. **Detection**: AWS Comprehend Medical identifies PHI entities
2. **Tokenization**: Replace PHI with tokens (e.g., `[NAME_1]`, `[DATE_1]`)
3. **Encryption**: AES-256 encryption of PHI mapping
4. **Storage**: Store encrypted mapping in database
5. **Re-identification** (if needed): Decrypt and restore original PHI

**PHI Types Detected**:
- Names, addresses, phone numbers
- Dates (birth, admission, discharge)
- Medical record numbers
- Social security numbers
- Account numbers

#### Report Processing Pipeline

**Report Processor** ([services/report_processor.py](backend/app/services/report_processor.py))

```python
1. Load encounter and files
2. Extract text from documents
3. Detect and de-identify PHI
4. Extract medical codes (AWS Comprehend Medical)
   - ICD-10 diagnoses
   - SNOMED procedures
5. Map SNOMED to CPT (crosswalk)
6. Analyze with OpenAI GPT-4
   - Compare billed codes
   - Suggest additional codes
   - Provide justifications
7. Calculate revenue impact
8. Generate structured report
9. Save to database
10. Trigger webhooks
11. Send WebSocket update
```

---

## Database Schema

### Core Models

#### User
**Table**: `users`

```prisma
- id: UUID (PK)
- email: String (unique)
- passwordHash: String
- role: ADMIN | MEMBER
- emailVerified: Boolean
- profileComplete: Boolean

# Profile
- name, phone, timezone, language

# Preferences
- theme (light/dark/system)
- emailNotifications
- dateFormat, timeFormat

# Subscription
- trialEndDate: DateTime
- subscriptionStatus: INACTIVE | TRIAL | ACTIVE | CANCELLED | EXPIRED
- stripeCustomerId: String

# Relations
- encounters: Encounter[]
- subscriptions: Subscription[]
- auditLogs: AuditLog[]
- tokens: Token[]
- apiKeys: ApiKey[]
- webhooks: Webhook[]
- fhirConnections: FhirConnection[]
```

#### Encounter
**Table**: `encounters`

```prisma
- id: UUID (PK)
- userId: UUID (FK -> users)
- batchId: String (for bulk uploads)

# Status
- status: PENDING | PROCESSING | COMPLETE | FAILED
- processingStartedAt: DateTime
- processingCompletedAt: DateTime
- processingTime: Int (milliseconds)

# Clinical metadata (de-identified)
- patientAge: Int
- patientSex: String
- visitDate: DateTime

# Search/matching
- fileHash: String (SHA-256)
- providerInitials: String
- dateOfService: DateTime
- encounterType: String

# FHIR integration
- fhirEncounterId: String (canonical FHIR ID)
- fhirPatientId: String
- fhirProviderId: String
- fhirSourceSystem: String
- encounterSource: FILE_UPLOAD | FHIR

# Error handling
- errorMessage: String
- retryCount: Int

# Relations
- user: User
- uploadedFiles: UploadedFile[]
- billingCodes: BillingCode[]
- icd10Codes: ICD10Code[]
- snomedCodes: SNOMEDCode[]
- report: Report
- phiMapping: PhiMapping
```

#### Report
**Table**: `reports`

```prisma
- id: UUID (PK)
- encounterId: UUID (FK -> encounters, unique)

# Processing status
- status: PENDING | PROCESSING | COMPLETE | FAILED
- processingStartedAt: DateTime
- processingCompletedAt: DateTime
- processingTimeMs: Int

# Progress tracking
- progressPercent: Int
- currentStep: String

# Error handling
- errorMessage: String
- errorDetails: Json
- retryCount: Int

# Analysis results
- billedCodes: Json (submitted codes)
- suggestedCodes: Json (AI recommendations)
- extractedIcd10Codes: Json
- extractedSnomedCodes: Json
- cptSuggestions: Json (from SNOMED crosswalk)

# Revenue analysis
- incrementalRevenue: Float

# AI metadata
- aiModel: String (e.g., "gpt-4")
- confidenceScore: Float

# Report formats
- reportYaml: String
- reportJson: String

# Relations
- encounter: Encounter
```

#### UploadedFile
**Table**: `uploaded_files`

```prisma
- id: UUID (PK)
- encounterId: UUID (FK -> encounters)

# File metadata
- fileType: CLINICAL_NOTE_TXT | CLINICAL_NOTE_PDF | CLINICAL_NOTE_DOCX
           | BILLING_CODES_CSV | BILLING_CODES_JSON
- fileName: String
- filePath: String (S3 key)
- fileSize: Int
- mimeType: String
- extractedText: Text

# Duplicate detection
- fileHash: String (SHA-256)
- isDuplicate: Boolean
- duplicateHandling: SKIP | REPLACE | PROCESS_AS_NEW
- originalFileId: UUID (FK)

# Virus scanning
- scanStatus: PENDING | CLEAN | INFECTED | ERROR
- scanResult: String

# Relations
- encounter: Encounter
```

#### PhiMapping
**Table**: `phi_mappings`

```prisma
- id: UUID (PK)
- encounterId: UUID (FK -> encounters, unique)

# PHI data (encrypted)
- encryptedMapping: String (AES-256 encrypted JSON)

# PHI metadata
- phiDetected: Boolean
- phiEntityCount: Int

# De-identified text
- deidentifiedText: Text

# Relations
- encounter: Encounter
```

#### BillingCode
**Table**: `billing_codes`

```prisma
- id: UUID (PK)
- encounterId: UUID (FK -> encounters)

# Code details
- code: String (CPT/ICD code)
- codeType: String (CPT, ICD10, etc.)
- description: String
- isBilled: Boolean

# Relations
- encounter: Encounter
```

#### ICD10Code
**Table**: `icd10_codes`

```prisma
- id: UUID (PK)
- encounterId: UUID (FK -> encounters)

# Code details
- code: String (ICD-10-CM)
- description: String

# AWS Comprehend Medical metadata
- category: String
- type: String
- score: Float (0-1 confidence)

# Text context
- beginOffset: Int
- endOffset: Int
- text: String (matched text from note)

# Relations
- encounter: Encounter
```

#### SNOMEDCode
**Table**: `snomed_codes`

```prisma
- id: UUID (PK)
- encounterId: UUID (FK -> encounters)

# Code details
- code: String (SNOMED CT concept ID)
- description: String

# AWS Comprehend Medical metadata
- category: String
- type: String
- score: Float (0-1 confidence)

# Text context
- beginOffset: Int
- endOffset: Int
- text: String (matched text from note)

# Relations
- encounter: Encounter
```

#### SNOMEDCrosswalk
**Table**: `snomed_crosswalk`

```prisma
- id: UUID (PK)

# Mapping
- snomedCode: String
- snomedDescription: String
- cptCode: String
- cptDescription: String

# Metadata
- mappingType: String (EXACT, APPROXIMATE, BROADER)
- confidence: Float

# Source
- source: String (CMS, SNOMED_INTERNATIONAL)
- sourceVersion: String
- effectiveDate: DateTime

# Unique constraint: (snomedCode, cptCode)
```

### Supporting Models

#### Subscription
**Table**: `subscriptions`

```prisma
- id: UUID (PK)
- userId: UUID (FK -> users)

# Stripe integration
- stripeSubscriptionId: String (unique)
- stripeCustomerId: String
- stripePriceId: String

# Subscription details
- status: SubscriptionStatus
- currentPeriodStart: DateTime
- currentPeriodEnd: DateTime
- cancelAtPeriodEnd: Boolean
- canceledAt: DateTime

# Billing
- amount: Float
- currency: String (default: usd)
- billingInterval: String (month/year)

# Relations
- user: User
```

#### Token
**Table**: `tokens`

```prisma
- id: UUID (PK)
- userId: UUID (FK -> users)

# Token details
- token: String (unique)
- tokenType: EMAIL_VERIFICATION | PASSWORD_RESET | API_KEY
- expiresAt: DateTime
- used: Boolean

# Relations
- user: User
```

#### ApiKey
**Table**: `api_keys`

```prisma
- id: UUID (PK)
- userId: UUID (FK -> users)

# Key details
- name: String (user-provided)
- keyHash: String (unique, hashed)
- keyPrefix: String (first 8 chars for identification)

# Permissions
- isActive: Boolean
- rateLimit: Int (requests/minute, default 100)

# Usage tracking
- lastUsedAt: DateTime
- usageCount: Int

# Expiration
- expiresAt: DateTime

# Relations
- user: User
- webhooks: Webhook[]
```

#### Webhook
**Table**: `webhooks`

```prisma
- id: UUID (PK)
- userId: UUID (FK -> users)
- apiKeyId: UUID (FK -> api_keys, optional)

# Configuration
- url: String (webhook endpoint)
- events: String[] (e.g., "encounter.completed")
- secret: String (for HMAC signature)

# Status
- isActive: Boolean
- failureCount: Int
- lastSuccessAt: DateTime
- lastFailureAt: DateTime
- lastError: String

# Relations
- user: User
- apiKey: ApiKey
- deliveries: WebhookDelivery[]
```

#### WebhookDelivery
**Table**: `webhook_deliveries`

```prisma
- id: UUID (PK)
- webhookId: UUID (FK -> webhooks)

# Delivery details
- event: String
- payload: Json

# HTTP details
- requestUrl: String
- requestMethod: String (default: POST)
- requestHeaders: Json

# Response
- responseStatus: Int
- responseBody: String
- responseTime: Int (milliseconds)

# Status
- status: PENDING | DELIVERED | FAILED | RETRYING
- error: String

# Retry tracking
- attemptNumber: Int
- maxAttempts: Int (default: 3)
- nextRetryAt: DateTime

# Relations
- webhook: Webhook
```

#### AuditLog
**Table**: `audit_logs`

```prisma
- id: UUID (PK)
- userId: UUID (FK -> users, nullable)

# Action details
- action: String (UPLOAD_FILE, VIEW_REPORT, LOGIN_SUCCESS, etc.)
- resourceType: String (Encounter, Report, etc.)
- resourceId: String

# Request metadata
- ipAddress: String
- userAgent: String

# Context
- metadata: Json (additional structured data)

# Relations
- user: User
```

#### FhirConnection
**Table**: `fhir_connections`

```prisma
- id: UUID (PK)
- userId: UUID (FK -> users)

# FHIR server configuration
- fhirServerUrl: String (base URL)
- fhirVersion: String (R4, R5, etc.)

# Authentication
- authType: OAUTH2 | BASIC | API_KEY | SMART_ON_FHIR
- clientId: String
- clientSecretHash: String (encrypted)
- tokenEndpoint: String
- scope: String

# Connection metadata
- isActive: Boolean
- lastSyncAt: DateTime
- lastError: String

# Relations
- user: User
```

---

## Authentication & Authorization

### Frontend Authentication

#### JWT Token Flow
1. User logs in via `/login` form
2. Frontend sends credentials to backend `/api/v1/auth/login`
3. Backend validates credentials, returns JWT token
4. Frontend stores token in:
   - **Zustand store** (authStore)
   - **localStorage** (`auth_token`)
   - **Cookie** (`auth_token`, HttpOnly-like behavior for middleware)

#### Middleware Protection ([src/middleware.ts](src/middleware.ts))
```typescript
Public routes: ["/", "/login", "/register", "/verify-email", "/forgot-password"]
Admin routes: ["/admin"]

Middleware checks for "auth_token" cookie:
- If no token and not public route -> redirect to /login
- If admin route -> allow (role check pending)
- Otherwise -> allow
```

#### Cookie Synchronization
**CookieSync component** syncs Zustand auth token to document.cookie:
- Max age: 7 days
- SameSite: Lax
- Secure: true (production only)

### Backend Authentication

#### JWT Configuration
- **Algorithm**: HS256
- **Secret**: `JWT_SECRET_KEY` (environment variable)
- **Expiration**: Configurable (default: 7 days)
- **Claims**: `user_id`, `email`, `role`

#### Authentication Methods

**1. JWT Bearer Token** (User sessions)
```
Authorization: Bearer <jwt_token>
```

**2. API Key** (Programmatic access)
```
X-API-Key: <api_key>
```

#### Security Utilities ([app/core/security.py](backend/app/core/security.py))
- `create_access_token()` - Generate JWT
- `verify_token()` - Validate JWT
- `hash_password()` - Bcrypt password hashing
- `verify_password()` - Verify hashed password
- `hash_api_key()` - Hash API keys for storage
- `verify_api_key()` - Validate API key

#### Protected Endpoints
Use dependency injection:
```python
from app.core.security import get_current_user

@router.get("/me")
async def get_current_user_endpoint(
    current_user: User = Depends(get_current_user)
):
    return current_user
```

### Role-Based Access Control (RBAC)

#### Roles
- **ADMIN**: Full system access, admin panel, user management
- **MEMBER**: Standard user access, own encounters/reports

#### Implementation (Planned)
```python
from app.core.security import require_role

@router.get("/admin/users")
async def list_users(
    current_user: User = Depends(require_role("ADMIN"))
):
    # Admin-only endpoint
```

### Email Verification

#### Flow
1. User registers -> email verification token generated
2. Email sent with verification link
3. User clicks link -> token verified
4. `emailVerified` flag set to `true`
5. User can now log in

#### Token Management
- **Type**: `EMAIL_VERIFICATION`
- **Expiration**: 24 hours
- **Storage**: `tokens` table
- **One-time use**: `used` flag prevents reuse

### Password Reset

#### Flow
1. User requests reset via `/forgot-password`
2. Backend generates reset token
3. Email sent with reset link
4. User clicks link, submits new password
5. Token verified, password updated
6. Token marked as used

---

## Key Features & Workflows

### 1. Encounter Submission (Single)

**User Flow**:
1. Navigate to `/encounters/new`
2. Upload clinical note (TXT, PDF, DOCX)
3. Upload billing codes (CSV, JSON, or manual entry)
4. Submit encounter

**Backend Processing**:
```
1. Validate files (size, type, virus scan)
2. Upload to S3 (encrypted at rest)
3. Create Encounter record (status: PENDING)
4. Trigger Celery task: process_encounter()
   ├── Extract text from files
   ├── Detect PHI -> create PhiMapping
   ├── Extract ICD-10 codes (AWS Comprehend Medical)
   ├── Extract SNOMED codes (AWS Comprehend Medical)
   ├── Map SNOMED to CPT (crosswalk)
   ├── Analyze with OpenAI GPT-4
   ├── Compare billed vs. suggested codes
   ├── Calculate incremental revenue
   ├── Generate Report (status: COMPLETE)
   └── Send webhook notifications
5. Update Encounter (status: COMPLETE)
6. Send WebSocket update to client
```

### 2. Bulk Encounter Upload

**User Flow**:
1. Navigate to `/encounters/bulk-upload`
2. Upload multiple files (clinical notes + billing codes)
3. Review file list, handle duplicates
4. Submit batch

**Backend Processing**:
- Same as single encounter, but:
  - All encounters share same `batchId`
  - Processed in parallel by Celery workers
  - Progress tracked per encounter
  - Bulk report summary generated

**Duplicate Detection**:
- File hash (SHA-256) calculated
- Check against existing files
- User options:
  - **Skip**: Ignore duplicate
  - **Replace**: Update existing encounter
  - **Process as new**: Create new encounter

### 3. Report Generation

**Processing Steps**:

**Step 1: PHI Detection & De-identification**
- AWS Comprehend Medical `detect_phi()` API
- Replace PHI entities with tokens
- Store encrypted mapping in `phi_mappings`

**Step 2: Medical Code Extraction**
- AWS Comprehend Medical `detect_entities_v2()` API
- Extract ICD-10 diagnosis codes
- Extract SNOMED procedure codes
- Store in `icd10_codes` and `snomed_codes`

**Step 3: SNOMED to CPT Mapping**
- Query `snomed_crosswalk` table
- Map extracted SNOMED codes to CPT codes
- Include mapping confidence scores

**Step 4: AI Analysis**
- Send de-identified note + billed codes to OpenAI GPT-4
- Structured prompt engineering
- Request:
  - Additional code suggestions
  - Justifications
  - Confidence scores
  - Revenue estimates

**Step 5: Code Comparison**
- Compare billed codes vs. suggested codes
- Identify missed codes
- Calculate incremental revenue

**Step 6: Report Generation**
- Structure report as JSON/YAML
- Include:
  - Billed codes
  - Suggested additional codes with justifications
  - Extracted ICD-10/SNOMED codes
  - CPT suggestions from crosswalk
  - Incremental revenue estimate
  - AI confidence score

### 4. Real-time Status Updates

**WebSocket Connection**:
```
ws://localhost:8000/api/v1/ws/reports/{encounter_id}
```

**Events**:
- `status_update`: Processing status change
- `progress_update`: Progress percentage
- `report_complete`: Report ready

**Frontend Usage**:
```typescript
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/reports/${encounterId}`);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Update UI with status
};
```

### 5. FHIR Integration

**FHIR Webhook Receiver** (`/api/v1/fhir/webhook`)
- Receives FHIR Encounter resources from EHR
- Validates FHIR resource structure
- Transforms to internal Encounter format
- Triggers processing pipeline

**FHIR Connection Management**
- Configure FHIR server URL and credentials
- Support for multiple EHR systems
- OAuth2/SMART on FHIR authentication
- Periodic sync of encounters

**FHIR Encounter Mapping**:
```
FHIR Encounter -> RevRx Encounter
├── Encounter.id -> fhirEncounterId
├── Encounter.subject -> fhirPatientId
├── Encounter.participant -> fhirProviderId
├── Encounter.serviceProvider -> fhirSourceSystem
└── DocumentReference -> UploadedFile (clinical note)
```

### 6. Webhook Notifications

**Configuration** (`/api/v1/webhooks`)
- Create webhook endpoint
- Subscribe to events:
  - `encounter.submitted`
  - `encounter.processing`
  - `encounter.completed`
  - `encounter.failed`

**Delivery**:
- HMAC-SHA256 signature in `X-Hub-Signature-256` header
- Automatic retry with exponential backoff
- Delivery logs in `webhook_deliveries` table

**Payload Example**:
```json
{
  "event": "encounter.completed",
  "timestamp": "2025-10-15T10:30:00Z",
  "data": {
    "encounter_id": "uuid",
    "status": "COMPLETE",
    "report_id": "uuid"
  }
}
```

### 7. Subscription Management

**Stripe Integration**:
- Create customer on registration
- 7-day free trial (no credit card required)
- Subscription plans: Monthly ($99), Annual ($990)
- Webhook handling for subscription events

**Trial Management**:
- `trialEndDate` tracked in User model
- `subscriptionStatus` updated automatically
- Middleware checks subscription status (planned)
- Grace period for expired subscriptions

### 8. Admin Panel

**Features** (Planned):
- User management
- System statistics
- Encounter monitoring
- Report analytics
- Audit log viewing

---

## External Integrations

### AWS Comprehend Medical

**Purpose**: Medical NLP for entity extraction and PHI detection

**APIs Used**:
- `detect_phi()` - PHI entity detection
- `detect_entities_v2()` - Medical entity extraction (ICD-10, SNOMED, RxNorm)
- `infer_icd10_cm()` - ICD-10 code inference
- `infer_snomed_ct()` - SNOMED CT code inference

**Configuration**:
```python
AWS_REGION: us-east-1 (Comprehend Medical availability)
AWS_ACCESS_KEY_ID: <access_key>
AWS_SECRET_ACCESS_KEY: <secret_key>
```

### AWS S3

**Purpose**: Secure file storage

**Buckets**:
- Clinical notes (encrypted at rest)
- Billing code files
- De-identified documents

**Configuration**:
```python
AWS_S3_BUCKET_NAME: <bucket_name>
AWS_S3_REGION: us-east-1
```

**Features**:
- Server-side encryption (AES-256)
- Object versioning
- Lifecycle policies for data retention
- Presigned URLs for temporary access

### OpenAI GPT-4

**Purpose**: AI-powered code analysis and suggestions

**Model**: `gpt-4` (configurable to `gpt-4-turbo`, `gpt-3.5-turbo`)

**Usage**:
- Analyze de-identified clinical notes
- Compare billed codes with documentation
- Suggest additional codes with justifications
- Revenue impact estimation

**Prompt Engineering**:
- Structured prompts in [services/prompt_templates.py](backend/app/services/prompt_templates.py)
- Few-shot examples for consistent output
- JSON response format for parsing

**Configuration**:
```python
OPENAI_API_KEY: <api_key>
OPENAI_MODEL: gpt-4
OPENAI_TEMPERATURE: 0.2 (low for consistency)
OPENAI_MAX_TOKENS: 2000
```

### Stripe

**Purpose**: Payment processing and subscription management

**Features**:
- Customer creation
- Subscription management
- Payment method storage
- Webhook handling for events

**Webhooks**:
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_succeeded`
- `invoice.payment_failed`

**Configuration**:
```python
STRIPE_SECRET_KEY: <secret_key>
STRIPE_PUBLISHABLE_KEY: <publishable_key>
STRIPE_WEBHOOK_SECRET: <webhook_secret>
```

### Resend (Email Service)

**Purpose**: Transactional email delivery

**Email Types**:
- Email verification
- Password reset
- Welcome emails
- Subscription notifications
- Report completion alerts

**Configuration**:
```python
RESEND_API_KEY: <api_key>
EMAIL_FROM: noreply@revrx.com
EMAIL_FROM_NAME: RevRx
```

### FHIR EHR Systems

**Purpose**: EHR integration for automatic encounter ingestion

**Supported Standards**:
- FHIR R4
- FHIR R5 (planned)
- SMART on FHIR authentication

**Authentication Methods**:
- OAuth2
- Basic Auth
- API Key
- SMART on FHIR

**Resources Consumed**:
- `Encounter` - Clinical encounters
- `DocumentReference` - Clinical notes
- `Patient` - Patient demographics (de-identified)
- `Practitioner` - Provider information

---

## Security & Compliance

### HIPAA Compliance

#### PHI Protection

**1. PHI Detection**
- AWS Comprehend Medical identifies 18+ PHI categories
- Automatic detection during processing

**2. De-identification**
- Replace PHI entities with tokens (e.g., `[NAME_1]`, `[DATE_1]`)
- Store de-identified text separately
- Encrypted PHI mapping for re-identification (if needed)

**3. Encryption**

**At Rest**:
- Database: PostgreSQL with encryption
- Files: S3 server-side encryption (AES-256)
- PHI Mappings: AES-256 encryption before storage

**In Transit**:
- HTTPS/TLS 1.3 for all API communication
- Encrypted WebSocket connections (WSS)

**4. Access Control**
- Role-based access control (RBAC)
- User can only access own encounters
- Admin role for system administration
- API key-based authentication for integrations

**5. Audit Logging**
- All PHI access logged to `audit_logs`
- IP address, user agent tracking
- Action, resource type, resource ID captured
- Immutable audit log (no updates/deletes)

**6. Data Retention**
- Configurable retention policies
- Automatic deletion of old encounters/reports
- PHI purging after retention period
- Audit logs retained for compliance period

#### Security Best Practices

**Password Security**:
- Bcrypt hashing (cost factor: 12)
- No plaintext password storage
- Password reset tokens (one-time use, 1-hour expiration)

**API Key Security**:
- SHA-256 hashing before storage
- Key prefix for identification
- Rate limiting per key
- Expiration dates
- Usage tracking

**Session Security**:
- JWT tokens with short expiration
- HttpOnly cookies (via middleware simulation)
- Secure flag in production
- SameSite: Lax

**Input Validation**:
- Pydantic schemas for request validation
- Zod schemas for frontend validation
- File type validation
- File size limits
- Virus scanning before processing

**Output Sanitization**:
- HTML escaping in reports
- SQL injection prevention (Prisma ORM)
- XSS prevention

**Rate Limiting**:
- API key-based rate limiting
- Default: 100 requests/minute
- Configurable per key
- Rate limit headers in response

**CORS Configuration**:
- Whitelist specific origins
- Credentials support
- Controlled headers/methods

### Vulnerability Management

**Dependency Scanning**:
- Regular `npm audit` (frontend)
- Regular `pip audit` (backend)
- Automated security updates

**Monitoring**:
- Structured logging (Structlog)
- Error tracking
- Performance monitoring
- Anomaly detection (planned)

---

## Deployment Architecture

### Production Environment

#### Frontend (Next.js)
**Platform**: Vercel (recommended) or AWS Amplify

**Configuration**:
```bash
NODE_ENV=production
NEXT_PUBLIC_API_URL=https://api.revrx.com/api
```

**Build Command**: `npm run build`

**Features**:
- Edge Functions for API routes
- Automatic HTTPS
- CDN distribution
- Image optimization

#### Backend (FastAPI)
**Platform**: AWS ECS (Fargate) or Heroku

**Configuration**:
```bash
APP_ENV=production
APP_DEBUG=false
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
AWS_REGION=us-east-1
# ... other env vars
```

**Deployment**:
```bash
docker build -t revrx-backend .
docker push <registry>/revrx-backend:latest
```

**Scaling**:
- Auto-scaling based on CPU/memory
- Multiple Celery workers for background tasks
- Load balancer for API instances

#### Database (PostgreSQL)
**Platform**: AWS RDS or Heroku Postgres

**Configuration**:
- PostgreSQL 16+
- Multi-AZ deployment (production)
- Automated backups (daily)
- Point-in-time recovery
- Read replicas for analytics (optional)

#### Cache & Queue (Redis)
**Platform**: AWS ElastiCache or Heroku Redis

**Configuration**:
- Redis 7+
- Cluster mode for high availability
- Automatic failover
- Eviction policy: allkeys-lru

#### File Storage (S3)
**Configuration**:
- Bucket: `revrx-production`
- Region: `us-east-1`
- Encryption: AES-256 (server-side)
- Versioning: Enabled
- Lifecycle rules: Archive to Glacier after 90 days

### Development Environment

#### Local Setup
```bash
# Frontend
cd /path/to/revrx
npm install
npm run dev  # http://localhost:3000

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
prisma generate
prisma migrate dev
uvicorn app.main:app --reload  # http://localhost:8000

# Services
docker-compose up -d postgres redis
```

#### Docker Compose
```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: revrx
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  celery:
    build: ./backend
    command: celery -A app.celery_app worker --loglevel=info
    depends_on:
      - redis
      - postgres
```

### CI/CD Pipeline

#### GitHub Actions (Recommended)

**Frontend Pipeline**:
```yaml
name: Frontend CI/CD
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npm run lint
      - run: npm test
      - run: npm run build
      - name: Deploy to Vercel
        run: vercel --prod
```

**Backend Pipeline**:
```yaml
name: Backend CI/CD
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: pytest
      - run: flake8
      - run: mypy .
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Build Docker image
        run: docker build -t revrx-backend .
      - name: Push to registry
        run: docker push <registry>/revrx-backend:latest
      - name: Deploy to ECS
        run: aws ecs update-service ...
```

### Monitoring & Observability

**Logging**:
- Structured logging with Structlog
- Log aggregation (CloudWatch, Datadog)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

**Metrics**:
- API response times
- Error rates
- Database query performance
- Celery task processing times
- S3 upload/download latency

**Alerts**:
- High error rate (> 5%)
- Slow API responses (> 2s p95)
- Failed Celery tasks
- Database connection issues
- S3 upload failures

**Health Checks**:
- `/health` - Basic health check
- `/api/v1/monitoring/status` - Detailed system status
- Database connectivity
- Redis connectivity
- S3 accessibility

---

## Performance Considerations

### Frontend Optimization

**Code Splitting**:
- Next.js automatic code splitting by route
- Dynamic imports for heavy components
- Lazy loading for images

**Caching**:
- Static asset caching (1 year)
- API response caching (Zustand persist)
- SWR/React Query for data fetching (future)

**Bundle Size**:
- Tree shaking for unused code
- Minimize third-party dependencies
- Analyze bundle with `@next/bundle-analyzer`

### Backend Optimization

**Database**:
- Indexes on frequently queried fields
  - `encounters(userId, createdAt)`
  - `encounters(status)`
  - `reports(status)`
  - `audit_logs(userId, createdAt)`
- Connection pooling (Prisma default: 10 connections)
- Query optimization with `EXPLAIN ANALYZE`

**Caching**:
- Redis for:
  - Rate limiting data
  - Celery task queue
  - Session storage (future)
- Application-level caching for:
  - SNOMED crosswalk lookups
  - User profile data

**Background Tasks**:
- Celery workers for async processing
- Task prioritization (high, normal, low)
- Task result expiration
- Dead letter queue for failed tasks

**API Performance**:
- Async/await for I/O-bound operations
- Connection pooling for external APIs
- Batch processing for bulk operations
- Pagination for list endpoints

---

## Scalability Roadmap

### Current Limitations
- Single-region deployment
- Monolithic backend API
- Synchronous WebSocket updates

### Future Enhancements

**1. Multi-Region Deployment**
- Deploy backend to multiple AWS regions
- Use Route53 for geo-routing
- Replicate database with cross-region replication

**2. Microservices Architecture**
- Split backend into services:
  - Auth Service
  - Encounter Service
  - Report Service
  - Notification Service
  - FHIR Service

**3. Event-Driven Architecture**
- Replace Celery with AWS SQS/SNS
- Use EventBridge for event routing
- Implement CQRS for read/write separation

**4. Advanced Caching**
- Redis Cluster for distributed caching
- CDN caching for static assets
- Database query result caching

**5. Horizontal Scaling**
- Auto-scaling groups for API instances
- Multiple Celery worker pools
- Read replicas for database

**6. Performance Monitoring**
- APM tools (Datadog, New Relic)
- Distributed tracing (OpenTelemetry)
- Real-user monitoring (RUM)

---

## Appendix

### Environment Variables

#### Frontend (.env.local)
```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api

# Feature Flags
NEXT_PUBLIC_ENABLE_FHIR=true
```

#### Backend (.env)
```bash
# Application
APP_ENV=development
APP_DEBUG=true
SECRET_KEY=<random_secret>

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/revrx

# Redis
REDIS_URL=redis://localhost:6379/0

# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<access_key>
AWS_SECRET_ACCESS_KEY=<secret_key>
AWS_S3_BUCKET_NAME=revrx-dev

# OpenAI
OPENAI_API_KEY=<api_key>
OPENAI_MODEL=gpt-4

# Stripe
STRIPE_SECRET_KEY=<secret_key>
STRIPE_WEBHOOK_SECRET=<webhook_secret>

# Email
RESEND_API_KEY=<api_key>
EMAIL_FROM=noreply@revrx.com

# Security
JWT_SECRET_KEY=<jwt_secret>
PHI_ENCRYPTION_KEY=<32_byte_key>

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Allowed Hosts
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Useful Commands

#### Frontend
```bash
# Development
npm run dev                 # Start dev server
npm run build              # Production build
npm run start              # Start production server
npm run lint               # Run ESLint
npm test                   # Run tests

# Debugging
npm run dev -- --turbo     # Use Turbopack
```

#### Backend
```bash
# Development
uvicorn app.main:app --reload              # Start dev server
celery -A app.celery_app worker --loglevel=info  # Start Celery worker

# Database
prisma generate            # Generate Prisma client
prisma migrate dev         # Create and apply migration
prisma db push             # Push schema without migration
prisma studio              # Open Prisma Studio

# Testing
pytest                     # Run all tests
pytest -v                  # Verbose output
pytest --cov               # Coverage report
pytest -k "test_name"      # Run specific test

# Code Quality
black .                    # Format code
flake8                     # Lint code
mypy .                     # Type check
```

### API Documentation

**Development**: http://localhost:8000/api/docs (Swagger UI)
**Production**: Disabled for security

### Database Migrations

```bash
# Create new migration
prisma migrate dev --name add_feature

# Apply migrations (production)
prisma migrate deploy

# Reset database (development only)
prisma migrate reset
```

---

## Conclusion

RevRx is a modern, HIPAA-compliant healthcare coding review system built with scalability, security, and user experience in mind. The architecture leverages industry-standard technologies (Next.js, FastAPI, PostgreSQL) combined with cutting-edge AI services (OpenAI GPT-4, AWS Comprehend Medical) to deliver accurate, actionable coding recommendations that help healthcare providers maximize revenue while maintaining compliance.

The system is designed for:
- **Security**: Comprehensive PHI protection, encryption, and audit logging
- **Scalability**: Background task processing, caching, and horizontal scaling
- **Reliability**: Error handling, retry logic, and monitoring
- **Extensibility**: FHIR integration, webhook notifications, and API access

For questions or contributions, please refer to the repository documentation.

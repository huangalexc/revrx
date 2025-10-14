# Backend Debugging Tasks

## Current Status
- Backend server crashes on startup
- Multiple import errors blocking server initialization
- Registration endpoint not functional
- PostgreSQL database not running

## Critical Path Tasks

### 1. Fix Database Dependencies Module
**Priority:** CRITICAL
**Status:** BLOCKED - Current blocker

**Error:**
```
ImportError: cannot import name 'get_db' from 'app.core.deps'
```

**Location:** `/backend/app/api/subscriptions.py` imports `get_db` from `app.core.deps`

**Action Items:**
- [ ] Read `/backend/app/core/deps.py` to check current implementation
- [ ] Verify if `get_db` function exists or needs to be created
- [ ] Implement `get_db` as async generator for database sessions
- [ ] Ensure proper Prisma client integration
- [ ] Test import resolves successfully

**Expected Implementation:**
```python
# app/core/deps.py
from typing import AsyncGenerator
from prisma import Prisma

db = Prisma()

async def get_db() -> AsyncGenerator[Prisma, None]:
    """Dependency for getting database session."""
    await db.connect()
    try:
        yield db
    finally:
        await db.disconnect()
```

---

### 2. Review and Fix All Import Errors
**Priority:** HIGH
**Status:** PENDING

**Known Missing Modules:**
- [x] `app.schemas.user` - FIXED (created user.py)
- [ ] `app.core.deps.get_db` - CURRENT BLOCKER
- [ ] Other potential missing imports (TBD)

**Action Items:**
- [ ] Attempt server startup after fixing `get_db`
- [ ] Document any new import errors that appear
- [ ] Systematically create missing modules
- [ ] Verify all imports resolve correctly

---

### 3. Start PostgreSQL Database
**Priority:** HIGH
**Status:** NOT STARTED

**Current State:**
- Database URL configured: `postgresql://user:password@localhost:5432/revrx_db`
- PostgreSQL service not running
- Database schema not initialized

**Action Items:**
- [ ] Verify PostgreSQL is installed
- [ ] Start PostgreSQL service
- [ ] Create `revrx_db` database
- [ ] Verify connection with DATABASE_URL

**Commands:**
```bash
# Check if PostgreSQL is installed
psql --version

# Start PostgreSQL service (macOS)
brew services start postgresql

# Create database
createdb revrx_db

# Test connection
psql postgresql://user:password@localhost:5432/revrx_db
```

---

### 4. Run Prisma Migrations
**Priority:** HIGH
**Status:** BLOCKED (requires database running)

**Prerequisites:**
- PostgreSQL running
- Database created
- Prisma client generated ✅ (COMPLETED)

**Action Items:**
- [ ] Review existing migrations in `/backend/prisma/migrations/`
- [ ] Run `prisma db push` to sync schema to database
- [ ] Verify all tables created successfully
- [ ] Run seed script if needed

**Commands:**
```bash
cd backend
prisma db push --schema=./prisma/schema.prisma
prisma db seed  # if seed script exists
```

---

### 5. Fix Backend Server Configuration
**Priority:** MEDIUM
**Status:** IN PROGRESS

**Current State:**
- Server process running (ID: f81ada)
- Crashes on startup due to import errors
- Using uvicorn with --reload flag
- Environment variables loaded successfully

**Action Items:**
- [ ] Verify all environment variables in `.env` are valid
- [ ] Check CORS configuration matches frontend URL
- [ ] Ensure encryption key is properly base64 encoded ✅ (COMPLETED)
- [ ] Test server starts without errors

---

### 6. Test Registration Endpoint
**Priority:** HIGH
**Status:** BLOCKED (requires working server)

**Prerequisites:**
- Backend server running without errors
- Database initialized with schema
- All dependencies resolved

**Action Items:**
- [ ] Verify `/api/auth/register` endpoint is accessible
- [ ] Test registration with valid email/password
- [ ] Verify user created in database
- [ ] Check email verification flow
- [ ] Test error handling (duplicate email, weak password)

**Test Payload:**
```json
POST http://localhost:8000/api/auth/register
{
  "email": "test@example.com",
  "password": "SecurePass123!"
}
```

---

### 7. Verify Frontend-Backend Integration
**Priority:** MEDIUM
**Status:** BLOCKED (requires working registration)

**Current State:**
- Frontend configured to use `http://localhost:8000/api`
- Registration form ready on `/register` page
- API client configured with axios

**Action Items:**
- [ ] Test registration from frontend form
- [ ] Verify CORS allows frontend requests
- [ ] Check JWT token storage in localStorage
- [ ] Test redirect to `/verify-email` on success
- [ ] Verify error messages display correctly

---

## Completed Tasks

- [x] Create `.env` file with proper configuration
- [x] Install all Python dependencies
- [x] Fix `resend` version to 2.5.1
- [x] Fix `redis` version to 5.2.1
- [x] Install `pydantic[email]` for email validation
- [x] Install `libmagic` via homebrew
- [x] Create `app/schemas/user.py` module
- [x] Fix PBKDF2 import to PBKDF2HMAC
- [x] Generate proper base64 encryption key
- [x] Generate Prisma client successfully
- [x] Initialize encryption service
- [x] Initialize report generator

---

## Dependency Chain

```
1. Fix get_db import
   ↓
2. Resolve remaining import errors
   ↓
3. Start PostgreSQL database
   ↓
4. Run Prisma migrations
   ↓
5. Start backend server successfully
   ↓
6. Test registration endpoint
   ↓
7. Verify frontend integration
```

---

## Environment Configuration

### Required Services
- [x] Python 3.10
- [ ] PostgreSQL 14+
- [ ] Redis (for Celery background tasks)

### Environment Variables Status
- [x] DATABASE_URL configured
- [x] JWT secrets configured
- [x] CORS origins configured
- [x] PHI encryption key configured (base64)
- [ ] AWS credentials (optional for local dev)
- [ ] OpenAI API key (optional for local dev)
- [ ] Stripe keys (optional for local dev)
- [ ] Resend API key (optional for local dev)

---

## Known Issues

### Issue 1: Missing get_db Function
**Status:** ACTIVE BLOCKER
**File:** `app/core/deps.py`
**Impact:** Server cannot start
**Next Action:** Implement get_db function

### Issue 2: Database Not Running
**Status:** KNOWN ISSUE
**Impact:** Will block after fixing imports
**Next Action:** Start PostgreSQL service

### Issue 3: Schema Not Initialized
**Status:** KNOWN ISSUE
**Impact:** Will block registration even if server starts
**Next Action:** Run Prisma migrations

---

## Success Criteria

Backend is considered fully functional when:
- [ ] Server starts without errors
- [ ] All imports resolve successfully
- [ ] Database connection established
- [ ] Registration endpoint responds correctly
- [ ] Users can register from frontend
- [ ] Email verification flow works
- [ ] JWT tokens generated correctly
- [ ] Protected endpoints require authentication

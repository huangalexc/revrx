# Authentication & Authorization System

## Overview

The Post-Facto Coding Review API implements a comprehensive authentication and authorization system with:

- **User Registration** with email verification
- **JWT-based Authentication** with access and refresh tokens
- **Password Reset Flow** with secure tokens
- **Role-Based Access Control** (RBAC) with ADMIN and MEMBER roles
- **Resource Ownership Validation**
- **Subscription Status Verification**

## Architecture

### Security Components

#### 1. Password Hashing (`app/core/security.py`)
- Uses bcrypt with automatic salt generation
- Password strength validation (uppercase, lowercase, digits)
- Secure verification without timing attacks

#### 2. JWT Token Management
- **Access Tokens**: Short-lived (30 minutes default)
- **Refresh Tokens**: Long-lived (7 days default)
- Algorithm: HS256 (configurable)
- Token payload includes: user ID, email, role, expiration

#### 3. Token Generator
- Cryptographically secure random tokens
- Email verification tokens (32 bytes)
- Password reset tokens (32 bytes)

### Dependencies (`app/core/deps.py`)

FastAPI dependency injection for authentication:

```python
from app.core.deps import (
    get_current_user,           # Requires valid JWT, verified email
    get_current_active_user,    # Requires active subscription
    get_current_admin_user,     # Requires ADMIN role
    verify_resource_ownership,  # Checks user owns resource
    optional_auth,              # Optional authentication
)
```

## API Endpoints

### Public Endpoints (No Authentication)

#### POST /api/v1/auth/register
Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "confirm_password": "SecurePass123"
}
```

**Response:**
```json
{
  "message": "Registration successful. Please check your email to verify your account.",
  "user_id": "uuid",
  "email": "user@example.com"
}
```

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit

---

#### POST /api/v1/auth/verify-email
Verify email address using token from email.

**Request:**
```json
{
  "token": "verification_token_from_email"
}
```

**Response:**
```json
{
  "message": "Email verified successfully. Your 7-day trial has started!",
  "email": "user@example.com"
}
```

**Side Effects:**
- Sets `emailVerified` to true
- Sets `subscriptionStatus` to "TRIAL"
- Sets `trialEndDate` to 7 days from now
- Sends welcome email

---

#### POST /api/v1/auth/resend-verification
Resend verification email.

**Request:**
```json
{
  "email": "user@example.com"
}
```

---

#### POST /api/v1/auth/login
Authenticate and receive JWT tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

**Response:**
```json
{
  "message": "Login successful",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "role": "MEMBER",
    "email_verified": true,
    "profile_complete": false,
    "subscription_status": "TRIAL",
    "trial_end_date": "2024-04-22T10:30:00Z",
    "created_at": "2024-04-15T10:30:00Z",
    "last_login_at": "2024-04-15T10:30:00Z"
  },
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

---

#### POST /api/v1/auth/refresh
Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

#### POST /api/v1/auth/forgot-password
Request password reset email.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "If an account with this email exists, a password reset email has been sent."
}
```

---

#### POST /api/v1/auth/reset-password
Reset password using token from email.

**Request:**
```json
{
  "token": "reset_token_from_email",
  "new_password": "NewSecurePass123",
  "confirm_password": "NewSecurePass123"
}
```

**Response:**
```json
{
  "message": "Password reset successful. You can now log in with your new password."
}
```

---

### Protected Endpoints (Require Authentication)

**Authorization Header:**
```
Authorization: Bearer <access_token>
```

#### GET /api/v1/auth/me
Get current user profile.

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "role": "MEMBER",
  "email_verified": true,
  "profile_complete": false,
  "subscription_status": "TRIAL",
  "trial_end_date": "2024-04-22T10:30:00Z",
  "created_at": "2024-04-15T10:30:00Z",
  "last_login_at": "2024-04-15T10:30:00Z"
}
```

---

#### PUT /api/v1/auth/me
Update user profile (currently supports password change).

**Request:**
```json
{
  "current_password": "OldSecurePass123",
  "new_password": "NewSecurePass123",
  "confirm_password": "NewSecurePass123"
}
```

---

#### POST /api/v1/auth/logout
Logout user (for logging purposes).

**Response:**
```json
{
  "message": "Logout successful. Please remove your tokens from client storage."
}
```

**Note:** JWT tokens are stateless. Logout is handled client-side by removing tokens.

---

### User Management Endpoints

#### GET /api/v1/users/me
Get current user profile (alias for `/auth/me`).

#### GET /api/v1/users/me/subscription-status
Get detailed subscription status.

**Response:**
```json
{
  "subscriptionStatus": "TRIAL",
  "role": "MEMBER",
  "hasActiveAccess": true,
  "trialInfo": {
    "trialEndDate": "2024-04-22T10:30:00Z",
    "daysRemaining": 7,
    "isExpired": false
  }
}
```

---

### Admin-Only Endpoints

Require ADMIN role (`get_current_admin_user` dependency).

#### GET /api/v1/users
List all users with pagination and filters.

**Query Parameters:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Number of records to return (default: 50, max: 100)
- `role`: Filter by role (ADMIN, MEMBER)
- `subscriptionStatus`: Filter by subscription status

**Response:**
```json
[
  {
    "id": "uuid",
    "email": "user@example.com",
    "role": "MEMBER",
    "email_verified": true,
    "subscription_status": "TRIAL",
    ...
  }
]
```

---

#### GET /api/v1/users/{user_id}
Get user by ID.

---

#### PUT /api/v1/users/{user_id}/suspend
Suspend a user account.

**Response:**
```json
{
  "id": "uuid",
  "subscription_status": "SUSPENDED",
  ...
}
```

---

#### PUT /api/v1/users/{user_id}/activate
Activate a suspended user account.

---

#### PUT /api/v1/users/{user_id}/grant-free-access
Grant free lifetime access (sets status to ACTIVE without payment).

---

#### DELETE /api/v1/users/{user_id}
Permanently delete a user account.

**Note:** Cannot delete your own account.

---

## User Roles

### MEMBER (Default)
- Access to own encounters and reports
- Upload clinical notes
- Generate reports
- Manage own profile

### ADMIN
- All MEMBER permissions
- View all users
- Suspend/activate users
- Grant free access
- Delete users
- View audit logs
- Access admin dashboard

## Subscription Status

| Status | Description | Access |
|--------|-------------|--------|
| INACTIVE | Email not verified or trial/subscription expired | No API access |
| TRIAL | 7-day free trial active | Full API access |
| ACTIVE | Paid subscription active | Full API access |
| CANCELLED | Subscription cancelled (access until period end) | Full API access |
| EXPIRED | Trial or subscription expired | No API access |
| SUSPENDED | Account suspended by admin | No API access |

## Email Verification Flow

1. User registers with email and password
2. System generates verification token (24-hour expiration)
3. Verification email sent with link: `http://frontend.com/auth/verify-email?token=xxx`
4. User clicks link, frontend calls `/api/v1/auth/verify-email`
5. Backend verifies token, activates account, starts trial
6. Welcome email sent

## Password Reset Flow

1. User requests password reset
2. System generates reset token (1-hour expiration)
3. Reset email sent with link: `http://frontend.com/auth/reset-password?token=xxx`
4. User clicks link, enters new password
5. Frontend calls `/api/v1/auth/reset-password` with token and new password
6. Backend verifies token, updates password

## JWT Token Flow

### Login Flow
```
1. User sends email + password → POST /auth/login
2. Backend verifies credentials
3. Backend generates access_token (30min) + refresh_token (7days)
4. Frontend stores tokens (localStorage/sessionStorage)
```

### Authenticated Request Flow
```
1. Frontend sends request with Authorization: Bearer <access_token>
2. Backend validates token (signature, expiration, user exists)
3. Backend checks email verification
4. Backend checks subscription status (if required)
5. Request processed with user context
```

### Token Refresh Flow
```
1. Access token expires
2. Frontend detects 401 error
3. Frontend calls POST /auth/refresh with refresh_token
4. Backend validates refresh_token
5. Backend returns new access_token
6. Frontend retries original request
```

## Audit Logging

All authentication events are logged to the `audit_logs` table:

- `USER_REGISTERED`
- `EMAIL_VERIFIED`
- `LOGIN_SUCCESS`
- `LOGIN_FAILED`
- `PASSWORD_RESET_REQUESTED`
- `PASSWORD_RESET_COMPLETED`
- `PROFILE_UPDATED`
- `LOGOUT`
- `USER_SUSPENDED`
- `USER_ACTIVATED`
- `FREE_ACCESS_GRANTED`
- `USER_DELETED`

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Passwords do not match"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid email or password"
}
```

### 403 Forbidden
```json
{
  "detail": "Please verify your email before logging in"
}
```

### 402 Payment Required
```json
{
  "detail": "Active subscription required. Your subscription has expired or is inactive."
}
```

### 404 Not Found
```json
{
  "detail": "User not found"
}
```

## Security Best Practices

### Password Security
- Bcrypt hashing with automatic salt
- Minimum password requirements enforced
- Confirmation password required on registration and reset

### Token Security
- Short-lived access tokens (30 minutes)
- Refresh tokens for seamless UX
- Secure random token generation for email/reset
- Token expiration enforced

### Email Verification
- Required before login
- Trial starts only after verification
- Prevents spam registrations

### Audit Trail
- All authentication events logged
- User ID, action, timestamp, metadata
- IP address tracking (when implemented in middleware)

### Admin Protection
- Role-based access control
- Cannot delete own admin account
- All admin actions logged

## Environment Variables

Required in `.env`:

```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here-minimum-32-characters
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Email Service (Resend)
RESEND_API_KEY=your-resend-api-key
FROM_EMAIL=noreply@yourdomain.com

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

## Frontend Integration Example

### Login
```javascript
async function login(email, password) {
  const response = await fetch('/api/v1/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });

  const data = await response.json();

  if (response.ok) {
    localStorage.setItem('access_token', data.tokens.access_token);
    localStorage.setItem('refresh_token', data.tokens.refresh_token);
    return data.user;
  } else {
    throw new Error(data.detail);
  }
}
```

### Authenticated Request
```javascript
async function fetchProtectedResource() {
  const token = localStorage.getItem('access_token');

  const response = await fetch('/api/v1/encounters', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  if (response.status === 401) {
    // Try to refresh token
    await refreshToken();
    // Retry request
    return fetchProtectedResource();
  }

  return response.json();
}
```

### Refresh Token
```javascript
async function refreshToken() {
  const refresh_token = localStorage.getItem('refresh_token');

  const response = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token })
  });

  if (response.ok) {
    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
  } else {
    // Refresh token invalid - redirect to login
    localStorage.clear();
    window.location.href = '/login';
  }
}
```

## Testing

See `backend/tests/test_auth.py` for comprehensive test suite covering:
- User registration
- Email verification
- Login/logout
- Password reset
- Token refresh
- Role-based access control
- Resource ownership validation

## Next Steps

Track 2 (Authentication & Authorization) is now complete. Next tracks:

- **Track 3**: File Upload & Validation
- **Track 4**: HIPAA Compliance & PHI Handling
- **Track 7**: Payment & Subscription (Stripe integration)

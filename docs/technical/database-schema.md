# Database Schema Documentation

## Overview

This document describes the PostgreSQL database schema for the Post-Facto Coding Review MVP. The schema is designed to be HIPAA-compliant with encryption at rest and supports role-based access control, audit logging, and subscription management.

## Entity Relationship Diagram

```
User (1) ──── (M) Encounter
User (1) ──── (1) Subscription
User (1) ──── (M) AuditLog
Encounter (1) ──── (M) UploadedFile
Encounter (1) ──── (1) Report
User (1) ──── (M) Token
```

## Tables

### User

Stores user account information and authentication credentials.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique user identifier |
| email | VARCHAR(255) | UNIQUE, NOT NULL | User email address |
| password_hash | VARCHAR(255) | NOT NULL | Bcrypt hashed password |
| full_name | VARCHAR(255) | NOT NULL | User's full name |
| organization | VARCHAR(255) | NULL | Organization name |
| role | ENUM('USER', 'ADMIN') | NOT NULL, DEFAULT 'USER' | User role for RBAC |
| email_verified | BOOLEAN | NOT NULL, DEFAULT FALSE | Email verification status |
| trial_end_date | TIMESTAMP | NULL | End date of free trial |
| subscription_status | ENUM('trial', 'active', 'cancelled', 'expired') | NOT NULL, DEFAULT 'trial' | Current subscription status |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Account creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `idx_user_email` on `email` (unique)
- `idx_user_subscription_status` on `subscription_status`

**Security Notes:**
- Passwords must never be stored in plain text
- Use bcrypt with salt rounds ≥ 12
- Email must be validated before account activation

---

### Encounter

Represents a clinical encounter uploaded for analysis.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique encounter identifier |
| user_id | UUID | FOREIGN KEY → User.id, NOT NULL | Owner of the encounter |
| upload_date | TIMESTAMP | NOT NULL, DEFAULT NOW() | Upload timestamp |
| status | ENUM('pending', 'processing', 'complete', 'failed') | NOT NULL, DEFAULT 'pending' | Processing status |
| processing_time | DECIMAL(10,2) | NULL | Processing time in seconds |
| patient_age | INTEGER | NULL | Patient age (PHI - encrypted) |
| patient_sex | CHAR(1) | NULL | Patient sex (M/F/O) |
| visit_date | DATE | NULL | Date of clinical visit |
| encounter_type | VARCHAR(100) | NULL | Type of encounter |
| error_message | TEXT | NULL | Error details if status = 'failed' |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Record creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes:**
- `idx_encounter_user_id` on `user_id`
- `idx_encounter_status` on `status`
- `idx_encounter_upload_date` on `upload_date` (for time-based queries)

**Constraints:**
- `fk_encounter_user` FOREIGN KEY (user_id) REFERENCES User(id) ON DELETE CASCADE
- `chk_patient_age` CHECK (patient_age BETWEEN 0 AND 150)
- `chk_patient_sex` CHECK (patient_sex IN ('M', 'F', 'O'))

**HIPAA Note:**
- Patient age/sex should be minimally identifying
- Full PHI is stored separately in encrypted form

---

### UploadedFile

Stores metadata for uploaded clinical notes and billing code files.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique file identifier |
| encounter_id | UUID | FOREIGN KEY → Encounter.id, NOT NULL | Associated encounter |
| file_type | ENUM('note', 'billing_codes') | NOT NULL | Type of uploaded file |
| file_format | VARCHAR(10) | NOT NULL | File format (txt, pdf, docx, csv, json) |
| file_path | VARCHAR(500) | NOT NULL | S3 path to encrypted file |
| file_size | INTEGER | NOT NULL | File size in bytes |
| original_filename | VARCHAR(255) | NOT NULL | Original filename |
| checksum | VARCHAR(64) | NOT NULL | SHA-256 checksum for integrity |
| uploaded_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Upload timestamp |

**Indexes:**
- `idx_uploaded_file_encounter_id` on `encounter_id`
- `idx_uploaded_file_type` on `file_type`

**Constraints:**
- `fk_uploaded_file_encounter` FOREIGN KEY (encounter_id) REFERENCES Encounter(id) ON DELETE CASCADE
- `chk_file_size` CHECK (file_size <= 5242880) -- 5MB max

**Security Notes:**
- Files stored in encrypted S3 bucket
- Access via presigned URLs only
- Checksums verified on upload and retrieval

---

### Report

Stores analysis results and suggested billing codes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique report identifier |
| encounter_id | UUID | FOREIGN KEY → Encounter.id, UNIQUE, NOT NULL | Associated encounter |
| billed_codes | JSONB | NOT NULL | Original billed CPT/ICD codes |
| suggested_codes | JSONB | NOT NULL | AI-suggested additional codes |
| total_incremental_revenue | DECIMAL(10,2) | NOT NULL | Estimated revenue opportunity |
| de_identified_text | TEXT | NULL | PHI-stripped clinical text |
| phi_mapping | JSONB | NULL | Encrypted PHI token mapping |
| generated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Report generation timestamp |

**Indexes:**
- `idx_report_encounter_id` on `encounter_id` (unique)
- `idx_report_generated_at` on `generated_at`

**Constraints:**
- `fk_report_encounter` FOREIGN KEY (encounter_id) REFERENCES Encounter(id) ON DELETE CASCADE

**JSONB Schema for `billed_codes`:**
```json
[
  {
    "code": "99214",
    "type": "CPT",
    "description": "Office visit, established patient"
  }
]
```

**JSONB Schema for `suggested_codes`:**
```json
[
  {
    "code": {
      "code": "99215",
      "type": "CPT",
      "description": "Office visit, high complexity"
    },
    "justification": "Documentation supports high complexity evaluation",
    "supportingText": [
      "Comprehensive history taken",
      "Detailed examination performed"
    ],
    "confidence": 0.92,
    "estimatedRevenue": 75.00
  }
]
```

**HIPAA Note:**
- `phi_mapping` contains encrypted reversible de-identification data
- Must be encrypted at rest using AES-256
- Access strictly audited

---

### Subscription

Manages user payment and subscription information.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique subscription identifier |
| user_id | UUID | FOREIGN KEY → User.id, UNIQUE, NOT NULL | Subscriber user |
| stripe_customer_id | VARCHAR(255) | NULL | Stripe customer ID |
| stripe_subscription_id | VARCHAR(255) | NULL | Stripe subscription ID |
| status | ENUM('trial', 'active', 'cancelled', 'expired') | NOT NULL | Subscription status |
| billing_period | ENUM('monthly', 'annual') | NOT NULL, DEFAULT 'monthly' | Billing frequency |
| amount | DECIMAL(10,2) | NOT NULL | Subscription amount |
| currency | VARCHAR(3) | NOT NULL, DEFAULT 'USD' | Currency code |
| trial_start_date | TIMESTAMP | NULL | Trial start date |
| trial_end_date | TIMESTAMP | NULL | Trial end date |
| next_billing_date | TIMESTAMP | NULL | Next billing date |
| cancelled_at | TIMESTAMP | NULL | Cancellation timestamp |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Subscription creation |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update |

**Indexes:**
- `idx_subscription_user_id` on `user_id` (unique)
- `idx_subscription_stripe_customer` on `stripe_customer_id`
- `idx_subscription_status` on `status`

**Constraints:**
- `fk_subscription_user` FOREIGN KEY (user_id) REFERENCES User(id) ON DELETE CASCADE

**PCI Compliance Note:**
- Payment card data never stored in database
- All payment processing via Stripe
- Only store Stripe tokens/IDs

---

### AuditLog

Comprehensive audit trail for HIPAA compliance.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique log entry identifier |
| user_id | UUID | FOREIGN KEY → User.id, NULL | User who performed action |
| action | VARCHAR(100) | NOT NULL | Action type (login, upload, view, etc.) |
| resource_type | VARCHAR(50) | NULL | Type of resource accessed |
| resource_id | UUID | NULL | ID of resource accessed |
| ip_address | VARCHAR(45) | NOT NULL | Client IP address |
| user_agent | TEXT | NULL | Client user agent |
| timestamp | TIMESTAMP | NOT NULL, DEFAULT NOW() | Action timestamp |
| metadata | JSONB | NULL | Additional context data |
| success | BOOLEAN | NOT NULL, DEFAULT TRUE | Whether action succeeded |

**Indexes:**
- `idx_audit_log_user_id` on `user_id`
- `idx_audit_log_action` on `action`
- `idx_audit_log_timestamp` on `timestamp` (for time-range queries)
- `idx_audit_log_resource` on `(resource_type, resource_id)`

**Constraints:**
- `fk_audit_log_user` FOREIGN KEY (user_id) REFERENCES User(id) ON DELETE SET NULL

**Common Actions:**
- `auth.login`
- `auth.logout`
- `auth.register`
- `encounter.upload_note`
- `encounter.upload_codes`
- `report.view`
- `report.download`
- `subscription.create`
- `subscription.cancel`
- `phi.access`

**Retention Policy:**
- Audit logs must be retained for minimum 6 years (HIPAA requirement)
- Implement log rotation and archival strategy

---

### Token

Manages email verification and password reset tokens.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique token identifier |
| user_id | UUID | FOREIGN KEY → User.id, NOT NULL | Associated user |
| token | VARCHAR(255) | UNIQUE, NOT NULL | Secure random token |
| type | ENUM('email_verification', 'password_reset') | NOT NULL | Token purpose |
| expires_at | TIMESTAMP | NOT NULL | Token expiration |
| used | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether token was used |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW() | Token creation |

**Indexes:**
- `idx_token_token` on `token` (unique)
- `idx_token_user_id` on `user_id`
- `idx_token_expires_at` on `expires_at` (for cleanup)

**Constraints:**
- `fk_token_user` FOREIGN KEY (user_id) REFERENCES User(id) ON DELETE CASCADE

**Security Notes:**
- Tokens should be cryptographically random (at least 32 bytes)
- Tokens expire after:
  - Email verification: 24 hours
  - Password reset: 1 hour
- Single-use only (mark as `used=true` after consumption)
- Implement automatic cleanup of expired tokens

---

## Data Encryption

### At-Rest Encryption
- PostgreSQL transparent data encryption (TDE) enabled
- Sensitive columns additionally encrypted:
  - `Report.phi_mapping` (AES-256)
  - `Encounter.patient_age` (if stored)
- Encryption keys managed via AWS KMS or similar HSM

### In-Transit Encryption
- All database connections via TLS 1.3
- Certificate validation enforced
- No plaintext connections allowed

---

## Access Control

### Role-Based Access (RBAC)

**USER Role:**
- Read/write own encounters, reports, subscriptions
- No access to other users' data
- No admin endpoints

**ADMIN Role:**
- Full read access to all data
- Access to audit logs
- User management capabilities
- No ability to view PHI without audit trail

### Row-Level Security (RLS)

Implement PostgreSQL RLS policies:

```sql
-- Example: Users can only access their own encounters
CREATE POLICY encounter_user_policy ON Encounter
  FOR ALL
  TO authenticated_user
  USING (user_id = current_user_id());
```

---

## Backup and Recovery

### Backup Strategy
- Full daily backups with 30-day retention
- Point-in-time recovery (PITR) enabled
- Encrypted backups stored in geographically separate region
- Quarterly backup restoration tests

### Disaster Recovery
- RTO (Recovery Time Objective): 4 hours
- RPO (Recovery Point Objective): 1 hour
- Automated failover to standby replica
- Documented recovery procedures

---

## Performance Considerations

### Indexing Strategy
- All foreign keys indexed
- Composite indexes for common query patterns
- Regular ANALYZE/VACUUM maintenance

### Query Optimization
- Use prepared statements
- Implement connection pooling (pgBouncer)
- Monitor slow queries (log queries > 1s)
- Implement read replicas for reporting queries

### Scalability
- Horizontal partitioning for AuditLog by timestamp
- Archive old encounters (>1 year) to cold storage
- Use JSONB indexes for frequently queried JSON fields

---

## Migration Strategy

### Schema Versioning
- Use Prisma migrations or similar tool
- Version control all schema changes
- Test migrations on staging before production

### Zero-Downtime Migrations
- Use backward-compatible changes
- Blue-green deployment strategy
- Implement database migration rollback procedures

---

## Compliance Checklist

- [x] PHI encryption at rest (AES-256)
- [x] TLS 1.3 for all connections
- [x] Comprehensive audit logging
- [x] Role-based access control
- [x] 6-year audit log retention
- [x] Automated backup with encryption
- [x] Data deletion/retention policies
- [x] Access logging for PHI

---

## Appendix: SQL Schema Example

```sql
-- User table
CREATE TABLE "User" (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(255) NOT NULL,
  organization VARCHAR(255),
  role VARCHAR(20) NOT NULL DEFAULT 'USER' CHECK (role IN ('USER', 'ADMIN')),
  email_verified BOOLEAN NOT NULL DEFAULT FALSE,
  trial_end_date TIMESTAMP,
  subscription_status VARCHAR(20) NOT NULL DEFAULT 'trial'
    CHECK (subscription_status IN ('trial', 'active', 'cancelled', 'expired')),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_email ON "User"(email);
CREATE INDEX idx_user_subscription_status ON "User"(subscription_status);

-- Encounter table
CREATE TABLE "Encounter" (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES "User"(id) ON DELETE CASCADE,
  upload_date TIMESTAMP NOT NULL DEFAULT NOW(),
  status VARCHAR(20) NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'processing', 'complete', 'failed')),
  processing_time DECIMAL(10,2),
  patient_age INTEGER CHECK (patient_age BETWEEN 0 AND 150),
  patient_sex CHAR(1) CHECK (patient_sex IN ('M', 'F', 'O')),
  visit_date DATE,
  encounter_type VARCHAR(100),
  error_message TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_encounter_user_id ON "Encounter"(user_id);
CREATE INDEX idx_encounter_status ON "Encounter"(status);
CREATE INDEX idx_encounter_upload_date ON "Encounter"(upload_date);

-- Additional tables follow similar pattern...
```

---

## Document Information

**Version:** 1.0
**Last Updated:** 2025-09-30
**Author:** RevRX Engineering Team
**Review Cycle:** Quarterly

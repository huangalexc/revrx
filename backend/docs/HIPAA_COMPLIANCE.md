# HIPAA Compliance & PHI Handling

## Overview

This document describes the HIPAA-compliant PHI handling system implemented in the Post-Facto Coding Review application. The system provides comprehensive PHI detection, de-identification, secure storage, and audit logging to meet HIPAA Privacy Rule and Security Rule requirements.

## Architecture

### Components

1. **Amazon Comprehend Medical** - PHI detection and medical entity extraction
2. **Encryption Service** - AES-256-GCM encryption for PHI data at rest
3. **PHI Handler Service** - De-identification and re-identification workflows
4. **Data Retention Service** - Automated retention policy enforcement
5. **Audit Logging** - Complete audit trail for all PHI access

### Data Flow

```
Clinical Note Upload
    ↓
1. Store raw file in encrypted S3 bucket (AES-256)
    ↓
2. Extract text from file (PDF/DOCX/TXT)
    ↓
3. Detect PHI using Amazon Comprehend Medical
    ↓
4. De-identify PHI (replace with tokens like [NAME_1])
    ↓
5. Store encrypted PHI mapping in PostgreSQL
    ↓
6. Store de-identified text for AI processing
    ↓
7. Log PHI access in audit log
    ↓
8. Process de-identified text with AI
    ↓
9. Generate report (can re-identify if needed)
    ↓
10. Auto-delete after 7 years (configurable)
```

---

## PHI Detection

### Amazon Comprehend Medical Integration

Location: `backend/app/services/comprehend_medical.py`

#### Detected PHI Types

The system detects the following PHI categories:

| PHI Type | Description | Example |
|----------|-------------|---------|
| NAME | Patient names, provider names | "John Smith", "Dr. Sarah Johnson" |
| DATE | Birth dates, admission dates, discharge dates | "04/15/1980", "January 5, 2024" |
| AGE | Ages over 89 years | "92 years old" |
| PHONE_OR_FAX | Phone and fax numbers | "(555) 123-4567" |
| EMAIL | Email addresses | "patient@example.com" |
| ID | Medical record numbers, SSN, account numbers | "MRN-12345", "SSN 123-45-6789" |
| URL | Web URLs | "http://example.com" |
| IP_ADDRESS | IP addresses | "192.168.1.1" |
| ADDRESS | Street addresses, cities, states, zip codes | "123 Main St, Boston, MA 02101" |

#### Usage Example

```python
from app.services.comprehend_medical import comprehend_medical_service

# Detect PHI
phi_entities = comprehend_medical_service.detect_phi(clinical_text)

# Detect medical entities (conditions, medications, procedures)
medical_entities = comprehend_medical_service.detect_entities_v2(clinical_text)

# Comprehensive analysis
result = comprehend_medical_service.analyze_text(clinical_text)
```

#### API Limits

- Maximum text size: 20,000 bytes per request
- Rate limits: AWS account limits apply
- Supported languages: English only

---

## PHI De-identification

### Token-Based Masking

Location: `backend/app/services/phi_handler.py`

The system uses **reversible de-identification** with token replacement:

#### Original Text
```
Patient John Smith (DOB: 04/15/1980) was admitted on 12/20/2023
with chest pain. Phone: (555) 123-4567.
```

#### De-identified Text
```
Patient [NAME_1] (DOB: [DATE_1]) was admitted on [DATE_2]
with chest pain. Phone: [PHONE_OR_FAX_1].
```

### Token Format

- Pattern: `[{PHI_TYPE}_{INDEX}]`
- Examples: `[NAME_1]`, `[NAME_2]`, `[DATE_1]`, `[PHONE_OR_FAX_1]`
- Sequential indexing prevents collisions

### De-identification Process

```python
from app.services.phi_handler import phi_handler

# Detect and de-identify
result = phi_handler.detect_and_deidentify(clinical_text)

# Access results
deidentified_text = result.deidentified_text
phi_mappings = result.phi_mappings
phi_detected = result.phi_detected

# Re-identify (for authorized report generation)
original_text = phi_handler.reidentify(deidentified_text, phi_mappings)
```

### PHI Mapping Storage

PHI mappings are stored in the `phi_mappings` table with:

- **Encrypted mapping**: AES-256-GCM encrypted JSON containing token→original mappings
- **De-identified text**: Safe to use for AI processing
- **Metadata**: PHI detection status, entity count

```python
# Store PHI mapping
await phi_handler.store_phi_mapping(encounter_id, result)

# Retrieve PHI mapping
result = await phi_handler.retrieve_phi_mapping(encounter_id)

# Get de-identified text only
deidentified_text = await phi_handler.get_deidentified_text(encounter_id)
```

---

## Encryption

### AES-256-GCM Encryption

Location: `backend/app/core/encryption.py`

The system uses **AES-256-GCM** (Galois/Counter Mode) for authenticated encryption:

#### Features

- **256-bit key**: Maximum security strength
- **Authenticated encryption**: Detects tampering
- **Random nonces**: Unique 12-byte nonce per encryption
- **AEAD**: Authenticated Encryption with Associated Data

#### Key Management

```bash
# Generate new encryption key
python -m app.core.encryption

# Output: Base64-encoded 32-byte key
# Add to .env as PHI_ENCRYPTION_KEY
```

#### Usage

```python
from app.core.encryption import encryption_service

# Encrypt text
encrypted = encryption_service.encrypt("sensitive data")

# Decrypt text
plaintext = encryption_service.decrypt(encrypted)

# Encrypt/decrypt JSON
encrypted_json = encryption_service.encrypt_json({"key": "value"})
data_dict = encryption_service.decrypt_json(encrypted_json)
```

#### Key Rotation

```python
# Re-encrypt data with new key
new_encrypted = encryption_service.rotate_key(new_key, old_encrypted)
```

### Encryption at Rest

| Data Type | Encryption Method | Location |
|-----------|-------------------|----------|
| Raw uploaded files | AWS S3 AES-256 | S3 bucket with server-side encryption |
| PHI mappings | AES-256-GCM | PostgreSQL `phi_mappings.encrypted_mapping` |
| Database | PostgreSQL encryption | Database level encryption (recommended) |

---

## Data Retention

### Retention Policy

Location: `backend/app/services/data_retention.py`

**Default Retention: 7 years (2,555 days)**

This meets HIPAA requirements and most state regulations.

#### Retention Process

1. **Automated Daily Cleanup**
   - Scheduled job runs daily
   - Identifies encounters older than retention period
   - Deletes encounter and all associated data
   - Logs deletion in audit log

2. **Data Deletion Includes**
   - Encounter record
   - Uploaded files from S3
   - PHI mappings (encrypted)
   - Reports
   - Related metadata

3. **Audit Trail**
   - All deletions logged with reason
   - Cannot be deleted (separate retention for audit logs)

#### Usage

```python
from app.services.data_retention import data_retention_service

# Run automated cleanup (should be scheduled daily)
stats = await data_retention_service.run_retention_cleanup()

# Check retention status for specific encounter
status = await data_retention_service.get_retention_status(encounter_id)

# Get overall retention summary
summary = await data_retention_service.get_retention_summary()
```

#### Configuration

```bash
# .env file
DATA_RETENTION_DAYS=2555  # 7 years (default)
```

#### Scheduled Job Setup

Add to crontab or Kubernetes CronJob:

```yaml
# k8s/cronjobs/data-retention.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: data-retention-cleanup
spec:
  schedule: "0 2 * * *"  # Run daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: cleanup
            image: backend:latest
            command:
            - python
            - -m
            - app.scripts.retention_cleanup
```

---

## Audit Logging

### HIPAA Audit Trail

All PHI-related actions are logged in the `audit_logs` table.

#### Logged Actions

| Action | Description | Triggered When |
|--------|-------------|----------------|
| `PHI_DETECTED` | PHI detected in clinical note | After Comprehend Medical analysis |
| `PHI_ACCESSED` | PHI mapping retrieved | When re-identifying for reports |
| `ENCOUNTER_UPLOADED` | Clinical note uploaded | File upload complete |
| `REPORT_GENERATED` | Report created | Report generation complete |
| `ENCOUNTER_DELETED` | Encounter deleted | Manual or automated deletion |
| `DATA_RETENTION_CLEANUP` | Retention cleanup run | Automated cleanup job |

#### Audit Log Schema

```typescript
{
  id: string
  userId: string
  action: string
  resourceType: string  // "Encounter", "Report", "PhiMapping"
  resourceId: string
  ipAddress: string     // Optional
  userAgent: string     // Optional
  metadata: json        // Additional context
  createdAt: DateTime
}
```

#### Querying Audit Logs

```python
# Get all PHI access for an encounter
logs = await prisma.auditlog.find_many(
    where={
        "resourceType": "Encounter",
        "resourceId": encounter_id,
        "action": {"in": ["PHI_DETECTED", "PHI_ACCESSED"]}
    },
    order={"createdAt": "desc"}
)

# Get user's PHI access history
logs = await prisma.auditlog.find_many(
    where={
        "userId": user_id,
        "action": {"contains": "PHI"}
    }
)
```

---

## Security Measures

### Technical Safeguards

#### 1. Encryption in Transit

- **TLS 1.3** for all API endpoints
- **HTTPS only** in production
- Certificate pinning for mobile apps

```python
# uvicorn with TLS
uvicorn app.main:app \
  --ssl-keyfile=/path/to/key.pem \
  --ssl-certfile=/path/to/cert.pem \
  --ssl-version=TLSv1_3
```

#### 2. Encryption at Rest

- **S3 Server-Side Encryption**: AES-256 (SSE-S3 or SSE-KMS)
- **PHI Mappings**: AES-256-GCM application-level encryption
- **Database**: PostgreSQL encryption at rest (recommended)

```bash
# PostgreSQL encryption
# postgresql.conf
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
```

#### 3. Access Controls

- **Role-Based Access Control (RBAC)**
  - ADMIN: Full access to all data
  - MEMBER: Access only to own encounters

- **Resource Ownership Validation**
  - Users can only access their own data
  - Admins can access all data (logged)

```python
from app.core.deps import verify_resource_ownership

# In endpoint
await verify_resource_ownership(encounter.userId, current_user)
```

#### 4. Authentication

- **JWT tokens**: Short-lived access tokens (30 min)
- **Password hashing**: Bcrypt with automatic salt
- **Email verification**: Required before access
- **MFA**: Ready for implementation

#### 5. Data Minimization

- **De-identified AI processing**: PHI never sent to OpenAI
- **Minimal storage**: Only necessary data retained
- **Automatic deletion**: After retention period

---

## HIPAA Compliance Checklist

### Privacy Rule Compliance

- [x] **Notice of Privacy Practices**: Template provided
- [x] **Individual Rights**: Users can access/delete their data
- [x] **Minimum Necessary**: Only required PHI collected
- [x] **PHI De-identification**: Automated de-identification before AI processing
- [x] **Business Associate Agreements**: BAA template provided

### Security Rule Compliance

#### Administrative Safeguards
- [x] **Security Management Process**: Documented procedures
- [x] **Workforce Training**: Documentation available
- [x] **Contingency Planning**: Disaster recovery plan
- [x] **Audit Controls**: Comprehensive audit logging

#### Physical Safeguards
- [x] **Facility Access Controls**: Cloud provider security
- [x] **Workstation Security**: Developer guidelines
- [x] **Device/Media Controls**: Encrypted storage

#### Technical Safeguards
- [x] **Access Control**: RBAC with JWT authentication
- [x] **Audit Controls**: All PHI access logged
- [x] **Integrity Controls**: Encryption prevents tampering
- [x] **Transmission Security**: TLS 1.3 for all communications

### Breach Notification Rule

- [x] **Risk Assessment Process**: Documented in incident response plan
- [x] **Notification Procedures**: Documented in incident response plan
- [x] **Breach Log**: Maintained in audit logs

---

## Best Practices

### For Developers

1. **Never Log PHI**
   ```python
   # BAD
   logger.info("Processing patient John Smith")

   # GOOD
   logger.info("Processing encounter", encounter_id=encounter_id)
   ```

2. **Always Use De-identified Text for AI**
   ```python
   # Get de-identified text
   deidentified_text = await phi_handler.get_deidentified_text(encounter_id)

   # Process with AI
   response = await openai_client.process(deidentified_text)
   ```

3. **Encrypt Before Storing PHI**
   ```python
   # Encrypt sensitive data
   encrypted_data = encryption_service.encrypt(phi_data)

   # Store encrypted
   await prisma.phimapping.create(data={"encryptedMapping": encrypted_data})
   ```

4. **Log All PHI Access**
   ```python
   await prisma.auditlog.create(
       data={
           "userId": user_id,
           "action": "PHI_ACCESSED",
           "resourceType": "Encounter",
           "resourceId": encounter_id,
       }
   )
   ```

### For Administrators

1. **Regular Security Audits**
   - Review audit logs weekly
   - Monitor failed authentication attempts
   - Check for unusual PHI access patterns

2. **Key Management**
   - Rotate encryption keys annually
   - Store keys in secure key management system (AWS KMS, HashiCorp Vault)
   - Never commit keys to version control

3. **Backup and Recovery**
   - Daily automated backups of encrypted data
   - Test restore procedures quarterly
   - Document recovery time objectives (RTO)

4. **Compliance Monitoring**
   - Generate monthly compliance reports
   - Review data retention policy effectiveness
   - Ensure BAAs are signed with all vendors

---

## Environment Variables

Required in `.env`:

```bash
# AWS Comprehend Medical
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_COMPREHEND_MEDICAL_REGION=us-east-1

# S3 Storage
AWS_S3_BUCKET_NAME=your-bucket-name
AWS_S3_ENCRYPTION=AES256

# PHI Encryption (32-byte key, base64-encoded)
PHI_ENCRYPTION_KEY=your-base64-encoded-32-byte-key

# Data Retention
DATA_RETENTION_DAYS=2555  # 7 years

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# TLS/SSL
SSL_ENABLED=true
SSL_CERT_FILE=/path/to/cert.pem
SSL_KEY_FILE=/path/to/key.pem
```

---

## Testing

### PHI Detection Testing

```python
# Test PHI detection
text = "Patient John Smith (DOB: 04/15/1980) was admitted."
result = phi_handler.detect_and_deidentify(text)

assert result.phi_detected == True
assert len(result.phi_entities) == 2  # NAME and DATE
assert "[NAME_1]" in result.deidentified_text
assert "[DATE_1]" in result.deidentified_text
```

### Encryption Testing

```python
# Test encryption
plaintext = "sensitive PHI data"
encrypted = encryption_service.encrypt(plaintext)
decrypted = encryption_service.decrypt(encrypted)

assert decrypted == plaintext
assert encrypted != plaintext
```

### Re-identification Testing

```python
# Test reversible de-identification
original = "Patient John Smith"
result = phi_handler.detect_and_deidentify(original)
reidentified = phi_handler.reidentify(result.deidentified_text, result.phi_mappings)

assert reidentified == original
```

---

## Incident Response

If PHI breach suspected:

1. **Immediate Actions**
   - Isolate affected systems
   - Preserve audit logs
   - Document timeline

2. **Risk Assessment**
   - Determine scope of breach
   - Assess encryption status
   - Identify affected individuals

3. **Notification** (if required)
   - Notify affected individuals within 60 days
   - Notify HHS Office for Civil Rights
   - Notify media (if >500 individuals)

4. **Remediation**
   - Fix security vulnerability
   - Implement additional safeguards
   - Update policies/procedures

See `docs/compliance/incident-response-plan.md` for detailed procedures.

---

## References

- [HIPAA Privacy Rule](https://www.hhs.gov/hipaa/for-professionals/privacy/index.html)
- [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
- [Amazon Comprehend Medical Documentation](https://docs.aws.amazon.com/comprehend-medical/)
- [AES-GCM Encryption](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf)

---

## Support

For HIPAA compliance questions:
- Security Officer: security@yourdomain.com
- Privacy Officer: privacy@yourdomain.com
- Technical Support: support@yourdomain.com

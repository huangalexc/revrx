# PHI Handling Procedures

## Overview

This document outlines the procedures for handling Protected Health Information (PHI) in the Post-Facto Coding Review system. These procedures ensure compliance with HIPAA Privacy and Security Rules while enabling the system to process clinical documentation for coding analysis.

**HIPAA Compliance Strategy:** The system uses Amazon Comprehend Medical to detect and de-identify PHI before sending data to third-party AI services (OpenAI ChatGPT), ensuring PHI never leaves the HIPAA-compliant infrastructure.

---

## Table of Contents

1. [PHI Definition and Categories](#phi-definition-and-categories)
2. [PHI Lifecycle](#phi-lifecycle)
3. [De-identification Process](#de-identification-process)
4. [PHI Storage](#phi-storage)
5. [PHI Access Controls](#phi-access-controls)
6. [PHI Transmission](#phi-transmission)
7. [PHI Disposal](#phi-disposal)
8. [Incident Response](#incident-response)
9. [Training Requirements](#training-requirements)

---

## PHI Definition and Categories

### What is PHI?

Protected Health Information (PHI) is any information that can be used to identify an individual and relates to:
- Past, present, or future physical or mental health
- Provision of healthcare services
- Payment for healthcare services

### 18 HIPAA PHI Identifiers

1. **Names** - Patient name, family member names
2. **Geographic** - All subdivisions smaller than state (street address, city, zip code)
3. **Dates** - Birth, admission, discharge, death dates (except year)
4. **Phone Numbers** - All telephone numbers
5. **Fax Numbers** - All fax numbers
6. **Email Addresses** - All email addresses
7. **Social Security Numbers** - SSN
8. **Medical Record Numbers** - MRN, account numbers
9. **Health Plan Numbers** - Insurance ID numbers
10. **Certificate/License Numbers** - Professional license numbers
11. **Vehicle Identifiers** - License plates, serial numbers
12. **Device Identifiers** - Serial numbers, MAC addresses
13. **URLs** - Web URLs
14. **IP Addresses** - Internet Protocol addresses
15. **Biometric Identifiers** - Fingerprints, retinal scans
16. **Full-Face Photos** - Photos showing full face
17. **Unique Identifiers** - Any other unique identifying number/code
18. **Ages Over 89** - Must be aggregated to ≥90

### PHI in Our System

**Clinical Notes contain:**
- Patient names
- Dates (visit dates, DOB)
- Geographic information (addresses)
- Medical record numbers
- Phone numbers
- Medical conditions and treatments

**Billing Codes do NOT typically contain PHI:**
- CPT codes (procedure codes)
- ICD-10 codes (diagnosis codes)
- However, linked to encounters that contain PHI

---

## PHI Lifecycle

### Stage 1: Ingestion

**Action:** User uploads clinical note
**PHI Status:** Contains full PHI
**Security Measures:**
- HTTPS transmission (TLS 1.3)
- Authentication required
- File size validation (max 5MB)
- Virus scanning (ClamAV)
- Immediate encryption at rest

**Code Reference:** `backend/app/api/encounters.py:upload_note()`

### Stage 2: Storage

**Action:** Encrypted storage in S3-compatible bucket
**PHI Status:** Contains full PHI (encrypted)
**Security Measures:**
- AES-256 encryption at rest
- Server-side encryption enabled
- Presigned URLs for access (time-limited)
- Access logging enabled
- Bucket versioning enabled

**Storage Path:**
```
s3://revrx-uploads-{env}/
  raw-uploads/
    {user_id}/
      {encounter_id}/
        clinical-note.{ext}
        billing-codes.{ext}
```

### Stage 3: Processing - PHI Detection

**Action:** Extract text and detect PHI using Amazon Comprehend Medical
**PHI Status:** Full PHI analyzed
**Security Measures:**
- Processing occurs in secure worker environment
- PHI never logged
- AWS Comprehend Medical is HIPAA-compliant (BAA signed)
- Processing in same AWS region as data

**Code Reference:** `backend/app/services/phi_service.py:detect_phi()`

**Amazon Comprehend Medical API Call:**
```python
import boto3

client = boto3.client('comprehendmedical', region_name='us-east-1')

response = client.detect_phi(Text=clinical_note_text)

# Returns entities with:
# - Type: NAME, DATE, ADDRESS, PHONE, etc.
# - BeginOffset: Character position start
# - EndOffset: Character position end
# - Score: Confidence (0-1)
# - Text: The actual PHI text
```

### Stage 4: De-identification

**Action:** Replace PHI with tokens, store mapping
**PHI Status:** PHI removed (de-identified text created)
**Security Measures:**
- Token format: `[ENTITY_TYPE_N]`
- PHI mapping encrypted (AES-256)
- Mapping stored in database (separate encrypted column)
- Reversible de-identification for report generation

**Example:**
```
Original:
"Patient John Smith, DOB 03/15/1975, visited on 09/30/2025.
Phone: (555) 123-4567. Lives at 123 Main St, Anytown, CA 90210."

De-identified:
"Patient [NAME_1], DOB [DATE_1], visited on [DATE_2].
Phone: [PHONE_1]. Lives at [ADDRESS_1]."

PHI Mapping (encrypted):
{
  "NAME_1": "John Smith",
  "DATE_1": "03/15/1975",
  "DATE_2": "09/30/2025",
  "PHONE_1": "(555) 123-4567",
  "ADDRESS_1": "123 Main St, Anytown, CA 90210"
}
```

**Code Reference:** `backend/app/services/phi_service.py:deidentify_text()`

### Stage 5: AI Analysis

**Action:** Send de-identified text to ChatGPT for code suggestions
**PHI Status:** NO PHI (only de-identified text)
**Security Measures:**
- Only de-identified text sent to OpenAI
- No PHI tokens sent externally
- BAA with OpenAI (for extra protection)
- API calls over HTTPS
- Rate limiting and timeouts

**Important:** This is the key HIPAA compliance mechanism. PHI never leaves our infrastructure.

**Code Reference:** `backend/app/services/ai_service.py:suggest_codes()`

### Stage 6: Report Generation

**Action:** Create structured report with code suggestions
**PHI Status:** De-identified (tokens remain)
**Security Measures:**
- Reports stored in database (encrypted)
- Access requires authentication
- Owner verification enforced
- Download audit logged

**Report Format:**
```json
{
  "encounterId": "uuid",
  "billedCodes": [...],
  "suggestedCodes": [
    {
      "code": {"code": "99215", "type": "CPT"},
      "justification": "Documentation supports high complexity...",
      "supportingText": ["Patient [NAME_1] presented with..."],
      "confidence": 0.92,
      "estimatedRevenue": 75.00
    }
  ],
  "deIdentifiedText": "Patient [NAME_1]...",
  "totalIncrementalRevenue": 75.00
}
```

### Stage 7: Report Display

**Action:** User views report (optionally with re-identified PHI)
**PHI Status:** Can be re-identified for authorized user
**Security Measures:**
- Authentication and authorization required
- Owner must match or admin role
- PHI access logged in audit trail
- Time-based access tokens

**Re-identification Process:**
```python
# Decrypt PHI mapping
phi_mapping = decrypt_phi_mapping(report.phi_mapping)

# Replace tokens with original PHI
display_text = report.de_identified_text
for token, phi_value in phi_mapping.items():
    display_text = display_text.replace(f"[{token}]", phi_value)

# Log PHI access
audit_log(user_id, "phi_access", encounter_id)
```

### Stage 8: Retention & Disposal

**Action:** Data retained per policy, then securely deleted
**PHI Status:** Full PHI (until deletion)
**Security Measures:**
- Automated deletion after retention period
- Secure deletion (DoD 5220.22-M standard)
- Deletion audit trail
- Backup purging

**Retention Periods:**
- Encounter data: 365 days (configurable)
- Audit logs: 6 years (HIPAA requirement)
- Backups: 30 days

---

## De-identification Process

### Implementation Using Amazon Comprehend Medical

```python
# scripts/cm_example.py demonstrates the process

import boto3

client = boto3.client("comprehendmedical", region_name="us-east-1")

text = """
Patient John Smith was admitted on 04/15/2024 with chest pain.
Phone: (555) 123-4567. Lives at 123 Main St.
"""

# Step 1: Detect PHI
phi_response = client.detect_phi(Text=text)

# Step 2: Sort entities in reverse order
# (to avoid messing up offsets during replacement)
entities = sorted(
    phi_response["Entities"],
    key=lambda x: x["BeginOffset"],
    reverse=True
)

# Step 3: Redact PHI with placeholders
redacted_text = text
phi_mapping = {}
entity_counts = {}

for entity in entities:
    start, end = entity["BeginOffset"], entity["EndOffset"]
    entity_type = entity["Type"]

    # Generate unique token
    entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
    token = f"{entity_type}_{entity_counts[entity_type]}"

    # Store mapping
    phi_mapping[token] = text[start:end]

    # Replace with placeholder
    placeholder = f"[{token}]"
    redacted_text = redacted_text[:start] + placeholder + redacted_text[end:]

# Step 4: Encrypt PHI mapping
encrypted_mapping = encrypt_json(phi_mapping)

# Step 5: Store in database
save_report(
    encounter_id=encounter_id,
    de_identified_text=redacted_text,
    phi_mapping=encrypted_mapping
)
```

### Quality Assurance

**Manual Review:**
- Sample 10% of de-identified texts monthly
- Check for any remaining PHI
- Validate entity detection accuracy
- Document false positives/negatives

**Automated Testing:**
- Unit tests with known PHI examples
- Regex validation for common PHI patterns
- Confidence score thresholds
- Alert on low-confidence detections

**Continuous Improvement:**
- Track Comprehend Medical accuracy
- Report issues to AWS
- Maintain test case library
- Update procedures as needed

---

## PHI Storage

### Database Storage

**PHI Columns:**
- `Report.phi_mapping` - Encrypted PHI tokens mapping (JSONB, AES-256)
- `Encounter.patient_age` - Encrypted (if < 89)
- `Encounter.patient_sex` - Minimal identifier (M/F/O)

**Encryption:**
- Application-level encryption (AES-256-GCM)
- Database-level encryption (PostgreSQL TDE)
- Encryption keys managed via AWS KMS
- Key rotation annually

**Access Control:**
- Row-level security (RLS) policies
- User can only access own encounters
- Admin access fully audited
- No direct database access for developers

### File Storage (S3)

**Bucket Configuration:**
```json
{
  "bucket": "revrx-uploads-prod",
  "encryption": "AES256",
  "versioning": "Enabled",
  "lifecycle": {
    "expiration": 365,
    "transitions": [
      {"days": 90, "storage_class": "STANDARD_IA"},
      {"days": 180, "storage_class": "GLACIER"}
    ]
  },
  "logging": {
    "enabled": true,
    "target_bucket": "revrx-logs-prod"
  },
  "public_access_block": {
    "block_public_acls": true,
    "ignore_public_acls": true,
    "block_public_policy": true,
    "restrict_public_buckets": true
  }
}
```

**Access Method:**
- Presigned URLs only (no direct access)
- URLs expire after 15 minutes
- One-time use encouraged
- Access logged to audit trail

---

## PHI Access Controls

### Role-Based Access Control (RBAC)

**USER Role:**
- View own encounters and reports
- Upload files for own account
- Download own reports
- **Cannot** access other users' PHI
- **Cannot** view audit logs

**ADMIN Role:**
- View all users and encounters (audit logged)
- Access audit logs
- Manage users
- System configuration
- **Cannot** view PHI without specific audit trail entry

### Authentication Requirements

- JWT-based authentication
- Access token expiration: 1 hour
- Refresh token expiration: 7 days
- Failed login lockout: 5 attempts
- MFA recommended for admins

### Audit Logging

**All PHI Access Logged:**
```json
{
  "user_id": "uuid",
  "action": "phi_access",
  "resource_type": "encounter",
  "resource_id": "uuid",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "timestamp": "2025-09-30T12:34:56Z",
  "success": true
}
```

**Actions Logged:**
- encounter.upload_note
- encounter.upload_codes
- report.view
- report.download
- phi.access (when PHI mapping accessed)
- admin.view_user_data

---

## PHI Transmission

### In Transit Encryption

**Requirements:**
- TLS 1.3 minimum
- Strong cipher suites only
- Certificate validation enforced
- HSTS header enabled
- No HTTP access (redirect to HTTPS)

**API Communication:**
```
Client → API Gateway (TLS 1.3)
API Gateway → Backend (TLS 1.3)
Backend → Database (TLS 1.3)
Backend → S3 (HTTPS)
Backend → AWS Comprehend Medical (HTTPS)
Backend → OpenAI (HTTPS, de-identified only)
```

### External Service Communication

**Amazon Comprehend Medical:**
- PHI transmitted (BAA in place)
- HTTPS only
- Same AWS region (us-east-1)
- VPC endpoint recommended

**OpenAI ChatGPT:**
- NO PHI transmitted
- Only de-identified text
- HTTPS only
- BAA for extra protection

**Stripe:**
- NO PHI transmitted
- Only email and payment info
- BAA in place

---

## PHI Disposal

### Automated Deletion

**Retention Policy:**
- Encounters: 365 days (configurable)
- Audit logs: 6 years (HIPAA requirement)
- Backups: 30 days

**Deletion Process:**
```python
# Daily scheduled job
@celery.app.task
def delete_expired_encounters():
    expiration_date = datetime.now() - timedelta(days=365)

    encounters = Encounter.query.filter(
        Encounter.created_at < expiration_date
    ).all()

    for encounter in encounters:
        # Delete S3 files
        storage_service.delete_file(encounter.note_file_path)
        storage_service.delete_file(encounter.codes_file_path)

        # Delete database records (cascade to reports)
        db.session.delete(encounter)

        # Log deletion
        audit_log(
            action="data_deletion",
            resource_id=encounter.id,
            reason="retention_policy"
        )

    db.session.commit()
```

### Manual Deletion

**User-Requested Deletion:**
- User can delete encounters anytime
- "Delete Account" removes all user data
- Deletion within 24 hours
- Audit trail retained (6 years)
- Right to erasure (GDPR compliance)

### Secure Deletion Standards

**File Deletion:**
- DoD 5220.22-M standard (3-pass overwrite)
- Cryptographic erasure (delete encryption keys)
- S3 object versioning purge
- Backup deletion confirmation

**Database Deletion:**
- Hard delete (not soft delete after retention)
- VACUUM database to reclaim space
- Backup pruning
- Verify deletion in replicas

---

## Incident Response

### PHI Breach Definition

A PHI breach occurs when:
- Unauthorized access to PHI
- Unauthorized use or disclosure of PHI
- Compromise of PHI security

### Immediate Actions (< 1 hour)

1. **Contain the incident**
   - Revoke compromised credentials
   - Block malicious IP addresses
   - Isolate affected systems

2. **Assess the scope**
   - Identify what PHI was accessed
   - Determine number of affected individuals
   - Document timeline of events

3. **Notify security team**
   - Email: security@revrx.com
   - Phone: [24/7 hotline]
   - Incident commander assigned

### Investigation (< 24 hours)

1. **Determine root cause**
2. **Identify all affected individuals**
3. **Document evidence**
4. **Preserve logs and systems**

### Notification Requirements

**Individual Notification:**
- Required if breach affects 500+ individuals
- Within 60 days of discovery
- Method: Written notice by first-class mail

**HHS Notification:**
- Breaches affecting 500+: Within 60 days
- Breaches affecting < 500: Annual report

**Media Notification:**
- Required if breach affects 500+ in same state/jurisdiction
- Prominent media outlets

**See:** [Incident Response Plan](./incident-response-plan.md) for full procedures

---

## Training Requirements

### Initial Training (All Staff)

**Topics Covered:**
- HIPAA basics
- PHI identification
- Secure handling procedures
- Access controls
- Incident reporting
- Sanctions policy

**Duration:** 2 hours
**Format:** Online training + quiz
**Passing Score:** 85%

### Annual Refresher

**Duration:** 1 hour
**Format:** Online training
**Topics:** Policy updates, recent incidents, best practices

### Role-Specific Training

**Developers:**
- Secure coding practices
- De-identification implementation
- Encryption requirements
- Audit logging

**Administrators:**
- User management
- Audit log review
- Incident response
- Access control

**Support Staff:**
- Customer data handling
- Social engineering awareness
- Escalation procedures

### Training Records

- Maintained in HR system
- Completion tracked
- Certificates issued
- Accessible for audits

---

## Compliance Monitoring

### Monthly Activities

- [ ] Review audit logs for PHI access
- [ ] Validate de-identification accuracy (sample)
- [ ] Check for unauthorized access attempts
- [ ] Review user access levels

### Quarterly Activities

- [ ] Vulnerability scanning
- [ ] Penetration testing (external vendor)
- [ ] Policy review and updates
- [ ] Training completion verification

### Annual Activities

- [ ] Third-party HIPAA audit
- [ ] Risk assessment update
- [ ] BAA review and renewal
- [ ] Disaster recovery drill

---

## References

- [HIPAA Privacy Rule](https://www.hhs.gov/hipaa/for-professionals/privacy/index.html)
- [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
- [HHS Breach Notification Rule](https://www.hhs.gov/hipaa/for-professionals/breach-notification/index.html)
- [Amazon Comprehend Medical](https://docs.aws.amazon.com/comprehend-medical/)
- [NIST De-identification Guidance](https://www.nist.gov/itl/applied-cybersecurity/privacy-engineering/collaboration-space/focus-areas/de-id)

---

## Document Information

**Version:** 1.0
**Last Updated:** 2025-09-30
**Author:** RevRX Compliance Team
**Review Cycle:** Annual or after significant changes
**Next Review:** 2026-09-30

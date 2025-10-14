# Data Retention Policy

## Purpose

This Data Retention Policy establishes the guidelines and procedures for retaining and disposing of data in the RevRX Post-Facto Coding Review system. The policy ensures compliance with HIPAA, legal requirements, and business needs while minimizing data retention risks.

**Effective Date:** 2025-09-30
**Review Cycle:** Annual
**Policy Owner:** Compliance Officer
**Contact:** compliance@revrx.com

---

## Scope

This policy applies to all data stored, processed, or transmitted by the RevRX system, including:
- Protected Health Information (PHI)
- User account information
- Audit logs and security records
- Business records and reports
- System logs and operational data
- Backup and archive data

---

## Retention Periods

### Protected Health Information (PHI)

| Data Type | Retention Period | Rationale | Disposal Method |
|-----------|------------------|-----------|-----------------|
| Clinical Notes (Encrypted Files) | 365 days | Business requirement | Secure deletion (DoD 5220.22-M) |
| De-identified Text | 365 days | Linked to encounter | Secure deletion |
| PHI Mapping (Encrypted) | 365 days | Required for re-identification | Secure deletion + key destruction |
| Encounter Metadata | 365 days | Business requirement | Secure deletion |
| Generated Reports | 365 days | Business requirement | Secure deletion |

**Notes:**
- Retention period starts from encounter creation date
- Users can delete encounters earlier via UI
- Configurable via `DATA_RETENTION_DAYS` environment variable
- Default: 365 days (can be extended for business needs)

### Audit Logs

| Log Type | Retention Period | Rationale | Disposal Method |
|----------|------------------|-----------|-----------------|
| PHI Access Logs | 6 years | HIPAA requirement (§164.316(b)(2)(i)) | Secure archival, then deletion |
| Security Logs | 6 years | HIPAA requirement | Secure archival, then deletion |
| Authentication Logs | 6 years | Security and compliance | Secure archival, then deletion |
| System Logs | 1 year | Operational needs | Standard deletion |
| Application Logs | 90 days | Debugging and monitoring | Standard deletion |

**Notes:**
- HIPAA requires 6-year retention for audit logs
- Logs archived to cold storage after 1 year
- Audit logs stored separately from application database
- Immutable storage (WORM) for tamper-proofing

### User Account Data

| Data Type | Retention Period | Rationale | Disposal Method |
|-----------|------------------|-----------|-----------------|
| Active User Accounts | While active | N/A | N/A |
| Inactive User Accounts | 2 years after last login | Business requirement | Secure deletion after warning |
| Deleted User Accounts | Immediate (24 hours) | Right to erasure (GDPR) | Secure deletion |
| Account Deletion Audit | 6 years | Compliance requirement | Standard archival |

**Notes:**
- Users notified 30 days before account deletion due to inactivity
- Account deletion removes all personal data
- Audit trail of deletion retained (no PHI, only metadata)

### Payment and Subscription Data

| Data Type | Retention Period | Rationale | Disposal Method |
|-----------|------------------|-----------|-----------------|
| Subscription Records | 7 years | Tax and legal requirement | Secure archival |
| Payment Transactions | 7 years | Tax and legal requirement | Secure archival |
| Stripe Customer IDs | While subscribed + 7 years | Integration and legal | Standard deletion |
| Failed Payment Attempts | 90 days | Fraud detection | Standard deletion |

**Notes:**
- Payment card data never stored (handled by Stripe)
- 7-year retention complies with IRS requirements
- Archived to cold storage after subscription ends

### Backup Data

| Backup Type | Retention Period | Rationale | Disposal Method |
|-------------|------------------|-----------|-----------------|
| Daily Backups | 30 days | Disaster recovery | Secure deletion |
| Monthly Backups | 12 months | Long-term recovery | Secure deletion |
| Annual Backups | 7 years | Compliance and historical | Secure archival |

**Notes:**
- Backups encrypted at rest
- Stored in geographically separate region
- Backup restoration tested quarterly
- Old backups securely deleted (cannot be recovered)

---

## Data Lifecycle

### Stage 1: Active Data (0-90 days)

**Location:** Primary database and storage
**Access:** Immediate access by users
**Performance:** Optimized for fast retrieval
**Backup:** Daily incremental backups

### Stage 2: Inactive Data (90-365 days)

**Location:** Primary storage with lifecycle policy
**Access:** Available but less frequently accessed
**Performance:** Standard retrieval times
**Backup:** Weekly backups
**Action:** Automatic transition to Standard-IA storage (S3)

### Stage 3: Archival Data (365 days - retention end)

**Location:** Glacier or cold storage
**Access:** Rare access, retrieval time: hours
**Performance:** Slow retrieval acceptable
**Backup:** Included in archival storage
**Action:** Automatic transition to Glacier (S3)

### Stage 4: Deletion

**Location:** N/A (deleted)
**Access:** Permanently deleted
**Method:**
- Files: DoD 5220.22-M (3-pass overwrite) or cryptographic erasure
- Database: Hard delete + VACUUM
- Backups: Purged from all backup systems

---

## Automated Retention Management

### Daily Job: Encounter Deletion

```python
# Pseudocode for daily retention job

@schedule.every().day.at("02:00")
def enforce_retention_policy():
    retention_days = get_config("DATA_RETENTION_DAYS", 365)
    expiration_date = datetime.now() - timedelta(days=retention_days)

    # Find expired encounters
    expired_encounters = Encounter.query.filter(
        Encounter.created_at < expiration_date,
        Encounter.deleted_at.is_null()
    ).all()

    for encounter in expired_encounters:
        # Delete associated files from S3
        delete_encounter_files(encounter.id)

        # Delete database records
        soft_delete_encounter(encounter.id)

        # Log deletion
        audit_log(
            action="automated_retention_deletion",
            resource_type="encounter",
            resource_id=encounter.id,
            reason="retention_policy_expiration"
        )

    # Hard delete soft-deleted records after 30 days
    purge_date = datetime.now() - timedelta(days=30)
    permanently_delete_encounters(purge_date)
```

### Monthly Job: Audit Log Archival

```python
# Pseudocode for monthly audit log archival

@schedule.every().month.on(1).at("03:00")
def archive_old_audit_logs():
    # Archive logs older than 1 year to cold storage
    archive_date = datetime.now() - timedelta(days=365)

    old_logs = AuditLog.query.filter(
        AuditLog.timestamp < archive_date
    ).all()

    # Export to compressed format
    export_to_glacier(old_logs)

    # Mark as archived in database
    for log in old_logs:
        log.archived = True
        log.archive_location = "s3://revrx-audit-archive/..."

    db.session.commit()
```

### Annual Job: Compliance Deletion

```python
# Pseudocode for annual compliance deletion

@schedule.every().year.on("01/01").at("00:00")
def delete_expired_compliance_records():
    # Delete audit logs older than 6 years
    deletion_date = datetime.now() - timedelta(days=2190)  # 6 years

    AuditLog.query.filter(
        AuditLog.timestamp < deletion_date
    ).delete()

    # Delete subscription records older than 7 years
    subscription_deletion_date = datetime.now() - timedelta(days=2555)  # 7 years

    Subscription.query.filter(
        Subscription.cancelled_at < subscription_deletion_date
    ).delete()

    db.session.commit()
```

---

## Legal Hold

### When to Implement

A legal hold suspends normal retention policies when:
- Litigation is pending or anticipated
- Government investigation initiated
- Regulatory audit requested
- Subpoena or court order received

### Legal Hold Procedure

1. **Notification:** Legal counsel notifies Compliance Officer
2. **Identification:** Identify all relevant data and systems
3. **Preservation:** Apply legal hold tags to prevent deletion
4. **Documentation:** Document scope and duration of hold
5. **Communication:** Notify all relevant staff
6. **Monitoring:** Ensure hold is enforced
7. **Release:** Remove hold only when authorized by legal counsel

### Technical Implementation

```python
# Legal hold flag in database
class Encounter(Model):
    id = Column(UUID)
    legal_hold = Column(Boolean, default=False)
    legal_hold_reason = Column(String)
    legal_hold_date = Column(DateTime)

# Retention job checks for legal hold
def should_delete_encounter(encounter):
    if encounter.legal_hold:
        return False  # Skip deletion

    # Check normal retention policy
    return encounter.created_at < retention_expiration_date
```

---

## User-Requested Deletion

### Right to Erasure (GDPR Article 17)

Users have the right to request deletion of their personal data.

### Deletion Process

1. **Request:** User submits deletion request via UI or email
2. **Verification:** Verify user identity
3. **Impact Assessment:** Determine legal obligations (retain audit logs)
4. **Approval:** Approve deletion (automatic for most cases)
5. **Execution:** Delete personal data within 24 hours
6. **Confirmation:** Send deletion confirmation to user
7. **Audit:** Log deletion in audit trail (retained per HIPAA)

### What is Deleted

- User account information
- All encounters and reports
- Uploaded files (clinical notes, billing codes)
- PHI and de-identified data
- Subscription information (after 7 years)

### What is Retained

- Audit logs (anonymized user ID retained)
- Aggregated analytics (no personal data)
- Billing records (required by law for 7 years)

---

## Data Minimization

### Principle

Collect and retain only data necessary for business purposes.

### Practices

- **Limit PHI Collection:** Only collect PHI necessary for coding analysis
- **De-identification:** De-identify PHI before external processing
- **Access Restrictions:** Limit access to need-to-know basis
- **Automatic Deletion:** Delete data when no longer needed
- **Regular Review:** Quarterly review of retained data

### Example: Patient Demographics

**Collect:**
- Age (for billing context)
- Sex (for billing context)
- Visit date (for billing context)

**Do NOT Collect:**
- Full name (unless in clinical note)
- Full address
- Social Security Number
- Full date of birth (only age)

---

## Exceptions

### Extension of Retention Period

Retention periods may be extended for:
- Legal hold (litigation, investigation)
- Active disputes or claims
- Regulatory requirements
- Business necessity (with justification)

**Approval Required:** Compliance Officer

### Early Deletion

Data may be deleted before retention period ends:
- User-requested deletion
- System error correction
- Security incident response
- Data breach remediation

**Approval Required:** Compliance Officer or Security Officer

---

## Secure Deletion Methods

### File Deletion (DoD 5220.22-M)

**3-Pass Overwrite:**
1. Pass 1: Write zeros (0x00) to all sectors
2. Pass 2: Write ones (0xFF) to all sectors
3. Pass 3: Write random data to all sectors
4. Verification: Verify data is unrecoverable

**Alternative: Cryptographic Erasure**
- Delete encryption keys
- Renders data unreadable
- Faster than overwriting
- Suitable for encrypted storage

### Database Deletion

```sql
-- Hard delete (not soft delete)
DELETE FROM encounters WHERE id = 'uuid';

-- Free up space
VACUUM FULL encounters;

-- Verify deletion
SELECT COUNT(*) FROM encounters WHERE id = 'uuid';
-- Should return 0
```

### Backup Deletion

```bash
# Delete backup files
aws s3 rm s3://revrx-backups/backup-2024-01-01.sql.gz

# Purge all versions
aws s3api delete-objects \
  --bucket revrx-backups \
  --delete "$(aws s3api list-object-versions \
    --bucket revrx-backups \
    --prefix backup-2024-01-01 \
    --output=json | \
    jq '{Objects: [.Versions[] | {Key:.Key, VersionId : .VersionId}], Quiet: false}')"
```

---

## Monitoring and Compliance

### Monthly Review

- [ ] Verify retention jobs executed successfully
- [ ] Check for any failed deletions
- [ ] Review legal holds (still necessary?)
- [ ] Audit storage usage trends

### Quarterly Review

- [ ] Audit sample of deleted data (verify unrecoverable)
- [ ] Review retention policy effectiveness
- [ ] Update retention periods if needed
- [ ] Test data recovery procedures

### Annual Review

- [ ] Full policy review
- [ ] Legal and regulatory update check
- [ ] Third-party audit of retention practices
- [ ] Update policy as needed

---

## Responsibilities

### Compliance Officer

- Policy owner and enforcement
- Legal hold decisions
- Exception approvals
- Regulatory compliance

### Engineering Team

- Implement automated retention
- Secure deletion procedures
- Monitoring and alerting
- Technical compliance

### Security Team

- Audit log retention
- Secure deletion verification
- Incident response
- Access control

### Legal Counsel

- Legal hold notifications
- Regulatory guidance
- Litigation support
- Policy review

---

## Training

All staff must complete annual training on:
- Data retention requirements
- Secure deletion procedures
- Legal hold procedures
- Incident reporting

**Completion Required:** 100%
**Tracking:** HR training system

---

## Policy Updates

### Change Log

| Version | Date | Changes | Approver |
|---------|------|---------|----------|
| 1.0 | 2025-09-30 | Initial policy | Compliance Officer |

### Review Schedule

- **Next Review:** 2026-09-30
- **Review Cycle:** Annual or after significant regulatory changes
- **Review By:** Compliance Officer, Legal Counsel

---

## References

- HIPAA Security Rule §164.316(b)(2)(i) - Retention of documentation
- GDPR Article 17 - Right to erasure
- IRS Publication 583 - Record retention for businesses
- DoD 5220.22-M - Data sanitization standard
- NIST SP 800-88 - Guidelines for Media Sanitization

---

## Document Information

**Version:** 1.0
**Effective Date:** 2025-09-30
**Last Updated:** 2025-09-30
**Author:** RevRX Compliance Team
**Review Cycle:** Annual
**Next Review:** 2026-09-30

# PHI Handling - Quick Reference

## Quick Start

### 1. Process Clinical Note with PHI Detection

```python
from app.services.phi_handler import phi_handler

# One-line processing
result = await phi_handler.process_clinical_note(
    encounter_id="encounter-uuid",
    clinical_text="Patient John Smith was admitted...",
    user_id="user-uuid"
)

# Get de-identified text (safe for AI)
safe_text = result.deidentified_text
```

### 2. Retrieve De-identified Text Later

```python
# Get just the text
text = await phi_handler.get_deidentified_text(encounter_id)

# Or get full result with mappings
result = await phi_handler.retrieve_phi_mapping(encounter_id)
```

### 3. Re-identify for Authorized Reports

```python
# Get stored result
result = await phi_handler.retrieve_phi_mapping(encounter_id)

# Re-identify
original_text = phi_handler.reidentify(
    result.deidentified_text,
    result.phi_mappings
)
```

---

## Common Patterns

### Pattern 1: Encounter Upload Processing

```python
@router.post("/encounters/{id}/process")
async def process_encounter(
    encounter_id: str,
    current_user: User = Depends(get_current_active_user)
):
    # 1. Get uploaded file and extract text
    file_text = await extract_text(encounter_id)

    # 2. Process PHI
    result = await phi_handler.process_clinical_note(
        encounter_id, file_text, current_user.id
    )

    # 3. Use de-identified text for AI
    ai_response = await process_with_ai(result.deidentified_text)

    return {"status": "success", "phi_detected": result.phi_detected}
```

### Pattern 2: Report Generation with Optional PHI

```python
@router.get("/encounters/{id}/report")
async def get_report(
    encounter_id: str,
    include_phi: bool = False,
    current_user: User = Depends(get_current_user)
):
    # Get PHI result
    result = await phi_handler.retrieve_phi_mapping(encounter_id)

    # Admin can see PHI
    if include_phi and current_user.role == "ADMIN":
        text = phi_handler.reidentify(
            result.deidentified_text,
            result.phi_mappings
        )

        # Log PHI access
        await log_phi_access(current_user.id, encounter_id)
    else:
        text = result.deidentified_text

    return {"text": text}
```

### Pattern 3: Encryption for Custom Data

```python
from app.core.encryption import encryption_service

# Encrypt custom PHI data
encrypted = encryption_service.encrypt_json({
    "ssn": "123-45-6789",
    "mrn": "MRN-12345"
})

# Store in database
await prisma.customdata.create(data={"encrypted": encrypted})

# Decrypt later
data = encryption_service.decrypt_json(encrypted)
```

---

## PHI Types Detected

| Type | Examples |
|------|----------|
| NAME | John Smith, Dr. Sarah Johnson |
| DATE | 04/15/1980, January 5, 2024 |
| AGE | 92 years old (ages > 89) |
| PHONE_OR_FAX | (555) 123-4567 |
| EMAIL | patient@example.com |
| ID | MRN-12345, SSN 123-45-6789 |
| ADDRESS | 123 Main St, Boston, MA |
| URL | http://example.com |
| IP_ADDRESS | 192.168.1.1 |

---

## De-identification Examples

### Input
```
Patient John Smith (DOB: 04/15/1980) was admitted on 12/20/2023.
Phone: (555) 123-4567. MRN: 12345.
```

### Output
```
Patient [NAME_1] (DOB: [DATE_1]) was admitted on [DATE_2].
Phone: [PHONE_OR_FAX_1]. MRN: [ID_1].
```

---

## Error Handling

### Common Errors

```python
from botocore.exceptions import ClientError

try:
    result = await phi_handler.process_clinical_note(...)
except ClientError as e:
    if e.response['Error']['Code'] == 'TextSizeLimitExceededException':
        # Text > 20KB, split or summarize
        pass
    elif e.response['Error']['Code'] == 'ThrottlingException':
        # Rate limited, retry with backoff
        pass
except ValueError as e:
    # Encryption/decryption error
    logger.error("Encryption error", error=str(e))
```

---

## Best Practices

### ✅ DO

```python
# Use de-identified text for AI
deidentified = await phi_handler.get_deidentified_text(encounter_id)
ai_response = await openai.process(deidentified)

# Log all PHI access
await prisma.auditlog.create(data={
    "userId": user_id,
    "action": "PHI_ACCESSED",
    "resourceType": "Encounter",
    "resourceId": encounter_id
})

# Verify user owns resource before PHI access
await verify_resource_ownership(encounter.userId, current_user)
```

### ❌ DON'T

```python
# DON'T log PHI
logger.info(f"Processing patient John Smith")  # BAD

# DON'T send PHI to OpenAI
openai.process(original_clinical_text)  # BAD

# DON'T skip audit logging
result = await phi_handler.retrieve_phi_mapping(encounter_id)
# Missing audit log! BAD
```

---

## Configuration

### Required Environment Variables

```bash
# AWS Comprehend Medical
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_COMPREHEND_MEDICAL_REGION=us-east-1

# Encryption
PHI_ENCRYPTION_KEY=base64-encoded-32-byte-key

# Generate key:
python -m app.core.encryption
```

---

## Testing

### Unit Test Example

```python
import pytest
from app.services.phi_handler import phi_handler

@pytest.mark.asyncio
async def test_phi_deidentification():
    text = "Patient John Smith (DOB: 04/15/1980)"

    result = phi_handler.detect_and_deidentify(text)

    assert result.phi_detected == True
    assert "[NAME_1]" in result.deidentified_text
    assert "[DATE_1]" in result.deidentified_text
    assert "John Smith" not in result.deidentified_text

@pytest.mark.asyncio
async def test_reidentification():
    original = "Patient John Smith"
    result = phi_handler.detect_and_deidentify(original)

    reidentified = phi_handler.reidentify(
        result.deidentified_text,
        result.phi_mappings
    )

    assert reidentified == original
```

---

## Monitoring

### Key Metrics

```python
# PHI detection rate
phi_count = await prisma.phimapping.count(where={"phiDetected": True})
total = await prisma.encounter.count()
rate = (phi_count / total * 100) if total > 0 else 0

# Average PHI entities per encounter
avg = await prisma.phimapping.aggregate(_avg={"phiEntityCount": True})

# Recent PHI access
logs = await prisma.auditlog.find_many(
    where={"action": "PHI_ACCESSED"},
    order={"createdAt": "desc"},
    take=50
)
```

---

## Data Retention

### Run Cleanup Manually

```bash
# CLI
python -m app.scripts.retention_cleanup

# Programmatically
from app.services.data_retention import data_retention_service

stats = await data_retention_service.run_retention_cleanup()
```

### Check Retention Status

```python
from app.services.data_retention import data_retention_service

# Specific encounter
status = await data_retention_service.get_retention_status(encounter_id)
print(f"Days until deletion: {status['days_until_deletion']}")

# Overall summary
summary = await data_retention_service.get_retention_summary()
print(f"Encounters expiring soon: {summary['expiring_within_30_days']}")
```

---

## Troubleshooting

### Issue: "Text too large" error

```python
# Check size before processing
text_bytes = len(text.encode('utf-8'))
if text_bytes > 20000:
    # Option 1: Truncate
    text = text[:20000]

    # Option 2: Split and process chunks
    chunks = split_text(text, 20000)
    for chunk in chunks:
        result = phi_handler.detect_and_deidentify(chunk)
```

### Issue: Decryption fails

```python
# Verify encryption key
from app.core.config import settings
print(f"Key length: {len(base64.b64decode(settings.PHI_ENCRYPTION_KEY))}")
# Should be 32 bytes

# Test encryption/decryption
from app.core.encryption import encryption_service
test = encryption_service.encrypt("test")
assert encryption_service.decrypt(test) == "test"
```

---

## API Endpoints (Future)

### Process Encounter
```http
POST /api/v1/encounters/{id}/process
Authorization: Bearer {token}

Response:
{
  "status": "completed",
  "phi_detected": true,
  "phi_count": 5,
  "processing_time_ms": 1500
}
```

### Get Report
```http
GET /api/v1/encounters/{id}/report?include_phi=false
Authorization: Bearer {token}

Response:
{
  "report": {...},
  "clinical_text": "Patient [NAME_1] was admitted..."
}
```

---

## Further Reading

- **Complete Guide**: `backend/docs/HIPAA_COMPLIANCE.md`
- **Implementation Summary**: `backend/docs/PHI_IMPLEMENTATION_SUMMARY.md`
- **Code Examples**: See `scripts/cm_example.py` for AWS Comprehend Medical usage

---

## Support

For PHI-related questions:
- Check: `backend/docs/HIPAA_COMPLIANCE.md`
- Security: security@yourdomain.com
- Technical: support@yourdomain.com

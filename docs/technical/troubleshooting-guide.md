# Troubleshooting Guide

## Overview

This guide provides solutions to common issues encountered in the Post-Facto Coding Review MVP. It covers backend, frontend, deployment, and integration issues.

---

## Table of Contents

1. [Authentication Issues](#authentication-issues)
2. [File Upload Problems](#file-upload-problems)
3. [Processing Pipeline Failures](#processing-pipeline-failures)
4. [Database Connection Issues](#database-connection-issues)
5. [API Integration Errors](#api-integration-errors)
6. [Performance Issues](#performance-issues)
7. [Deployment Problems](#deployment-problems)
8. [Security & Compliance Issues](#security--compliance-issues)
9. [Monitoring & Logging](#monitoring--logging)
10. [Common Error Messages](#common-error-messages)

---

## Authentication Issues

### Issue: User Cannot Log In

**Symptoms:**
- "Invalid credentials" error despite correct password
- Login endpoint returns 401 Unauthorized

**Possible Causes & Solutions:**

1. **Email not verified**
   ```bash
   # Check user verification status
   psql $DATABASE_URL -c "SELECT email, email_verified FROM \"User\" WHERE email='user@example.com';"

   # Manually verify user (development only)
   psql $DATABASE_URL -c "UPDATE \"User\" SET email_verified=true WHERE email='user@example.com';"
   ```

2. **Password hash mismatch**
   ```bash
   # Reset password via API
   curl -X POST https://api.revrx.com/auth/forgot-password \
     -H "Content-Type: application/json" \
     -d '{"email":"user@example.com"}'
   ```

3. **JWT secret misconfiguration**
   ```bash
   # Verify JWT_SECRET is set
   kubectl exec deployment/revrx-backend -- env | grep JWT_SECRET

   # Generate new secret if missing
   openssl rand -base64 32
   ```

### Issue: JWT Token Expired

**Symptoms:**
- 401 Unauthorized on authenticated requests
- "Token expired" error message

**Solutions:**

```javascript
// Frontend: Implement token refresh
async function refreshToken() {
  const response = await fetch('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refreshToken: localStorage.getItem('refreshToken') })
  });
  const { accessToken } = await response.json();
  localStorage.setItem('accessToken', accessToken);
}

// Retry request with new token
axios.interceptors.response.use(
  response => response,
  async error => {
    if (error.response.status === 401) {
      await refreshToken();
      return axios.request(error.config);
    }
    return Promise.reject(error);
  }
);
```

### Issue: CORS Errors on Login

**Symptoms:**
- Browser console shows CORS policy error
- OPTIONS preflight requests failing

**Solutions:**

```python
# Backend: Check CORS configuration (FastAPI)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://revrx.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## File Upload Problems

### Issue: File Upload Fails with 413 Error

**Symptoms:**
- "Payload too large" error
- Upload stops at certain file size

**Solutions:**

1. **Increase nginx upload limit**
   ```yaml
   # kubernetes/ingress.yaml
   annotations:
     nginx.ingress.kubernetes.io/proxy-body-size: "10m"
   ```

2. **Check backend file size limit**
   ```python
   # backend/app/core/config.py
   MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
   ```

### Issue: PDF Text Extraction Fails

**Symptoms:**
- Processing status stuck at "processing"
- Error: "Could not extract text from PDF"

**Solutions:**

```python
# Try alternative PDF library
import pdfplumber

try:
    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
except Exception as e:
    # Fallback to OCR for scanned PDFs
    import pytesseract
    from pdf2image import convert_from_path

    images = convert_from_path(pdf_file)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img)
```

### Issue: S3 Upload Permission Denied

**Symptoms:**
- Error: "Access Denied" when uploading to S3
- HTTP 403 Forbidden

**Solutions:**

```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify S3 bucket policy
aws s3api get-bucket-policy --bucket revrx-uploads

# Test upload manually
aws s3 cp test.txt s3://revrx-uploads/test.txt

# Check IAM policy
aws iam get-user-policy --user-name revrx-api --policy-name s3-upload-policy
```

**Required IAM Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::revrx-uploads/*"
    }
  ]
}
```

---

## Processing Pipeline Failures

### Issue: Comprehend Medical API Errors

**Symptoms:**
- Processing fails at PHI detection step
- Error: "ThrottlingException" or "ServiceUnavailableException"

**Solutions:**

1. **Rate limiting**
   ```python
   import time
   from functools import wraps

   def rate_limited(max_per_second):
       min_interval = 1.0 / max_per_second
       last_called = [0.0]

       def decorator(func):
           @wraps(func)
           def wrapper(*args, **kwargs):
               elapsed = time.time() - last_called[0]
               left_to_wait = min_interval - elapsed
               if left_to_wait > 0:
                   time.sleep(left_to_wait)
               result = func(*args, **kwargs)
               last_called[0] = time.time()
               return result
           return wrapper
       return decorator

   @rate_limited(max_per_second=10)
   def detect_phi(text):
       return comprehend_client.detect_phi(Text=text)
   ```

2. **Exponential backoff**
   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential

   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=2, max=10)
   )
   def detect_phi_with_retry(text):
       return comprehend_client.detect_phi(Text=text)
   ```

### Issue: OpenAI API Timeout

**Symptoms:**
- Processing takes > 30 seconds
- Error: "Request timeout"

**Solutions:**

```python
import openai
from openai import OpenAI

client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    timeout=60.0,  # Increase timeout
    max_retries=2
)

# Use streaming for better user experience
response = client.chat.completions.create(
    model="gpt-4",
    messages=[...],
    stream=True,
    timeout=60
)

for chunk in response:
    if chunk.choices[0].delta.content:
        # Process chunk by chunk
        process_chunk(chunk.choices[0].delta.content)
```

### Issue: Background Job Not Processing

**Symptoms:**
- Encounter status stuck at "pending"
- Celery worker logs show no activity

**Solutions:**

```bash
# Check Celery worker status
kubectl logs deployment/revrx-worker

# Inspect queue
kubectl exec deployment/revrx-backend -- python -c "
from app.celery_app import celery_app
inspect = celery_app.control.inspect()
print('Active:', inspect.active())
print('Scheduled:', inspect.scheduled())
print('Reserved:', inspect.reserved())
"

# Restart workers
kubectl rollout restart deployment/revrx-worker

# Check Redis connection
kubectl exec deployment/revrx-backend -- redis-cli -h redis-master ping
```

---

## Database Connection Issues

### Issue: Connection Pool Exhausted

**Symptoms:**
- Error: "Cannot acquire connection from pool"
- Slow API responses

**Solutions:**

```python
# Increase pool size (Prisma)
# backend/prisma/schema.prisma
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
  connection_limit = 20  # Increase from default 10
}

# Or use connection string parameter
DATABASE_URL="postgresql://user:pass@host:5432/db?connection_limit=20&pool_timeout=10"
```

```bash
# Check active connections
psql $DATABASE_URL -c "
SELECT count(*) as active_connections,
       state
FROM pg_stat_activity
WHERE datname = 'revrx'
GROUP BY state;
"

# Kill idle connections
psql $DATABASE_URL -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'revrx'
  AND state = 'idle'
  AND state_change < now() - interval '5 minutes';
"
```

### Issue: Slow Database Queries

**Symptoms:**
- High response times (> 1 second)
- Database CPU usage at 100%

**Solutions:**

```bash
# Identify slow queries
psql $DATABASE_URL -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"

# Check missing indexes
psql $DATABASE_URL -c "
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
  AND n_distinct > 100
  AND correlation < 0.1;
"

# Create missing indexes
psql $DATABASE_URL -c "
CREATE INDEX CONCURRENTLY idx_encounter_user_status
ON \"Encounter\"(user_id, status);
"

# Analyze tables
psql $DATABASE_URL -c "ANALYZE VERBOSE;"
```

---

## API Integration Errors

### Issue: Stripe Webhook Signature Verification Failed

**Symptoms:**
- Webhook events not processing
- Error: "Invalid signature"

**Solutions:**

```python
import stripe
from fastapi import Request, HTTPException

@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        # Check webhook secret is correct
        # Verify endpoint URL in Stripe dashboard
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Process event
    handle_stripe_event(event)
    return {"status": "success"}
```

```bash
# Test webhook locally using Stripe CLI
stripe listen --forward-to localhost:8000/webhooks/stripe
stripe trigger payment_intent.succeeded
```

### Issue: Email Delivery Failures

**Symptoms:**
- Verification emails not received
- No errors in logs

**Solutions:**

```python
# Add retry logic
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def send_email(to: str, subject: str, body: str):
    try:
        response = resend.emails.send({
            "from": "noreply@revrx.com",
            "to": to,
            "subject": subject,
            "html": body
        })
        logger.info(f"Email sent: {response['id']}")
        return response
    except Exception as e:
        logger.error(f"Email failed: {e}")
        raise

# Check email service status
import requests
response = requests.get("https://status.resend.com/api/v2/status.json")
print(response.json())
```

---

## Performance Issues

### Issue: High API Latency

**Symptoms:**
- Response times > 500ms
- User complaints about slow loading

**Solutions:**

1. **Add caching**
   ```python
   from functools import lru_cache
   import redis

   redis_client = redis.Redis(host='redis-master', port=6379)

   @lru_cache(maxsize=100)
   def get_user_profile(user_id: str):
       # Cache in memory
       return db.user.find_unique(where={"id": user_id})

   def get_report_cached(encounter_id: str):
       # Cache in Redis
       cached = redis_client.get(f"report:{encounter_id}")
       if cached:
           return json.loads(cached)

       report = db.report.find_unique(where={"encounterId": encounter_id})
       redis_client.setex(f"report:{encounter_id}", 3600, json.dumps(report))
       return report
   ```

2. **Optimize database queries**
   ```python
   # Bad: N+1 query problem
   encounters = db.encounter.find_many(where={"userId": user_id})
   for encounter in encounters:
       report = db.report.find_unique(where={"encounterId": encounter.id})

   # Good: Use include
   encounters = db.encounter.find_many(
       where={"userId": user_id},
       include={"report": True}
   )
   ```

3. **Enable compression**
   ```python
   from fastapi.middleware.gzip import GZipMiddleware

   app.add_middleware(GZipMiddleware, minimum_size=1000)
   ```

### Issue: High Memory Usage

**Symptoms:**
- Pods restarting with OOMKilled status
- Memory usage steadily increasing

**Solutions:**

```bash
# Check memory usage
kubectl top pods

# Increase memory limits
kubectl set resources deployment/revrx-backend \
  --limits=memory=4Gi \
  --requests=memory=2Gi

# Profile memory usage
kubectl exec deployment/revrx-backend -- python -m memory_profiler app/main.py
```

```python
# Fix memory leaks
import gc

# Explicitly delete large objects
def process_large_file(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()
        result = process_data(data)
        del data  # Free memory
        gc.collect()
    return result
```

---

## Deployment Problems

### Issue: Pod CrashLoopBackOff

**Symptoms:**
- Pods constantly restarting
- Application not accessible

**Diagnostic Steps:**

```bash
# Check pod status
kubectl get pods

# View pod logs
kubectl logs deployment/revrx-backend --tail=100

# Describe pod for events
kubectl describe pod <pod-name>

# Check previous container logs
kubectl logs <pod-name> --previous
```

**Common Causes:**

1. **Missing environment variables**
   ```bash
   # Verify all required env vars
   kubectl exec deployment/revrx-backend -- env | sort

   # Add missing secret
   kubectl create secret generic revrx-secrets \
     --from-literal=DATABASE_URL='...' \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

2. **Database migration not run**
   ```bash
   # Run migrations
   kubectl exec deployment/revrx-backend -- npx prisma migrate deploy
   ```

3. **Port conflict**
   ```yaml
   # Ensure port matches Dockerfile EXPOSE
   containers:
   - name: backend
     ports:
     - containerPort: 8000  # Must match app.run(port=8000)
   ```

### Issue: Ingress Not Routing Traffic

**Symptoms:**
- 404 Not Found on all routes
- SSL certificate not applied

**Solutions:**

```bash
# Check ingress status
kubectl get ingress
kubectl describe ingress revrx-ingress

# Verify ingress controller running
kubectl get pods -n ingress-nginx

# Test service directly
kubectl port-forward svc/revrx-backend 8000:80
curl http://localhost:8000/health

# Check DNS resolution
nslookup revrx.com

# Verify TLS secret
kubectl get secret revrx-tls -o yaml
```

---

## Security & Compliance Issues

### Issue: PHI Exposed in Logs

**Symptoms:**
- Audit findings show PHI in application logs
- Compliance violation

**Solutions:**

```python
import logging
import re

class PHIFilter(logging.Filter):
    """Filter to redact PHI from logs"""

    PHI_PATTERNS = [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{10}\b',  # Phone
        r'\b[\w\.-]+@[\w\.-]+\.\w+\b',  # Email
    ]

    def filter(self, record):
        for pattern in self.PHI_PATTERNS:
            record.msg = re.sub(pattern, '[REDACTED]', str(record.msg))
        return True

logger = logging.getLogger(__name__)
logger.addFilter(PHIFilter())
```

### Issue: Audit Log Gaps

**Symptoms:**
- Missing audit trail entries
- Compliance requirements not met

**Solutions:**

```python
from functools import wraps

def audit_log(action: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get('current_user').id
            resource_id = kwargs.get('encounter_id')

            try:
                result = await func(*args, **kwargs)

                # Log successful action
                await db.auditlog.create({
                    "userId": user_id,
                    "action": action,
                    "resourceType": "Encounter",
                    "resourceId": resource_id,
                    "success": True,
                    "timestamp": datetime.utcnow()
                })

                return result
            except Exception as e:
                # Log failed action
                await db.auditlog.create({
                    "userId": user_id,
                    "action": action,
                    "success": False,
                    "metadata": {"error": str(e)}
                })
                raise
        return wrapper
    return decorator

@app.post("/encounters/{encounter_id}/report")
@audit_log("report.view")
async def get_report(encounter_id: str, current_user: User):
    return await fetch_report(encounter_id)
```

---

## Monitoring & Logging

### Issue: Logs Not Appearing in ELK

**Symptoms:**
- Empty Kibana dashboards
- No logs in Elasticsearch

**Solutions:**

```bash
# Check Filebeat/Fluentd status
kubectl get pods -n logging

# Verify log format is JSON
kubectl logs deployment/revrx-backend | head -1 | jq .

# Test Elasticsearch connection
kubectl exec deployment/revrx-backend -- curl -X GET elasticsearch:9200/_cluster/health

# Check index exists
curl -X GET "elasticsearch:9200/_cat/indices?v"
```

### Issue: Prometheus Not Scraping Metrics

**Symptoms:**
- Missing metrics in Grafana
- Prometheus targets down

**Solutions:**

```bash
# Check Prometheus targets
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
# Visit http://localhost:9090/targets

# Verify service monitor
kubectl get servicemonitor -n monitoring

# Check metrics endpoint
kubectl exec deployment/revrx-backend -- curl localhost:8000/metrics
```

```python
# Ensure metrics endpoint exposed
from prometheus_client import Counter, Histogram, generate_latest

request_count = Counter('http_requests_total', 'Total requests', ['method', 'endpoint'])
request_duration = Histogram('http_request_duration_seconds', 'Request duration')

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

## Common Error Messages

### Error: "FOREIGN KEY constraint failed"

**Cause:** Attempting to create/update record with invalid foreign key reference

**Solution:**
```python
# Verify parent record exists first
user = await db.user.find_unique(where={"id": user_id})
if not user:
    raise HTTPException(status_code=404, detail="User not found")

encounter = await db.encounter.create({
    "userId": user_id,  # Now guaranteed to exist
    # ...
})
```

### Error: "Unique constraint violated"

**Cause:** Duplicate value for unique field (email, etc.)

**Solution:**
```python
# Check for existing record first
existing_user = await db.user.find_unique(where={"email": email})
if existing_user:
    raise HTTPException(status_code=409, detail="Email already registered")

# Or use upsert
user = await db.user.upsert(
    where={"email": email},
    create={"email": email, ...},
    update={"updatedAt": datetime.utcnow()}
)
```

### Error: "PHI mapping decryption failed"

**Cause:** Encryption key changed or corrupted data

**Solution:**
```python
from cryptography.fernet import Fernet, InvalidToken

def decrypt_phi_mapping(encrypted_data: bytes) -> dict:
    try:
        cipher = Fernet(settings.ENCRYPTION_KEY)
        decrypted = cipher.decrypt(encrypted_data)
        return json.loads(decrypted)
    except InvalidToken:
        logger.error("PHI decryption failed - key mismatch")
        # Alert security team
        send_security_alert("PHI decryption failure")
        raise HTTPException(status_code=500, detail="Data integrity error")
```

---

## Getting Help

### Internal Resources

- **Slack Channels:**
  - `#revrx-support` - General support
  - `#revrx-engineering` - Technical issues
  - `#revrx-devops` - Deployment/infrastructure

- **Documentation:**
  - [API Documentation](./api-documentation.yaml)
  - [Architecture Diagrams](./architecture-diagrams.md)
  - [Deployment Guide](./deployment-guide.md)

### External Support

- **AWS Comprehend Medical:** https://aws.amazon.com/comprehend/medical/support/
- **OpenAI API:** https://help.openai.com/
- **Stripe:** https://support.stripe.com/
- **PostgreSQL:** https://www.postgresql.org/support/

### Emergency Contacts

- **On-Call Engineer:** Check PagerDuty rotation
- **Security Incidents:** security@revrx.com
- **HIPAA Compliance Officer:** compliance@revrx.com

---

## Document Information

**Version:** 1.0
**Last Updated:** 2025-09-30
**Author:** RevRX Engineering Team
**Review Cycle:** Quarterly

**Contribution Guidelines:**
- Add new issues as they are discovered and resolved
- Include actual error messages and stack traces
- Provide working code examples
- Update document version when making significant changes

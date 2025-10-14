# Disaster Recovery Plan

This document outlines the disaster recovery (DR) procedures for the RevRx application, ensuring business continuity in case of system failures, data loss, or security incidents.

## Table of Contents

1. [Overview](#overview)
2. [Backup Strategy](#backup-strategy)
3. [Recovery Procedures](#recovery-procedures)
4. [RTO and RPO](#rto-and-rpo)
5. [Incident Response](#incident-response)
6. [Testing and Validation](#testing-and-validation)

## Overview

### Scope

This DR plan covers:
- Database backup and restoration
- Application deployment recovery
- Infrastructure recovery
- Data integrity verification
- Security incident response

### Roles and Responsibilities

| Role | Responsibility | Contact |
|------|---------------|---------|
| Incident Commander | Overall incident coordination | On-call rotation |
| DevOps Lead | Infrastructure and deployment | devops@revrx.com |
| Database Administrator | Database recovery | dba@revrx.com |
| Security Officer | Security incidents | security@revrx.com |
| Engineering Manager | Technical decisions | engineering@revrx.com |

## Backup Strategy

### Database Backups

#### Automated Backups

1. **RDS Automated Backups** (Production)
   - Frequency: Daily snapshots
   - Retention: 30 days
   - Point-in-time recovery: Enabled (5-minute granularity)
   - Multi-AZ: Enabled for high availability

2. **Manual pg_dump Backups**
   - Frequency: Before each deployment
   - Retention: 90 days in S3
   - Location: `s3://revrx-backups/database/`

#### Backup Script

```bash
#!/bin/bash
# backup-database.sh

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="revrx-backup-${TIMESTAMP}.sql"
S3_BUCKET="revrx-backups"

# For Kubernetes deployment
kubectl exec deployment/postgres -n revrx -- \
  pg_dump -U revrx -F c revrx_db > "/tmp/${BACKUP_FILE}"

# Compress
gzip "/tmp/${BACKUP_FILE}"

# Upload to S3
aws s3 cp "/tmp/${BACKUP_FILE}.gz" \
  "s3://${S3_BUCKET}/database/${BACKUP_FILE}.gz" \
  --server-side-encryption AES256

# Verify upload
aws s3 ls "s3://${S3_BUCKET}/database/${BACKUP_FILE}.gz"

# Clean up
rm "/tmp/${BACKUP_FILE}.gz"

echo "Backup completed: ${BACKUP_FILE}.gz"
```

#### CronJob for Automated Backups

```yaml
# k8s/cronjobs/database-backup.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: revrx
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM UTC
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 7
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
          - name: backup
            image: postgres:16-alpine
            command:
            - /bin/sh
            - -c
            - |
              TIMESTAMP=$(date +%Y%m%d-%H%M%S)
              BACKUP_FILE="revrx-backup-${TIMESTAMP}.sql"

              pg_dump -h postgres -U revrx -F c revrx_db > "/tmp/${BACKUP_FILE}"
              gzip "/tmp/${BACKUP_FILE}"

              aws s3 cp "/tmp/${BACKUP_FILE}.gz" \
                "s3://revrx-backups/database/${BACKUP_FILE}.gz" \
                --server-side-encryption AES256
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: password
            - name: AWS_ACCESS_KEY_ID
              valueFrom:
                secretKeyRef:
                  name: aws-secret
                  key: access-key-id
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: aws-secret
                  key: secret-access-key
```

### Application Backups

#### Docker Images
- All images tagged and pushed to GitHub Container Registry
- Retention: All production tags kept indefinitely
- Staging tags: 30 days

#### Configuration Backups
- Kubernetes manifests: Version controlled in git
- Secrets: Sealed secrets stored in git (encrypted)
- Infrastructure as Code: Terraform state in S3 with versioning

### File Storage Backups (S3)

- Versioning: Enabled on all production buckets
- Cross-region replication: Enabled for critical data
- Lifecycle policies:
  - Standard storage: Current versions
  - Standard-IA: Non-current versions after 30 days
  - Glacier: Non-current versions after 90 days
  - Delete: Non-current versions after 365 days

## Recovery Procedures

### Database Recovery

#### Scenario 1: Data Corruption (Recent)

Recovery from automated RDS backup:

```bash
# 1. Identify the corruption time
RESTORE_TIME="2024-01-15T14:30:00Z"

# 2. Create a new RDS instance from backup
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier revrx-production \
  --target-db-instance-identifier revrx-production-restored \
  --restore-time ${RESTORE_TIME}

# 3. Wait for restoration to complete
aws rds wait db-instance-available \
  --db-instance-identifier revrx-production-restored

# 4. Update application connection string
kubectl set env deployment/backend -n revrx \
  DATABASE_URL="postgresql://user:pass@restored-endpoint:5432/revrx_db"

# 5. Verify data integrity
kubectl exec -it deployment/backend -n revrx -- \
  python scripts/verify_data_integrity.py

# 6. If verified, promote restored instance
# Update DNS or swap endpoints as needed
```

**Estimated Recovery Time**: 15-30 minutes

#### Scenario 2: Complete Database Loss

Recovery from S3 backup:

```bash
# 1. Download latest backup
LATEST_BACKUP=$(aws s3 ls s3://revrx-backups/database/ | sort | tail -n 1 | awk '{print $4}')
aws s3 cp "s3://revrx-backups/database/${LATEST_BACKUP}" .

# 2. Decompress
gunzip "${LATEST_BACKUP}"

# 3. Create new database instance (if needed)
# Via RDS console or Terraform

# 4. Restore backup
kubectl run -it --rm restore --image=postgres:16-alpine --restart=Never -n revrx -- \
  pg_restore -h <new-db-host> -U revrx -d revrx_db -F c "/backup/${BACKUP_FILE}"

# 5. Run any missing migrations
kubectl exec -it deployment/backend -n revrx -- \
  prisma migrate deploy

# 6. Verify data integrity
kubectl exec -it deployment/backend -n revrx -- \
  python scripts/verify_data_integrity.py

# 7. Update application to use new database
kubectl set env deployment/backend -n revrx \
  DATABASE_URL="postgresql://user:pass@new-endpoint:5432/revrx_db"
```

**Estimated Recovery Time**: 1-2 hours

### Application Recovery

#### Scenario 1: Bad Deployment

```bash
# 1. Identify issue
kubectl get pods -n revrx
kubectl logs deployment/backend -n revrx

# 2. Rollback to previous version
kubectl rollout undo deployment/backend -n revrx
kubectl rollout undo deployment/frontend -n revrx
kubectl rollout undo deployment/celery-worker -n revrx

# 3. Wait for rollback to complete
kubectl rollout status deployment/backend -n revrx
kubectl rollout status deployment/frontend -n revrx
kubectl rollout status deployment/celery-worker -n revrx

# 4. Verify services
curl -f https://api.revrx.com/health
curl -f https://app.revrx.com/api/health

# 5. Notify stakeholders
./scripts/notify-incident.sh "Deployment rolled back successfully"
```

**Estimated Recovery Time**: 5-10 minutes

#### Scenario 2: Complete Cluster Failure

```bash
# 1. Create new cluster (via Terraform or console)
cd terraform/production
terraform apply

# 2. Configure kubectl
aws eks update-kubeconfig --name revrx-production-new --region us-east-1

# 3. Install required controllers
./scripts/install-controllers.sh

# 4. Restore secrets
kubectl apply -f k8s/base/sealed-secrets/

# 5. Deploy application
kubectl apply -k k8s/overlays/production

# 6. Verify all services
kubectl get pods -n revrx
kubectl get ingress -n revrx

# 7. Update DNS to point to new cluster
# Via Route53 or your DNS provider

# 8. Verify traffic flow
curl -f https://api.revrx.com/health
curl -f https://app.revrx.com/api/health
```

**Estimated Recovery Time**: 30-60 minutes

### File Storage Recovery

#### Scenario: Accidental S3 Object Deletion

```bash
# 1. List deleted objects
aws s3api list-object-versions \
  --bucket revrx-production-uploads \
  --prefix "encounters/" \
  --query 'DeleteMarkers[?IsLatest==`true`]'

# 2. Restore specific object
aws s3api delete-object \
  --bucket revrx-production-uploads \
  --key "encounters/12345/note.pdf" \
  --version-id <delete-marker-version-id>

# 3. Verify restoration
aws s3 ls s3://revrx-production-uploads/encounters/12345/
```

#### Scenario: Complete Bucket Loss

```bash
# 1. Create new bucket
aws s3 mb s3://revrx-production-uploads-restored

# 2. Restore from cross-region replica
aws s3 sync \
  s3://revrx-production-uploads-replica \
  s3://revrx-production-uploads-restored

# 3. Update application configuration
kubectl set env deployment/backend -n revrx \
  S3_BUCKET_NAME="revrx-production-uploads-restored"

# 4. Verify file access
curl -f https://api.revrx.com/api/v1/files/test
```

## RTO and RPO

### Recovery Time Objective (RTO)

Maximum acceptable downtime:

| Component | RTO | Notes |
|-----------|-----|-------|
| Frontend | 5 minutes | Rollback or redeploy |
| Backend API | 5 minutes | Rollback or redeploy |
| Database (RDS) | 15 minutes | Point-in-time recovery |
| Database (S3 backup) | 2 hours | Full restore from backup |
| Complete Infrastructure | 1 hour | New cluster + deployment |

### Recovery Point Objective (RPO)

Maximum acceptable data loss:

| Component | RPO | Notes |
|-----------|-----|-------|
| Database | 5 minutes | RDS PITR granularity |
| File Storage | 0 | S3 versioning enabled |
| Application State | 0 | Stateless applications |

## Incident Response

### Severity Levels

| Level | Description | Response Time | Escalation |
|-------|-------------|--------------|------------|
| P0 | Complete outage | Immediate | All hands |
| P1 | Major functionality down | 15 minutes | On-call + Manager |
| P2 | Partial functionality impact | 1 hour | On-call engineer |
| P3 | Minor issues | 4 hours | Standard support |

### Response Workflow

1. **Detection**
   - Monitoring alerts
   - User reports
   - Automated health checks

2. **Assessment**
   - Determine severity
   - Identify affected components
   - Estimate impact

3. **Communication**
   - Notify stakeholders
   - Create status page update
   - Update incident channel

4. **Mitigation**
   - Follow recovery procedures
   - Document actions taken
   - Monitor progress

5. **Resolution**
   - Verify services restored
   - Update status page
   - Close incident ticket

6. **Post-Mortem**
   - Write incident report
   - Identify root cause
   - Create action items

### Communication Templates

#### Initial Alert
```
🚨 INCIDENT DETECTED 🚨

Severity: P0
Component: Backend API
Impact: Complete outage
Start Time: 2024-01-15 14:30 UTC

Incident Commander: @john
Status: Investigating

Updates will follow every 15 minutes.
```

#### Update
```
📊 INCIDENT UPDATE

Status: Mitigating
Action: Rolling back to v1.2.3
ETA: 5 minutes

Next update: 14:50 UTC
```

#### Resolution
```
✅ INCIDENT RESOLVED

Duration: 23 minutes
Root Cause: Bad deployment (database migration issue)
Resolution: Rollback to previous version

Post-mortem: Will be published within 24 hours
```

## Testing and Validation

### DR Drill Schedule

| Test Type | Frequency | Participants |
|-----------|-----------|--------------|
| Database restore | Quarterly | DBA, DevOps |
| Application rollback | Monthly | DevOps |
| Complete DR simulation | Annually | All teams |
| Security incident response | Bi-annually | Security, DevOps |

### Test Checklist

#### Database Restore Test

- [ ] Restore RDS snapshot to test instance
- [ ] Restore S3 backup to test instance
- [ ] Verify data integrity
- [ ] Test application connectivity
- [ ] Measure restoration time
- [ ] Document any issues
- [ ] Clean up test resources

#### Application Recovery Test

- [ ] Deploy to test environment
- [ ] Simulate bad deployment
- [ ] Perform rollback
- [ ] Verify services
- [ ] Measure recovery time
- [ ] Document any issues

#### Full DR Simulation

- [ ] Announce planned DR drill
- [ ] Simulate complete outage
- [ ] Follow all recovery procedures
- [ ] Time each step
- [ ] Test communication channels
- [ ] Verify full restoration
- [ ] Conduct post-drill review
- [ ] Update procedures based on findings

### Validation Scripts

```bash
# scripts/verify-backup.sh
#!/bin/bash
# Verify database backup integrity

BACKUP_FILE=$1

echo "Verifying backup: ${BACKUP_FILE}"

# Download backup
aws s3 cp "s3://revrx-backups/database/${BACKUP_FILE}" .

# Decompress
gunzip "${BACKUP_FILE}"

# Test restore to temporary database
docker run -d --name test-postgres -e POSTGRES_PASSWORD=test postgres:16-alpine
sleep 10

docker exec -i test-postgres psql -U postgres -c "CREATE DATABASE test_restore;"
cat "${BACKUP_FILE%.gz}" | docker exec -i test-postgres pg_restore -U postgres -d test_restore

# Verify table count
TABLES=$(docker exec test-postgres psql -U postgres -d test_restore -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

echo "Tables restored: ${TABLES}"

# Cleanup
docker stop test-postgres
docker rm test-postgres
rm "${BACKUP_FILE%.gz}"

if [ "$TABLES" -gt 0 ]; then
  echo "✅ Backup verification successful"
  exit 0
else
  echo "❌ Backup verification failed"
  exit 1
fi
```

## Contact Information

### Emergency Contacts

| Name | Role | Phone | Email |
|------|------|-------|-------|
| On-Call Rotation | Primary | +1-XXX-XXX-XXXX | oncall@revrx.com |
| DevOps Lead | Escalation | +1-XXX-XXX-XXXX | devops-lead@revrx.com |
| CTO | Executive | +1-XXX-XXX-XXXX | cto@revrx.com |

### Vendor Support

| Vendor | Support Level | Contact | SLA |
|--------|--------------|---------|-----|
| AWS | Enterprise | AWS Console | 15 min |
| OpenAI | Premium | support@openai.com | 1 hour |
| GitHub | Enterprise | Enterprise support | 4 hours |

## Appendix

### A. Backup Retention Policy

- Database backups: 30 days (automated), 90 days (manual)
- Application logs: 90 days
- Audit logs: 7 years (HIPAA compliance)
- File uploads: Per data retention policy (configurable)

### B. Compliance Requirements

This DR plan addresses:
- HIPAA disaster recovery requirements
- Business continuity planning
- Data integrity and availability
- Audit trail maintenance

### C. Related Documents

- [Environment Setup Guide](environment-setup.md)
- [Kubernetes Deployment Guide](../../k8s/README.md)
- [Security Incident Response Plan](../security/incident-response.md)
- [HIPAA Compliance Documentation](../compliance/hipaa-checklist.md)

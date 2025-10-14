# Deployment Procedures

This document provides step-by-step procedures for deploying the RevRx application across different environments.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Development Deployment](#development-deployment)
3. [Staging Deployment](#staging-deployment)
4. [Production Deployment](#production-deployment)
5. [Hotfix Deployment](#hotfix-deployment)
6. [Rollback Procedures](#rollback-procedures)
7. [Post-Deployment Verification](#post-deployment-verification)

## Pre-Deployment Checklist

### For All Environments

- [ ] All tests passing (unit, integration)
- [ ] Code review completed and approved
- [ ] Security scan completed (no critical vulnerabilities)
- [ ] Database migrations reviewed
- [ ] Environment variables documented
- [ ] Monitoring and alerts configured
- [ ] Rollback plan prepared
- [ ] Communication plan ready

### For Production Only

- [ ] Change request approved
- [ ] Database backup completed
- [ ] Maintenance window scheduled (if required)
- [ ] Stakeholders notified
- [ ] On-call engineer available
- [ ] Performance benchmarks established
- [ ] Load testing completed
- [ ] Security audit passed

## Development Deployment

### Local Development with Docker Compose

```bash
# 1. Clone the repository
git clone https://github.com/your-org/revrx.git
cd revrx

# 2. Set up environment variables
cd backend
cp .env.example .env
# Edit .env with your local configuration

# 3. Start services
docker-compose up -d

# 4. Run database migrations
docker-compose exec backend prisma migrate dev

# 5. (Optional) Seed database
docker-compose exec backend prisma db seed

# 6. Verify services
docker-compose ps
curl http://localhost:8000/health
```

### Frontend Development Server

```bash
# 1. Install dependencies
npm install

# 2. Set up environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# 3. Start development server
npm run dev

# 4. Access application
# Open http://localhost:3000 in your browser
```

### Stopping Development Environment

```bash
# Stop all services
cd backend
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

## Staging Deployment

Staging deployments are triggered automatically when code is merged to the `develop` branch.

### Manual Staging Deployment

```bash
# 1. Ensure you're on the develop branch
git checkout develop
git pull origin develop

# 2. Configure kubectl for staging
aws eks update-kubeconfig --name revrx-staging --region us-east-1

# 3. Verify cluster access
kubectl get nodes
kubectl get pods -n revrx-staging

# 4. Build and push Docker images (if not using CI/CD)
docker build -t ghcr.io/your-org/revrx/backend:staging-$(git rev-parse --short HEAD) ./backend
docker build -t ghcr.io/your-org/revrx/frontend:staging-$(git rev-parse --short HEAD) .
docker push ghcr.io/your-org/revrx/backend:staging-$(git rev-parse --short HEAD)
docker push ghcr.io/your-org/revrx/frontend:staging-$(git rev-parse --short HEAD)

# 5. Update Kustomize image tags
cd k8s/overlays/staging
kustomize edit set image \
  revrx-backend=ghcr.io/your-org/revrx/backend:staging-$(git rev-parse --short HEAD) \
  revrx-frontend=ghcr.io/your-org/revrx/frontend:staging-$(git rev-parse --short HEAD)

# 6. Deploy to staging
kubectl apply -k k8s/overlays/staging

# 7. Monitor deployment
kubectl rollout status deployment/backend-staging -n revrx-staging
kubectl rollout status deployment/frontend-staging -n revrx-staging
kubectl rollout status deployment/celery-worker-staging -n revrx-staging

# 8. Verify deployment
kubectl get pods -n revrx-staging
kubectl get ingress -n revrx-staging

# 9. Run smoke tests
curl -f https://api-staging.revrx.example.com/health
curl -f https://staging.revrx.example.com/api/health

# 10. Check logs for errors
kubectl logs -f deployment/backend-staging -n revrx-staging --tail=50
kubectl logs -f deployment/frontend-staging -n revrx-staging --tail=50
```

### Database Migrations in Staging

```bash
# 1. Review migration files
cat backend/prisma/migrations/*/migration.sql

# 2. Run migrations
kubectl exec -it deployment/backend-staging -n revrx-staging -- \
  prisma migrate deploy

# 3. Verify migration success
kubectl logs deployment/backend-staging -n revrx-staging | grep -i migration
```

### Staging Environment Testing

```bash
# 1. Run integration tests
npm run test:integration -- --env=staging

# 2. Run E2E tests
npm run test:e2e -- --baseUrl=https://staging.revrx.example.com

# 3. Manual testing checklist
# - User registration
# - File upload
# - Report generation
# - Payment flow
```

## Production Deployment

Production deployments can be triggered by:
1. Creating a git tag (e.g., `v1.0.0`)
2. Manual workflow dispatch

### Pre-Production Steps

```bash
# 1. Ensure all staging tests pass
npm run test:integration -- --env=staging
npm run test:e2e -- --baseUrl=https://staging.revrx.example.com

# 2. Create and push a release tag
git checkout main
git pull origin main
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# This will trigger the production deployment workflow
```

### Manual Production Deployment

```bash
# 1. Configure kubectl for production
aws eks update-kubeconfig --name revrx-production --region us-east-1

# 2. Verify cluster access
kubectl get nodes
kubectl get pods -n revrx

# 3. Create pre-deployment backup
kubectl exec deployment/postgres -n revrx -- \
  pg_dump -U revrx revrx_db > backup-pre-deploy-$(date +%Y%m%d-%H%M%S).sql

# 4. Upload backup to S3
aws s3 cp backup-pre-deploy-*.sql s3://revrx-backups/pre-deploy/

# 5. Review what will be deployed
kubectl diff -k k8s/overlays/production

# 6. Build and push Docker images (if not using CI/CD)
VERSION=v1.0.0
docker build -t ghcr.io/your-org/revrx/backend:${VERSION} ./backend
docker build -t ghcr.io/your-org/revrx/frontend:${VERSION} .
docker push ghcr.io/your-org/revrx/backend:${VERSION}
docker push ghcr.io/your-org/revrx/frontend:${VERSION}

# 7. Update Kustomize image tags
cd k8s/overlays/production
kustomize edit set image \
  revrx-backend=ghcr.io/your-org/revrx/backend:${VERSION} \
  revrx-frontend=ghcr.io/your-org/revrx/frontend:${VERSION}

# 8. Deploy to production
kubectl apply -k k8s/overlays/production

# 9. Monitor deployment (should take 5-10 minutes)
watch kubectl get pods -n revrx

# 10. Wait for rollout to complete
kubectl rollout status deployment/backend -n revrx --timeout=10m
kubectl rollout status deployment/frontend -n revrx --timeout=10m
kubectl rollout status deployment/celery-worker -n revrx --timeout=10m

# 11. Verify deployment
kubectl get pods -n revrx
kubectl get ingress -n revrx

# 12. Run smoke tests
curl -f https://api.revrx.com/health
curl -f https://app.revrx.com/api/health

# 13. Monitor application logs
kubectl logs -f deployment/backend -n revrx --tail=100
kubectl logs -f deployment/frontend -n revrx --tail=100

# 14. Check error rates in monitoring
# Access Grafana/CloudWatch dashboards

# 15. Notify stakeholders
# Send deployment notification via Slack/email
```

### Database Migrations in Production

```bash
# IMPORTANT: Always create a backup before running migrations

# 1. Create backup
kubectl exec deployment/postgres -n revrx -- \
  pg_dump -U revrx -F c revrx_db > backup-pre-migration-$(date +%Y%m%d-%H%M%S).sql
aws s3 cp backup-pre-migration-*.sql s3://revrx-backups/pre-migration/

# 2. Review migration files
cat backend/prisma/migrations/*/migration.sql

# 3. Test migration on staging first
kubectl exec -it deployment/backend-staging -n revrx-staging -- \
  prisma migrate deploy

# 4. If staging successful, run on production
kubectl exec -it deployment/backend -n revrx -- \
  prisma migrate deploy

# 5. Verify migration success
kubectl logs deployment/backend -n revrx | grep -i migration

# 6. Verify data integrity
kubectl exec -it deployment/backend -n revrx -- \
  python scripts/verify_data_integrity.py
```

## Hotfix Deployment

For critical production issues requiring immediate fixes.

### Hotfix Process

```bash
# 1. Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug-fix

# 2. Make the fix
# Edit necessary files

# 3. Test locally
npm test
npm run build

# 4. Commit and push
git add .
git commit -m "hotfix: Fix critical bug XYZ"
git push origin hotfix/critical-bug-fix

# 5. Create pull request
# Get expedited review and approval

# 6. Merge to main
git checkout main
git pull origin main

# 7. Create hotfix tag
git tag -a v1.0.1 -m "Hotfix: Critical bug fix"
git push origin v1.0.1

# 8. Deploy immediately (using manual workflow)
gh workflow run deploy-production.yaml --ref v1.0.1

# 9. Monitor deployment closely
kubectl logs -f deployment/backend -n revrx

# 10. Verify fix in production
# Test the specific issue that was fixed

# 11. Merge hotfix back to develop
git checkout develop
git merge main
git push origin develop
```

### Emergency Hotfix (Bypass CI/CD)

Only use in extreme emergencies when CI/CD is unavailable:

```bash
# 1. Build images locally
docker build -t ghcr.io/your-org/revrx/backend:hotfix-$(date +%s) ./backend
docker push ghcr.io/your-org/revrx/backend:hotfix-$(date +%s)

# 2. Update deployment directly
kubectl set image deployment/backend backend=ghcr.io/your-org/revrx/backend:hotfix-$(date +%s) -n revrx

# 3. Monitor rollout
kubectl rollout status deployment/backend -n revrx

# 4. Create proper release afterward
# Follow standard hotfix process to document the change
```

## Rollback Procedures

### Quick Rollback (Last Deployment)

```bash
# 1. Rollback deployment
kubectl rollout undo deployment/backend -n revrx
kubectl rollout undo deployment/frontend -n revrx
kubectl rollout undo deployment/celery-worker -n revrx

# 2. Wait for rollback to complete
kubectl rollout status deployment/backend -n revrx
kubectl rollout status deployment/frontend -n revrx
kubectl rollout status deployment/celery-worker -n revrx

# 3. Verify services
curl -f https://api.revrx.com/health
curl -f https://app.revrx.com/api/health

# 4. Notify stakeholders
# Send rollback notification
```

### Rollback to Specific Version

```bash
# 1. View deployment history
kubectl rollout history deployment/backend -n revrx

# 2. Check specific revision
kubectl rollout history deployment/backend -n revrx --revision=3

# 3. Rollback to specific revision
kubectl rollout undo deployment/backend -n revrx --to-revision=3
kubectl rollout undo deployment/frontend -n revrx --to-revision=3

# 4. Wait for rollback
kubectl rollout status deployment/backend -n revrx
```

### Database Rollback

```bash
# 1. If migration needs to be reversed
# First, restore database backup
aws s3 cp s3://revrx-backups/pre-migration/backup-pre-migration-TIMESTAMP.sql .

# 2. Stop application
kubectl scale deployment backend --replicas=0 -n revrx

# 3. Restore database
kubectl exec -i deployment/postgres -n revrx -- \
  psql -U revrx revrx_db < backup-pre-migration-TIMESTAMP.sql

# 4. Restart application
kubectl scale deployment backend --replicas=2 -n revrx

# 5. Verify restoration
kubectl exec -it deployment/backend -n revrx -- \
  python scripts/verify_data_integrity.py
```

## Post-Deployment Verification

### Automated Checks

```bash
# 1. Health checks
curl -f https://api.revrx.com/health || echo "Backend health check failed"
curl -f https://app.revrx.com/api/health || echo "Frontend health check failed"

# 2. API functionality
curl -X POST https://api.revrx.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test"}' \
  || echo "API login failed"

# 3. Database connectivity
kubectl exec -it deployment/backend -n revrx -- \
  python -c "from app.db import database; print('DB connected' if database.is_connected else 'DB failed')"

# 4. Cache connectivity
kubectl exec -it deployment/backend -n revrx -- \
  redis-cli -h redis ping
```

### Manual Verification Checklist

- [ ] Application loads successfully
- [ ] User can register/login
- [ ] File upload works
- [ ] Report generation works
- [ ] Payment processing works
- [ ] Email notifications work
- [ ] Background jobs processing
- [ ] No error spikes in logs
- [ ] Response times normal
- [ ] Database queries performing well

### Monitoring Dashboard Checks

1. **Application Metrics**
   - Request rate
   - Error rate (should be < 1%)
   - Response time (p95, p99)
   - Active users

2. **Infrastructure Metrics**
   - CPU usage (should be < 70%)
   - Memory usage (should be < 80%)
   - Disk usage
   - Network I/O

3. **Database Metrics**
   - Connection count
   - Query performance
   - Replication lag (if applicable)
   - Cache hit rate

4. **Business Metrics**
   - Successful uploads
   - Report generation time
   - Payment success rate
   - User satisfaction

### Post-Deployment Communication

```markdown
# Production Deployment Completed

**Version**: v1.0.0
**Deployed By**: @engineer
**Deployment Time**: 2024-01-15 14:30 UTC
**Duration**: 12 minutes

## Changes Deployed
- New feature: XYZ
- Bug fix: ABC
- Performance improvement: DEF

## Verification
- ✅ All health checks passing
- ✅ Smoke tests completed
- ✅ No error spikes detected
- ✅ Performance metrics normal

## Rollback Plan
If issues arise: `kubectl rollout undo deployment/backend -n revrx`

## Monitoring
- Logs: kubectl logs -f deployment/backend -n revrx
- Metrics: https://grafana.revrx.com/d/production
- Alerts: #ops-alerts Slack channel
```

## Troubleshooting Common Issues

### Deployment Stuck

```bash
# Check pod status
kubectl get pods -n revrx

# Describe problematic pod
kubectl describe pod <pod-name> -n revrx

# Check events
kubectl get events -n revrx --sort-by='.lastTimestamp'

# Force delete stuck pod
kubectl delete pod <pod-name> -n revrx --force --grace-period=0
```

### Image Pull Errors

```bash
# Check if image exists
docker pull ghcr.io/your-org/revrx/backend:v1.0.0

# Check imagePullSecrets
kubectl get secret -n revrx | grep docker

# Recreate image pull secret if needed
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=YOUR_USERNAME \
  --docker-password=YOUR_TOKEN \
  -n revrx
```

### Database Connection Errors

```bash
# Check if postgres is running
kubectl get pods -n revrx | grep postgres

# Test database connectivity
kubectl run -it --rm debug --image=postgres:16-alpine --restart=Never -n revrx -- \
  psql -h postgres -U revrx -d revrx_db

# Check database logs
kubectl logs deployment/postgres -n revrx
```

### High Memory Usage

```bash
# Check memory usage
kubectl top pods -n revrx

# Increase memory limits if needed
kubectl set resources deployment backend \
  --limits=memory=4Gi \
  -n revrx

# Or scale horizontally
kubectl scale deployment backend --replicas=5 -n revrx
```

## Related Documentation

- [Environment Setup Guide](environment-setup.md)
- [Disaster Recovery Plan](disaster-recovery.md)
- [Kubernetes Deployment Guide](../../k8s/README.md)
- [Monitoring and Alerting](../operations/monitoring.md)

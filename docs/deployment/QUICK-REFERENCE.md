# Quick Reference Guide

Common commands and procedures for day-to-day operations.

## Local Development

```bash
# Start all services
cd backend && docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f backend

# Run migrations
docker-compose exec backend prisma migrate dev

# Access database
docker-compose exec postgres psql -U revrx -d revrx_db

# Rebuild after code changes
docker-compose up -d --build backend
```

## Kubernetes Operations

### Context Switching

```bash
# Staging
aws eks update-kubeconfig --name revrx-staging --region us-east-1

# Production
aws eks update-kubeconfig --name revrx-production --region us-east-1
```

### Viewing Resources

```bash
# All pods
kubectl get pods -n revrx

# All deployments
kubectl get deployments -n revrx

# All services
kubectl get svc -n revrx

# Ingress
kubectl get ingress -n revrx

# HPA status
kubectl get hpa -n revrx
```

### Logs

```bash
# Backend logs (follow)
kubectl logs -f deployment/backend -n revrx

# Frontend logs (follow)
kubectl logs -f deployment/frontend -n revrx

# Worker logs (follow)
kubectl logs -f deployment/celery-worker -n revrx

# Last 100 lines
kubectl logs deployment/backend -n revrx --tail=100

# Logs from specific pod
kubectl logs <pod-name> -n revrx

# Previous pod logs (after crash)
kubectl logs <pod-name> -n revrx --previous
```

### Scaling

```bash
# Scale backend
kubectl scale deployment backend --replicas=5 -n revrx

# Scale workers
kubectl scale deployment celery-worker --replicas=10 -n revrx

# View HPA status
kubectl describe hpa backend-hpa -n revrx
```

### Rollback

```bash
# Quick rollback
kubectl rollout undo deployment/backend -n revrx

# View history
kubectl rollout history deployment/backend -n revrx

# Rollback to specific revision
kubectl rollout undo deployment/backend --to-revision=3 -n revrx

# Check rollout status
kubectl rollout status deployment/backend -n revrx
```

### Debugging

```bash
# Describe pod
kubectl describe pod <pod-name> -n revrx

# Get events
kubectl get events -n revrx --sort-by='.lastTimestamp'

# Execute command in pod
kubectl exec -it deployment/backend -n revrx -- /bin/sh

# Port forward for debugging
kubectl port-forward svc/backend 8000:8000 -n revrx
```

## Database Operations

### Backups

```bash
# Manual backup
kubectl exec deployment/postgres -n revrx -- \
  pg_dump -U revrx revrx_db > backup-$(date +%Y%m%d).sql

# Upload to S3
aws s3 cp backup-*.sql s3://revrx-backups/manual/

# Trigger automated backup job
kubectl create job --from=cronjob/postgres-backup manual-backup-$(date +%s) -n revrx
```

### Restore

```bash
# Download backup
aws s3 cp s3://revrx-backups/database/backup-20240115.sql.gz .
gunzip backup-20240115.sql.gz

# Restore
kubectl exec -i deployment/postgres -n revrx -- \
  psql -U revrx revrx_db < backup-20240115.sql
```

### Migrations

```bash
# Run migrations
kubectl exec -it deployment/backend -n revrx -- \
  prisma migrate deploy

# Check migration status
kubectl exec -it deployment/backend -n revrx -- \
  prisma migrate status
```

## Deployments

### Staging

```bash
# Deploy
kubectl apply -k k8s/overlays/staging

# Watch rollout
watch kubectl get pods -n revrx-staging

# Verify
curl -f https://api-staging.revrx.example.com/health
```

### Production

```bash
# Create backup first!
kubectl exec deployment/postgres -n revrx -- \
  pg_dump -U revrx revrx_db > backup-pre-deploy-$(date +%Y%m%d-%H%M%S).sql

# Deploy
kubectl apply -k k8s/overlays/production

# Monitor
kubectl rollout status deployment/backend -n revrx

# Verify
curl -f https://api.revrx.com/health
```

## CI/CD

### GitHub Actions

```bash
# View workflow runs
gh run list

# View specific run
gh run view <run-id>

# Watch run
gh run watch

# Re-run failed jobs
gh run rerun <run-id>

# Trigger manual deployment
gh workflow run deploy-production.yaml --ref v1.0.0
```

## Monitoring

### Health Checks

```bash
# Backend health
curl https://api.revrx.com/health

# Frontend health
curl https://app.revrx.com/api/health

# Check all endpoints
for url in api.revrx.com app.revrx.com; do
  echo "Checking $url..."
  curl -f https://$url/health && echo "✓" || echo "✗"
done
```

### Resource Usage

```bash
# Pod resource usage
kubectl top pods -n revrx

# Node resource usage
kubectl top nodes

# Detailed pod info
kubectl describe pod <pod-name> -n revrx | grep -A 5 Resources
```

## Secrets Management

### Create Sealed Secret

```bash
# Create secret
kubectl create secret generic my-secret \
  --from-literal=key=value \
  --dry-run=client -o yaml > secret.yaml

# Seal it
kubeseal --format=yaml < secret.yaml > sealed-secret.yaml

# Apply sealed secret
kubectl apply -f sealed-secret.yaml

# Clean up
rm secret.yaml
```

### Update Secret

```bash
# Delete old sealed secret
kubectl delete sealedsecret my-secret -n revrx

# Create new sealed secret (see above)

# Restart pods to pick up new secret
kubectl rollout restart deployment/backend -n revrx
```

## Troubleshooting

### Pod not starting

```bash
kubectl describe pod <pod-name> -n revrx
kubectl logs <pod-name> -n revrx
kubectl get events -n revrx --sort-by='.lastTimestamp'
```

### Image pull errors

```bash
# Check image exists
docker pull ghcr.io/your-org/revrx/backend:v1.0.0

# Check image pull secrets
kubectl get secret -n revrx | grep docker

# Describe pod for details
kubectl describe pod <pod-name> -n revrx | grep -A 5 "Failed to pull"
```

### Database connection errors

```bash
# Test connectivity
kubectl run -it --rm debug --image=postgres:16-alpine --restart=Never -n revrx -- \
  psql -h postgres -U revrx -d revrx_db

# Check postgres pod
kubectl get pod -n revrx | grep postgres
kubectl logs deployment/postgres -n revrx
```

### High CPU/Memory

```bash
# Check resource usage
kubectl top pods -n revrx

# Check HPA
kubectl get hpa -n revrx

# Increase limits
kubectl set resources deployment backend \
  --limits=cpu=2000m,memory=4Gi \
  -n revrx

# Or scale horizontally
kubectl scale deployment backend --replicas=5 -n revrx
```

### Ingress not working

```bash
# Check ingress
kubectl describe ingress revrx-ingress -n revrx

# Check ingress controller
kubectl logs -f deployment/ingress-nginx-controller -n ingress-nginx

# Check cert-manager (for TLS)
kubectl get certificate -n revrx
kubectl describe certificate revrx-tls -n revrx
```

## Useful Aliases

Add these to your `~/.bashrc` or `~/.zshrc`:

```bash
# Kubernetes
alias k='kubectl'
alias kgp='kubectl get pods'
alias kgd='kubectl get deployments'
alias kgs='kubectl get svc'
alias kl='kubectl logs -f'
alias kex='kubectl exec -it'
alias kdesc='kubectl describe'

# RevRx specific
alias kprod='aws eks update-kubeconfig --name revrx-production --region us-east-1'
alias kstage='aws eks update-kubeconfig --name revrx-staging --region us-east-1'
alias kpods='kubectl get pods -n revrx'
alias klogs='kubectl logs -f deployment/backend -n revrx'
alias krollback='kubectl rollout undo deployment/backend -n revrx'
```

## Emergency Contacts

| Issue | Contact | Channel |
|-------|---------|---------|
| Production down | On-call engineer | Phone: +1-XXX-XXX-XXXX |
| Security incident | Security team | security@revrx.com |
| Database issues | DBA team | dba@revrx.com |
| Infrastructure | DevOps team | #ops-alerts Slack |

## Common Issues & Solutions

### Issue: Pod CrashLoopBackOff

```bash
# View logs
kubectl logs <pod-name> -n revrx --previous

# Check for resource issues
kubectl describe pod <pod-name> -n revrx

# Check configuration
kubectl get configmap -n revrx
kubectl get secret -n revrx
```

### Issue: Deployment stuck

```bash
# Check rollout status
kubectl rollout status deployment/backend -n revrx

# Force delete stuck pods
kubectl delete pod <pod-name> -n revrx --force --grace-period=0

# Cancel rollout
kubectl rollout undo deployment/backend -n revrx
```

### Issue: High error rate

```bash
# Check logs
kubectl logs -f deployment/backend -n revrx | grep -i error

# Scale up
kubectl scale deployment backend --replicas=5 -n revrx

# Rollback if needed
kubectl rollout undo deployment/backend -n revrx
```

## Quick Links

- **Staging**: https://staging.revrx.example.com
- **Production**: https://app.revrx.com
- **Monitoring**: https://grafana.revrx.com
- **GitHub**: https://github.com/your-org/revrx
- **Documentation**: /docs/deployment/

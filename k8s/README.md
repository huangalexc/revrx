# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying the RevRx application.

## Directory Structure

```
k8s/
├── base/                  # Base Kubernetes resources
│   ├── namespace.yaml
│   ├── *-deployment.yaml
│   ├── *-service.yaml
│   ├── *-hpa.yaml
│   ├── *-pvc.yaml
│   ├── ingress.yaml
│   └── secrets-template.yaml
└── overlays/             # Environment-specific configurations
    ├── staging/
    │   └── kustomization.yaml
    └── production/
        └── kustomization.yaml
```

## Prerequisites

1. **Kubernetes Cluster**: EKS, GKE, or AKS cluster
2. **kubectl**: Version 1.28+
3. **kustomize**: Built into kubectl or standalone
4. **Sealed Secrets** or **External Secrets Operator**: For secrets management
5. **NGINX Ingress Controller**: For ingress
6. **cert-manager**: For TLS certificate management

## Initial Setup

### 1. Install Required Controllers

```bash
# Install NGINX Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.0/deploy/static/provider/cloud/deploy.yaml

# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Install Sealed Secrets
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml
```

### 2. Create Sealed Secrets

```bash
# Install kubeseal CLI
brew install kubeseal  # macOS
# or download from https://github.com/bitnami-labs/sealed-secrets/releases

# Create and seal secrets
kubectl create secret generic postgres-secret \
  --from-literal=username=revrx \
  --from-literal=password=YOUR_PASSWORD \
  --dry-run=client -o yaml | \
  kubeseal --format=yaml > k8s/base/postgres-sealed-secret.yaml

kubectl create secret generic backend-secret \
  --from-literal=database-url=postgresql://USER:PASS@postgres:5432/revrx_db \
  --from-literal=jwt-secret=YOUR_JWT_SECRET \
  --dry-run=client -o yaml | \
  kubeseal --format=yaml > k8s/base/backend-sealed-secret.yaml

kubectl create secret generic aws-secret \
  --from-literal=access-key-id=YOUR_KEY \
  --from-literal=secret-access-key=YOUR_SECRET \
  --from-literal=region=us-east-1 \
  --from-literal=s3-bucket-name=revrx-uploads \
  --dry-run=client -o yaml | \
  kubeseal --format=yaml > k8s/base/aws-sealed-secret.yaml

kubectl create secret generic openai-secret \
  --from-literal=api-key=YOUR_API_KEY \
  --dry-run=client -o yaml | \
  kubeseal --format=yaml > k8s/base/openai-sealed-secret.yaml
```

### 3. Configure cert-manager ClusterIssuer

```bash
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@revrx.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

## Deployment

### Development Environment

```bash
# Use docker-compose for local development
cd backend
docker-compose up -d
```

### Staging Environment

```bash
# Deploy to staging
kubectl apply -k k8s/overlays/staging

# Verify deployment
kubectl get pods -n revrx-staging
kubectl get ingress -n revrx-staging

# Check logs
kubectl logs -f deployment/backend-staging -n revrx-staging
kubectl logs -f deployment/frontend-staging -n revrx-staging
```

### Production Environment

```bash
# Deploy to production
kubectl apply -k k8s/overlays/production

# Verify deployment
kubectl get pods -n revrx
kubectl get ingress -n revrx

# Monitor rollout
kubectl rollout status deployment/backend -n revrx
kubectl rollout status deployment/frontend -n revrx
kubectl rollout status deployment/celery-worker -n revrx
```

## Scaling

### Manual Scaling

```bash
# Scale backend
kubectl scale deployment backend -n revrx --replicas=5

# Scale celery workers
kubectl scale deployment celery-worker -n revrx --replicas=10
```

### Horizontal Pod Autoscaling

HPA is configured automatically. View status:

```bash
kubectl get hpa -n revrx
kubectl describe hpa backend-hpa -n revrx
```

## Database Management

### Migrations

```bash
# Run migrations
kubectl exec -it deployment/backend -n revrx -- \
  prisma migrate deploy
```

### Backups

```bash
# Manual backup
kubectl exec deployment/postgres -n revrx -- \
  pg_dump -U revrx revrx_db > backup-$(date +%Y%m%d-%H%M%S).sql

# Restore from backup
kubectl exec -i deployment/postgres -n revrx -- \
  psql -U revrx revrx_db < backup.sql
```

### Automated Backups

Backups are configured in the CI/CD pipeline and run before each production deployment.

For continuous backups, consider using:
- AWS RDS automated backups (if using RDS)
- Velero for cluster-wide backups
- CronJob for periodic pg_dump

## Monitoring

### View Logs

```bash
# Backend logs
kubectl logs -f deployment/backend -n revrx

# Frontend logs
kubectl logs -f deployment/frontend -n revrx

# Celery worker logs
kubectl logs -f deployment/celery-worker -n revrx

# Database logs
kubectl logs -f deployment/postgres -n revrx
```

### Port Forwarding (for debugging)

```bash
# Access backend directly
kubectl port-forward svc/backend 8000:8000 -n revrx

# Access frontend directly
kubectl port-forward svc/frontend 3000:3000 -n revrx

# Access database
kubectl port-forward svc/postgres 5432:5432 -n revrx
```

## Troubleshooting

### Pod not starting

```bash
# Describe pod
kubectl describe pod <pod-name> -n revrx

# Check events
kubectl get events -n revrx --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> -n revrx --previous
```

### Database connection issues

```bash
# Test database connectivity
kubectl run -it --rm debug --image=postgres:16-alpine --restart=Never -n revrx -- \
  psql -h postgres -U revrx -d revrx_db
```

### Ingress not working

```bash
# Check ingress status
kubectl describe ingress revrx-ingress -n revrx

# Check nginx ingress logs
kubectl logs -f deployment/ingress-nginx-controller -n ingress-nginx
```

### Rollback Deployment

```bash
# View rollout history
kubectl rollout history deployment/backend -n revrx

# Rollback to previous version
kubectl rollout undo deployment/backend -n revrx

# Rollback to specific revision
kubectl rollout undo deployment/backend -n revrx --to-revision=3
```

## Security Best Practices

1. **Secrets**: Always use Sealed Secrets or External Secrets Operator
2. **RBAC**: Implement role-based access control
3. **Network Policies**: Restrict pod-to-pod communication
4. **Pod Security**: Use security contexts and pod security standards
5. **Image Scanning**: Scan images for vulnerabilities before deployment
6. **TLS**: Always use TLS for external communication
7. **Audit Logging**: Enable Kubernetes audit logs

## Resource Limits

Current resource limits per pod:

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---------|------------|-----------|----------------|--------------|
| Backend | 250m | 1000m | 512Mi | 2Gi |
| Frontend | 100m | 500m | 256Mi | 1Gi |
| Celery Worker | 250m | 1000m | 512Mi | 2Gi |
| PostgreSQL | 250m | 1000m | 512Mi | 2Gi |
| Redis | 100m | 500m | 256Mi | 1Gi |

Adjust these based on your workload requirements.

## Disaster Recovery

See [docs/disaster-recovery.md](../docs/disaster-recovery.md) for detailed DR procedures.

Quick recovery steps:
1. Restore database from S3 backup
2. Deploy application using the last known good image tag
3. Verify all services are healthy
4. Restore any lost data from backups

## Cost Optimization

1. Use HPA to scale down during low traffic
2. Use spot instances for worker nodes (except database nodes)
3. Implement pod disruption budgets for graceful scaling
4. Use resource requests/limits efficiently
5. Consider reserved instances for production

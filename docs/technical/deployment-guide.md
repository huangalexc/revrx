# Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Post-Facto Coding Review MVP to production environments. The application can be deployed using Docker containers on Kubernetes or managed platform services.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Database Migration](#database-migration)
6. [SSL/TLS Configuration](#ssltls-configuration)
7. [Monitoring Setup](#monitoring-setup)
8. [Backup Configuration](#backup-configuration)
9. [Rollback Procedures](#rollback-procedures)
10. [Post-Deployment Checklist](#post-deployment-checklist)

---

## Prerequisites

### Required Software
- Docker >= 24.0
- Kubernetes >= 1.28 (kubectl configured)
- Helm >= 3.12
- PostgreSQL >= 15
- Redis >= 7.0
- AWS CLI (for S3/Secrets Manager) or equivalent cloud CLI

### Required Access
- Container registry (Docker Hub, ECR, GCR)
- Cloud provider account (AWS, GCP, Azure)
- Domain name with DNS access
- SSL certificate (Let's Encrypt or commercial CA)

### Required Credentials
- Database credentials
- S3/Object storage credentials
- Stripe API keys
- OpenAI API key
- AWS Comprehend Medical credentials
- Email service credentials (Resend, SendGrid, etc.)

---

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/revrx.git
cd revrx
```

### 2. Create Environment Files

Create separate `.env` files for each environment:

```bash
# Development
cp .env.example .env.development

# Staging
cp .env.example .env.staging

# Production
cp .env.example .env.production
```

See [Environment Variables Documentation](./environment-variables.md) for complete configuration options.

### 3. Configure Secrets

Use a secrets management solution (never commit secrets to Git):

#### Option A: Kubernetes Secrets

```bash
kubectl create secret generic revrx-secrets \
  --from-literal=DATABASE_URL='postgresql://user:pass@host:5432/db' \
  --from-literal=STRIPE_SECRET_KEY='sk_live_...' \
  --from-literal=OPENAI_API_KEY='sk-...' \
  --namespace=production
```

#### Option B: External Secrets Operator (Recommended)

```yaml
# external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: revrx-secrets
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: revrx-secrets
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: prod/revrx/database-url
    - secretKey: STRIPE_SECRET_KEY
      remoteRef:
        key: prod/revrx/stripe-key
```

---

## Docker Deployment

### 1. Build Docker Images

#### Backend Image

```bash
cd backend

docker build \
  -t revrx-backend:latest \
  -t revrx-backend:$(git rev-parse --short HEAD) \
  -f Dockerfile \
  .
```

#### Frontend Image

```bash
cd frontend

docker build \
  -t revrx-frontend:latest \
  -t revrx-frontend:$(git rev-parse --short HEAD) \
  -f Dockerfile \
  --build-arg NEXT_PUBLIC_API_URL=https://api.revrx.com \
  .
```

### 2. Push to Container Registry

```bash
# Docker Hub
docker tag revrx-backend:latest yourusername/revrx-backend:latest
docker push yourusername/revrx-backend:latest

# AWS ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

docker tag revrx-backend:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/revrx-backend:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/revrx-backend:latest
```

### 3. Docker Compose Deployment (Simple/Staging)

```bash
# Use production docker-compose file
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale services
docker-compose -f docker-compose.prod.yml up -d --scale backend=3
```

---

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl create namespace revrx-production
kubectl config set-context --current --namespace=revrx-production
```

### 2. Deploy PostgreSQL (StatefulSet)

```yaml
# postgres-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: revrx-secrets
              key: POSTGRES_PASSWORD
        - name: POSTGRES_DB
          value: revrx
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: encrypted-gp3
      resources:
        requests:
          storage: 100Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
spec:
  ports:
  - port: 5432
  clusterIP: None
  selector:
    app: postgres
```

Apply:

```bash
kubectl apply -f postgres-statefulset.yaml
```

### 3. Deploy Redis

```bash
# Using Helm
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install redis bitnami/redis \
  --set auth.password=$(openssl rand -base64 32) \
  --set master.persistence.size=10Gi \
  --namespace revrx-production
```

### 4. Deploy Backend API

```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: revrx-backend
  labels:
    app: revrx-backend
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: revrx-backend
  template:
    metadata:
      labels:
        app: revrx-backend
    spec:
      containers:
      - name: backend
        image: revrx-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: revrx-secrets
              key: DATABASE_URL
        - name: REDIS_URL
          value: redis://redis-master:6379
        envFrom:
        - secretRef:
            name: revrx-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
---
apiVersion: v1
kind: Service
metadata:
  name: revrx-backend
spec:
  selector:
    app: revrx-backend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

Apply:

```bash
kubectl apply -f backend-deployment.yaml
```

### 5. Deploy Background Workers

```yaml
# worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: revrx-worker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: revrx-worker
  template:
    metadata:
      labels:
        app: revrx-worker
    spec:
      containers:
      - name: worker
        image: revrx-backend:latest
        command: ["celery", "-A", "app.celery_app", "worker", "-l", "info"]
        envFrom:
        - secretRef:
            name: revrx-secrets
        resources:
          requests:
            memory: "1Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "3000m"
```

Apply:

```bash
kubectl apply -f worker-deployment.yaml
```

### 6. Deploy Frontend

```yaml
# frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: revrx-frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: revrx-frontend
  template:
    metadata:
      labels:
        app: revrx-frontend
    spec:
      containers:
      - name: frontend
        image: revrx-frontend:latest
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_API_URL
          value: https://api.revrx.com
        livenessProbe:
          httpGet:
            path: /
            port: 3000
          initialDelaySeconds: 30
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: revrx-frontend
spec:
  selector:
    app: revrx-frontend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 3000
```

Apply:

```bash
kubectl apply -f frontend-deployment.yaml
```

### 7. Configure Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: revrx-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - revrx.com
    - api.revrx.com
    secretName: revrx-tls
  rules:
  - host: revrx.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: revrx-frontend
            port:
              number: 80
  - host: api.revrx.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: revrx-backend
            port:
              number: 80
```

Apply:

```bash
kubectl apply -f ingress.yaml
```

### 8. Horizontal Pod Autoscaler

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: revrx-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: revrx-backend
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

Apply:

```bash
kubectl apply -f hpa.yaml
```

---

## Database Migration

### Run Migrations

```bash
# Connect to backend pod
kubectl exec -it deployment/revrx-backend -- bash

# Inside pod
npx prisma migrate deploy

# Or run as Kubernetes Job
kubectl run prisma-migrate \
  --image=revrx-backend:latest \
  --restart=Never \
  --env="DATABASE_URL=$DATABASE_URL" \
  -- npx prisma migrate deploy
```

### Seed Database (Optional)

```bash
kubectl exec -it deployment/revrx-backend -- npx prisma db seed
```

---

## SSL/TLS Configuration

### Using cert-manager (Recommended)

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
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

Certificates will be automatically provisioned and renewed.

---

## Monitoring Setup

### 1. Install Prometheus & Grafana

```bash
# Add Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.adminPassword='your-secure-password'
```

### 2. Configure Application Metrics

Add Prometheus annotations to deployments:

```yaml
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8000"
    prometheus.io/path: "/metrics"
```

### 3. Set Up Alerting

```yaml
# prometheus-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: revrx-alerts
spec:
  groups:
  - name: revrx
    interval: 30s
    rules:
    - alert: HighErrorRate
      expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
      for: 5m
      annotations:
        summary: "High error rate detected"
    - alert: HighResponseTime
      expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 2
      for: 5m
      annotations:
        summary: "95th percentile response time > 2s"
```

---

## Backup Configuration

### Database Backups

```bash
# Create CronJob for daily backups
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15-alpine
            command:
            - /bin/sh
            - -c
            - |
              pg_dump \$DATABASE_URL | \
              gzip | \
              aws s3 cp - s3://revrx-backups/postgres-\$(date +%Y%m%d-%H%M%S).sql.gz
            envFrom:
            - secretRef:
                name: revrx-secrets
          restartPolicy: OnFailure
EOF
```

### Automated Backup Testing

```bash
# Quarterly backup restoration test
# Create test database
# Restore from backup
# Verify data integrity
# Document results
```

---

## Rollback Procedures

### Kubernetes Rollback

```bash
# View rollout history
kubectl rollout history deployment/revrx-backend

# Rollback to previous version
kubectl rollout undo deployment/revrx-backend

# Rollback to specific revision
kubectl rollout undo deployment/revrx-backend --to-revision=3

# Monitor rollout
kubectl rollout status deployment/revrx-backend
```

### Database Rollback

```bash
# Rollback last migration
npx prisma migrate resolve --rolled-back <migration-name>

# Restore from backup
psql $DATABASE_URL < backup.sql
```

---

## Post-Deployment Checklist

### Functional Verification

- [ ] Health check endpoints responding (GET /health)
- [ ] User registration works
- [ ] User login works
- [ ] File upload works (clinical notes)
- [ ] Billing codes upload works
- [ ] Processing pipeline completes successfully
- [ ] Reports generated correctly
- [ ] Stripe checkout works
- [ ] Email notifications sent
- [ ] Admin dashboard accessible

### Security Verification

- [ ] HTTPS enforced (HTTP redirects to HTTPS)
- [ ] SSL certificate valid
- [ ] HSTS header present
- [ ] CORS configured correctly
- [ ] Rate limiting active
- [ ] WAF rules active
- [ ] Database encrypted at rest
- [ ] S3 bucket encryption enabled
- [ ] PHI de-identification working
- [ ] Audit logs capturing events

### Performance Verification

- [ ] Page load time < 3 seconds
- [ ] API response time < 500ms (p95)
- [ ] Processing time < 30 seconds per encounter
- [ ] Autoscaling working (test load spike)
- [ ] CDN caching static assets
- [ ] Database queries optimized

### Monitoring Verification

- [ ] Prometheus collecting metrics
- [ ] Grafana dashboards displaying data
- [ ] Alerts configured and tested
- [ ] Log aggregation working
- [ ] Error tracking (Sentry) active
- [ ] Uptime monitoring configured

### Compliance Verification

- [ ] HIPAA compliance checklist completed
- [ ] BAA signed with all vendors
- [ ] Audit logging enabled
- [ ] Data retention policies active
- [ ] Incident response plan documented
- [ ] Security assessment completed

---

## Troubleshooting

### Common Issues

#### Pod CrashLoopBackOff

```bash
# Check logs
kubectl logs deployment/revrx-backend

# Check events
kubectl describe pod <pod-name>

# Common causes:
# - Missing environment variables
# - Database connection failure
# - Image pull errors
```

#### Database Connection Issues

```bash
# Test connection from pod
kubectl exec -it deployment/revrx-backend -- psql $DATABASE_URL -c "SELECT 1"

# Check PostgreSQL logs
kubectl logs statefulset/postgres
```

#### High Memory Usage

```bash
# Check resource usage
kubectl top pods

# Increase memory limits in deployment
kubectl set resources deployment/revrx-backend -c=backend --limits=memory=4Gi
```

See [Troubleshooting Guide](./troubleshooting-guide.md) for more details.

---

## Maintenance Windows

### Rolling Updates (Zero Downtime)

```bash
# Update image
kubectl set image deployment/revrx-backend backend=revrx-backend:v2.0.0

# Monitor rollout
kubectl rollout status deployment/revrx-backend
```

### Scheduled Maintenance

```bash
# Scale down for maintenance
kubectl scale deployment/revrx-backend --replicas=0

# Perform maintenance (DB migration, etc.)

# Scale back up
kubectl scale deployment/revrx-backend --replicas=3
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build and push Docker image
        run: |
          docker build -t revrx-backend:${{ github.sha }} .
          docker push revrx-backend:${{ github.sha }}

      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/revrx-backend \
            backend=revrx-backend:${{ github.sha }}
          kubectl rollout status deployment/revrx-backend
```

---

## Document Information

**Version:** 1.0
**Last Updated:** 2025-09-30
**Author:** RevRX DevOps Team
**Review Cycle:** Quarterly

**Next Steps:**
- Set up staging environment for testing
- Configure monitoring dashboards
- Schedule disaster recovery drill
- Document runbook procedures

# Environment Setup Guide

This document describes how to set up development, staging, and production environments for the RevRx application.

## Development Environment

### Prerequisites

- Docker Desktop 20.10+
- Node.js 20+
- Python 3.11+
- Docker Compose 2.0+

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/revrx.git
   cd revrx
   ```

2. **Configure environment variables**
   ```bash
   # Frontend
   cp .env.example .env.local

   # Backend
   cd backend
   cp .env.example .env
   ```

3. **Start services with Docker Compose**
   ```bash
   cd backend
   docker-compose up -d
   ```

4. **Run database migrations**
   ```bash
   docker-compose exec backend prisma migrate dev
   ```

5. **Seed database (optional)**
   ```bash
   docker-compose exec backend prisma db seed
   ```

6. **Start frontend development server**
   ```bash
   cd ..
   npm install
   npm run dev
   ```

7. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Development Environment Variables

#### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NODE_ENV=development
```

#### Backend (.env)

```env
# Database
DATABASE_URL=postgresql://revrx:revrx_dev_password@postgres:5432/revrx_db

# Redis
REDIS_URL=redis://redis:6379/0

# Application
APP_ENV=development
APP_DEBUG=true
LOG_LEVEL=DEBUG

# JWT
JWT_SECRET=your-dev-jwt-secret-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=43200

# AWS (use localstack for local development)
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1
S3_BUCKET_NAME=revrx-dev-uploads
S3_ENDPOINT_URL=http://localstack:4566

# OpenAI (use a test key or mock)
OPENAI_API_KEY=sk-test-key-here

# Comprehend Medical
COMPREHEND_REGION=us-east-1

# Email (use Mailhog for local testing)
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_FROM=noreply@revrx.local

# Data Retention
DATA_RETENTION_DAYS=7
```

### Development Tools

- **Prisma Studio**: View/edit database
  ```bash
  cd backend
  npx prisma studio
  ```

- **MailHog**: View emails
  - Add to docker-compose.yml
  - Access at http://localhost:8025

- **LocalStack**: Mock AWS services
  - Add to docker-compose.yml
  - Access at http://localhost:4566

## Staging Environment

### Infrastructure Requirements

- Kubernetes cluster (EKS recommended)
- Load balancer
- PostgreSQL database (RDS recommended)
- Redis cache (ElastiCache recommended)
- S3 bucket for file storage
- Domain with DNS configured

### Setup Steps

1. **Provision infrastructure**
   ```bash
   # Using Terraform (recommended)
   cd terraform/staging
   terraform init
   terraform plan
   terraform apply
   ```

2. **Configure kubectl**
   ```bash
   aws eks update-kubeconfig --name revrx-staging --region us-east-1
   ```

3. **Install required controllers**
   ```bash
   # NGINX Ingress
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.9.0/deploy/static/provider/cloud/deploy.yaml

   # cert-manager
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

   # Sealed Secrets
   kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml
   ```

4. **Create sealed secrets**
   ```bash
   # See k8s/README.md for detailed instructions
   ./scripts/create-sealed-secrets.sh staging
   ```

5. **Deploy application**
   ```bash
   kubectl apply -k k8s/overlays/staging
   ```

6. **Run database migrations**
   ```bash
   kubectl exec -it deployment/backend-staging -n revrx-staging -- \
     prisma migrate deploy
   ```

7. **Verify deployment**
   ```bash
   kubectl get pods -n revrx-staging
   kubectl get ingress -n revrx-staging
   ```

### Staging Environment Variables

Configure these in Kubernetes secrets (use sealed secrets):

```yaml
# backend-secret
DATABASE_URL: postgresql://USER:PASS@staging-db.region.rds.amazonaws.com:5432/revrx_staging
JWT_SECRET: <generated-secret>

# aws-secret
AWS_ACCESS_KEY_ID: <iam-user-key>
AWS_SECRET_ACCESS_KEY: <iam-user-secret>
AWS_REGION: us-east-1
S3_BUCKET_NAME: revrx-staging-uploads

# openai-secret
OPENAI_API_KEY: <staging-api-key>
```

### Staging Access

- Frontend: https://staging.revrx.example.com
- Backend API: https://api-staging.revrx.example.com
- API Docs: https://api-staging.revrx.example.com/docs

## Production Environment

### Infrastructure Requirements

- Production-grade Kubernetes cluster (EKS with multi-AZ)
- High-availability PostgreSQL (RDS Multi-AZ)
- Redis cluster (ElastiCache with replication)
- S3 bucket with versioning enabled
- CloudFront CDN (optional but recommended)
- WAF for security (recommended)
- Monitoring and alerting (Prometheus/Grafana or CloudWatch)

### Setup Steps

1. **Provision infrastructure**
   ```bash
   cd terraform/production
   terraform init
   terraform plan
   terraform apply
   ```

2. **Configure kubectl**
   ```bash
   aws eks update-kubeconfig --name revrx-production --region us-east-1
   ```

3. **Install required controllers** (same as staging)

4. **Create sealed secrets**
   ```bash
   ./scripts/create-sealed-secrets.sh production
   ```

5. **Deploy application**
   ```bash
   # Tag and push images
   docker tag revrx-backend:latest ghcr.io/your-org/revrx/backend:v1.0.0
   docker tag revrx-frontend:latest ghcr.io/your-org/revrx/frontend:v1.0.0
   docker push ghcr.io/your-org/revrx/backend:v1.0.0
   docker push ghcr.io/your-org/revrx/frontend:v1.0.0

   # Deploy
   kubectl apply -k k8s/overlays/production
   ```

6. **Run database migrations**
   ```bash
   # Create backup first!
   kubectl exec deployment/postgres -n revrx -- \
     pg_dump -U revrx revrx_db > backup-pre-migration.sql

   # Run migrations
   kubectl exec -it deployment/backend -n revrx -- \
     prisma migrate deploy
   ```

7. **Configure monitoring**
   ```bash
   # Install Prometheus/Grafana
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring
   ```

8. **Set up backups**
   ```bash
   # Configure automated backups (see disaster-recovery.md)
   kubectl apply -f k8s/cronjobs/database-backup.yaml
   ```

### Production Environment Variables

Configure these in Kubernetes secrets (use sealed secrets):

```yaml
# backend-secret
DATABASE_URL: postgresql://USER:PASS@prod-db.region.rds.amazonaws.com:5432/revrx_prod
JWT_SECRET: <strong-generated-secret>

# aws-secret
AWS_ACCESS_KEY_ID: <iam-user-key>
AWS_SECRET_ACCESS_KEY: <iam-user-secret>
AWS_REGION: us-east-1
S3_BUCKET_NAME: revrx-production-uploads

# openai-secret
OPENAI_API_KEY: <production-api-key>
```

### Production Access

- Frontend: https://app.revrx.com
- Backend API: https://api.revrx.com
- API Docs: https://api.revrx.com/docs (restrict access)

## CI/CD Configuration

### GitHub Secrets Required

#### For All Environments
- `GITHUB_TOKEN`: Automatically provided by GitHub

#### For Staging
- `AWS_ACCESS_KEY_ID`: AWS credentials for staging
- `AWS_SECRET_ACCESS_KEY`: AWS credentials for staging
- `AWS_REGION`: AWS region (e.g., us-east-1)
- `EKS_CLUSTER_NAME`: Staging cluster name

#### For Production
- `AWS_ACCESS_KEY_ID`: AWS credentials for production
- `AWS_SECRET_ACCESS_KEY`: AWS credentials for production
- `AWS_REGION`: AWS region
- `EKS_CLUSTER_NAME_PROD`: Production cluster name
- `BACKUP_BUCKET`: S3 bucket for backups

#### For Notifications (Optional)
- `SLACK_WEBHOOK_URL`: Slack webhook for deployment notifications

### Setting Secrets in GitHub

```bash
# Using GitHub CLI
gh secret set AWS_ACCESS_KEY_ID --body "YOUR_KEY"
gh secret set AWS_SECRET_ACCESS_KEY --body "YOUR_SECRET"

# Or via GitHub UI:
# Settings → Secrets and variables → Actions → New repository secret
```

## Environment Comparison

| Feature | Development | Staging | Production |
|---------|------------|---------|------------|
| Infrastructure | Docker Compose | Kubernetes (Single AZ) | Kubernetes (Multi-AZ) |
| Database | PostgreSQL (local) | RDS Single-AZ | RDS Multi-AZ |
| Cache | Redis (local) | ElastiCache Single | ElastiCache Cluster |
| Storage | Local filesystem | S3 Standard | S3 with versioning |
| Scaling | Manual | HPA (limited) | HPA (full) |
| Monitoring | Logs only | Basic CloudWatch | Full observability |
| Backups | None | Daily | Hourly + PITR |
| HTTPS | No | Yes (Let's Encrypt) | Yes (ACM) |
| CDN | No | No | CloudFront |
| WAF | No | No | Yes |

## Security Considerations

### Development
- Use test credentials only
- Never commit secrets to git
- Use `.env` files (gitignored)

### Staging
- Use separate AWS account if possible
- Limit access to authorized personnel
- Use sealed secrets for sensitive data
- Enable audit logging

### Production
- Use separate AWS account
- Implement strict RBAC
- Enable all security features (WAF, GuardDuty, etc.)
- Regular security audits
- Automated vulnerability scanning
- Encrypted data at rest and in transit
- HIPAA compliance measures active

## Troubleshooting

### Development Issues

**Database connection failed**
```bash
docker-compose ps  # Check if postgres is running
docker-compose logs postgres  # Check logs
```

**Port already in use**
```bash
# Change ports in docker-compose.yml or stop conflicting services
lsof -i :3000  # Find what's using port 3000
```

### Staging/Production Issues

**Deployment failed**
```bash
kubectl describe pod <pod-name> -n revrx
kubectl logs <pod-name> -n revrx
kubectl get events -n revrx --sort-by='.lastTimestamp'
```

**Database connection issues**
```bash
# Check connectivity
kubectl run -it --rm debug --image=postgres:16-alpine --restart=Never -n revrx -- \
  psql -h <db-host> -U revrx -d revrx_db
```

**Ingress not working**
```bash
kubectl describe ingress revrx-ingress -n revrx
kubectl logs -f deployment/ingress-nginx-controller -n ingress-nginx
```

## Support

For additional help:
- Check [k8s/README.md](../../k8s/README.md) for Kubernetes-specific issues
- See [disaster-recovery.md](disaster-recovery.md) for backup/restore procedures
- Contact DevOps team: devops@revrx.com

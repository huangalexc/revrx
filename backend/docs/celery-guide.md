# Celery Worker Guide

## Overview

This guide covers running Celery workers for distributed async report processing. Celery provides production-grade distributed task processing with Redis as the message broker.

## Prerequisites

1. **Redis Running**: See [redis-setup.md](./redis-setup.md)
2. **Environment Variables**: Configure Celery settings in `.env`

## Configuration

### Environment Variables

Add to `.env`:

```bash
# Enable Celery mode (default: false for asyncio mode)
ENABLE_CELERY=true

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=  # Set for production

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Worker Settings
CELERY_WORKER_CONCURRENCY=4  # Number of concurrent tasks per worker
CELERY_WORKER_PREFETCH_MULTIPLIER=2  # How many tasks to prefetch
CELERY_TASK_TIME_LIMIT=300  # Hard time limit (5 minutes)
CELERY_TASK_SOFT_TIME_LIMIT=240  # Soft time limit (4 minutes)
CELERY_RESULT_EXPIRES=3600  # Result TTL (1 hour)
```

## Running Workers

### Development Mode

#### Single Worker

```bash
cd backend
source venv/bin/activate
celery -A app.celery_app worker --loglevel=info
```

#### With Auto-Reload (Development)

```bash
celery -A app.celery_app worker --loglevel=info --autoreload
```

#### Multiple Queues

```bash
# Worker for reports queue
celery -A app.celery_app worker --loglevel=info -Q reports -n reports@%h

# Worker for default queue
celery -A app.celery_app worker --loglevel=info -Q default -n default@%h
```

### Production Mode

#### Single Worker

```bash
celery -A app.celery_app worker \
  --loglevel=warning \
  --concurrency=4 \
  --prefetch-multiplier=2 \
  --max-tasks-per-child=1000 \
  --time-limit=300 \
  --soft-time-limit=240 \
  -n worker1@%h
```

#### Multiple Workers (Scale Horizontally)

```bash
# Worker 1
celery -A app.celery_app worker -n worker1@%h --concurrency=4 -Q reports &

# Worker 2
celery -A app.celery_app worker -n worker2@%h --concurrency=4 -Q reports &

# Worker 3
celery -A app.celery_app worker -n worker3@%h --concurrency=4 -Q reports &
```

#### With Process Pool

```bash
celery -A app.celery_app worker \
  --pool=prefork \
  --concurrency=8 \
  --max-tasks-per-child=1000 \
  --time-limit=300 \
  --soft-time-limit=240 \
  -Q reports \
  -n worker@%h
```

## Monitoring Workers

### Worker Status

```bash
# Inspect active tasks
celery -A app.celery_app inspect active

# Inspect scheduled tasks
celery -A app.celery_app inspect scheduled

# Inspect reserved tasks
celery -A app.celery_app inspect reserved

# Show registered tasks
celery -A app.celery_app inspect registered

# Show worker stats
celery -A app.celery_app inspect stats

# Ping workers
celery -A app.celery_app inspect ping
```

### Queue Statistics

```bash
# Using Celery CLI
celery -A app.celery_app inspect active_queues

# Using Redis CLI
redis-cli LLEN celery  # Default queue length
redis-cli LLEN reports  # Reports queue length
```

### Real-Time Monitoring with Events

```bash
# Start event monitor
celery -A app.celery_app events

# Start Flower (web-based monitoring)
pip install flower
celery -A app.celery_app flower --port=5555
# Open http://localhost:5555
```

## Managing Workers

### Control Commands

```bash
# Graceful shutdown (wait for current tasks)
celery -A app.celery_app control shutdown

# Cancel all active tasks
celery -A app.celery_app purge

# Enable/disable task consumption
celery -A app.celery_app control cancel_consumer
celery -A app.celery_app control add_consumer

# Change log level at runtime
celery -A app.celery_app control log_level debug
```

### Health Check

```bash
# Test health check task
celery -A app.celery_app call app.celery_app.health_check
```

## Systemd Service (Linux Production)

Create `/etc/systemd/system/revrx-celery-worker.service`:

```ini
[Unit]
Description=RevRx Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=revrx
Group=revrx
WorkingDirectory=/opt/revrx/backend
Environment="PATH=/opt/revrx/backend/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/opt/revrx/backend/.env

ExecStart=/opt/revrx/backend/venv/bin/celery -A app.celery_app multi start worker1 \
    --pidfile=/var/run/celery/%n.pid \
    --logfile=/var/log/celery/%n%I.log \
    --loglevel=info \
    --concurrency=4 \
    --time-limit=300 \
    --soft-time-limit=240 \
    -Q reports

ExecStop=/opt/revrx/backend/venv/bin/celery -A app.celery_app multi stopwait worker1 \
    --pidfile=/var/run/celery/%n.pid

ExecReload=/opt/revrx/backend/venv/bin/celery -A app.celery_app multi restart worker1 \
    --pidfile=/var/run/celery/%n.pid \
    --logfile=/var/log/celery/%n%I.log \
    --loglevel=info \
    --concurrency=4

Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

Create required directories:

```bash
sudo mkdir -p /var/run/celery /var/log/celery
sudo chown revrx:revrx /var/run/celery /var/log/celery
```

Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable revrx-celery-worker
sudo systemctl start revrx-celery-worker
sudo systemctl status revrx-celery-worker
```

## Docker Deployment

### Dockerfile for Worker

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run Celery worker
CMD ["celery", "-A", "app.celery_app", "worker", \
     "--loglevel=info", \
     "--concurrency=4", \
     "-Q", "reports", \
     "-n", "worker@%h"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.worker
    environment:
      - ENABLE_CELERY=true
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - DATABASE_URL=${DATABASE_URL}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      redis:
        condition: service_healthy
    deploy:
      replicas: 2
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    command: >
      celery -A app.celery_app worker
      --loglevel=info
      --concurrency=4
      --max-tasks-per-child=1000
      -Q reports
      -n worker@%h

  flower:
    image: mher/flower
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    ports:
      - "5555:5555"
    depends_on:
      - redis
      - celery-worker

volumes:
  redis-data:
```

Start with:

```bash
docker-compose up -d
```

## Kubernetes Deployment

### Worker Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: revrx-celery-worker
  namespace: revrx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: revrx-celery-worker
  template:
    metadata:
      labels:
        app: revrx-celery-worker
    spec:
      containers:
      - name: worker
        image: revrx/backend:latest
        command: ["celery"]
        args:
          - "-A"
          - "app.celery_app"
          - "worker"
          - "--loglevel=info"
          - "--concurrency=4"
          - "--max-tasks-per-child=1000"
          - "-Q"
          - "reports"
          - "-n"
          - "worker@%h"
        env:
        - name: ENABLE_CELERY
          value: "true"
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: revrx-secrets
              key: redis-url
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: revrx-secrets
              key: database-url
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: revrx-secrets
              key: openai-api-key
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        livenessProbe:
          exec:
            command:
            - celery
            - -A
            - app.celery_app
            - inspect
            - ping
          initialDelaySeconds: 30
          periodSeconds: 60
          timeoutSeconds: 10
        readinessProbe:
          exec:
            command:
            - celery
            - -A
            - app.celery_app
            - inspect
            - active
          initialDelaySeconds: 10
          periodSeconds: 30
          timeoutSeconds: 10
```

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: revrx-celery-worker-hpa
  namespace: revrx
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: revrx-celery-worker
  minReplicas: 2
  maxReplicas: 10
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

## Troubleshooting

### Worker Not Starting

```bash
# Check Redis connectivity
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD PING

# Check Celery configuration
python -c "from app.celery_app import celery_app; print(celery_app.conf)"

# Verify Python imports
python -c "from app.tasks.report_tasks import process_report"
```

### Tasks Not Being Processed

```bash
# Check worker is consuming from correct queue
celery -A app.celery_app inspect active_queues

# Check task routing
celery -A app.celery_app inspect registered

# Check Redis queue
redis-cli LLEN reports
```

### Memory Leaks

```bash
# Reduce max-tasks-per-child to restart workers more frequently
celery -A app.celery_app worker --max-tasks-per-child=100

# Use thread pool instead of prefork
celery -A app.celery_app worker --pool=threads --concurrency=20
```

### High Latency

```bash
# Increase worker concurrency
celery -A app.celery_app worker --concurrency=8

# Add more workers
celery -A app.celery_app worker -n worker2@%h --concurrency=4 &

# Check queue depth
redis-cli LLEN reports
```

## Performance Tuning

### Optimal Concurrency

- **CPU-bound tasks**: `concurrency = number of CPU cores`
- **I/O-bound tasks**: `concurrency = 2-4 × number of CPU cores`
- **Mixed workload**: `concurrency = 1.5 × number of CPU cores`

For report processing (I/O-bound with OpenAI/Comprehend calls):
```bash
# For 4-core machine
celery -A app.celery_app worker --concurrency=12
```

### Prefetch Optimization

- **Low prefetch** (1-2): Better distribution, more Redis calls
- **High prefetch** (4-8): Fewer Redis calls, potential worker starvation

```bash
# Balanced setting for report processing
celery -A app.celery_app worker --prefetch-multiplier=2
```

### Task Result Optimization

```bash
# Reduce result expiration to save Redis memory
CELERY_RESULT_EXPIRES=1800  # 30 minutes

# Disable result storage for tasks that don't need it
CELERY_TASK_IGNORE_RESULT=true  # In task decorator
```

## Best Practices

1. **Always use named workers** (`-n worker1@%h`) for easier debugging
2. **Set concurrency based on workload type** (CPU vs I/O bound)
3. **Use dedicated queues** for different task types
4. **Monitor worker memory** and restart periodically (`max-tasks-per-child`)
5. **Enable task events** for monitoring (`task_send_sent_event`)
6. **Use soft time limits** to allow graceful cleanup
7. **Set up alerts** for queue depth and worker failures
8. **Use Flower** for production monitoring
9. **Version your tasks** to handle code changes gracefully
10. **Test autoscaling** before production deployment

## Next Steps

After setting up workers:

1. Test with load testing script: `python scripts/load_test_async_reports.py`
2. Set up monitoring and alerts (Section 9.4)
3. Configure autoscaling (Section 9.3)

## References

- [Celery Documentation](https://docs.celeryq.dev/)
- [Celery Best Practices](https://docs.celeryq.dev/en/stable/userguide/tasks.html#best-practices)
- [Flower Monitoring](https://flower.readthedocs.io/)

# Worker Autoscaling Configuration

## Overview

This guide covers autoscaling configuration for Celery workers across different infrastructure platforms. Autoscaling ensures optimal resource utilization and cost efficiency while maintaining performance.

## Autoscaling Strategies

### 1. Queue-Based Autoscaling (Recommended)

Scale workers based on Redis queue depth:

- **Scale up when**: Queue depth > threshold × current workers
- **Scale down when**: Queue depth < threshold × current workers AND workers idle > cooldown

**Metrics**:
- Queue depth (from Redis `LLEN` command)
- Active tasks per worker
- Task processing rate

### 2. CPU/Memory-Based Autoscaling

Scale workers based on resource utilization:

- **Scale up when**: CPU > 75% OR Memory > 80%
- **Scale down when**: CPU < 30% AND Memory < 50% for >5 minutes

### 3. Hybrid Autoscaling (Best)

Combine queue depth and resource metrics:

- Primary: Queue depth (fast reaction)
- Secondary: CPU/Memory (prevent overload)
- Tertiary: Time of day patterns (predictive)

## Kubernetes Horizontal Pod Autoscaler (HPA)

### Prerequisites

1. Metrics Server installed:
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

2. Prometheus + Grafana (for custom metrics):
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack
```

### HPA Configuration

#### Basic CPU/Memory Autoscaling

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
  maxReplicas: 20
  metrics:
  # CPU-based scaling
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  # Memory-based scaling
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 minutes before scaling down
      policies:
      - type: Percent
        value: 50  # Scale down max 50% of current pods
        periodSeconds: 60
      - type: Pods
        value: 2  # Or remove max 2 pods
        periodSeconds: 60
      selectPolicy: Min  # Choose the more conservative policy
    scaleUp:
      stabilizationWindowSeconds: 60  # Wait 1 minute before scaling up
      policies:
      - type: Percent
        value: 100  # Scale up max 100% of current pods
        periodSeconds: 30
      - type: Pods
        value: 4  # Or add max 4 pods
        periodSeconds: 30
      selectPolicy: Max  # Choose the more aggressive policy
```

Apply with:
```bash
kubectl apply -f k8s/celery-worker-hpa.yaml
```

#### Custom Metrics: Queue Depth Autoscaling

**Step 1**: Create Redis queue metrics exporter

```yaml
# redis-queue-exporter.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-queue-exporter
  namespace: revrx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis-queue-exporter
  template:
    metadata:
      labels:
        app: redis-queue-exporter
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9121"
    spec:
      containers:
      - name: exporter
        image: oliver006/redis_exporter:latest
        ports:
        - containerPort: 9121
        env:
        - name: REDIS_ADDR
          value: "redis:6379"
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: password
---
apiVersion: v1
kind: Service
metadata:
  name: redis-queue-exporter
  namespace: revrx
  labels:
    app: redis-queue-exporter
spec:
  ports:
  - port: 9121
    targetPort: 9121
    name: metrics
  selector:
    app: redis-queue-exporter
```

**Step 2**: Create ServiceMonitor for Prometheus

```yaml
# redis-queue-servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: redis-queue-exporter
  namespace: revrx
spec:
  selector:
    matchLabels:
      app: redis-queue-exporter
  endpoints:
  - port: metrics
    interval: 10s
```

**Step 3**: Create HPA with custom queue depth metric

```yaml
# celery-worker-hpa-custom.yaml
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
  maxReplicas: 20
  metrics:
  # Custom metric: Redis queue depth per worker
  - type: Pods
    pods:
      metric:
        name: redis_queue_depth_per_worker
      target:
        type: AverageValue
        averageValue: "10"  # Target 10 tasks per worker
  # Fallback to CPU if custom metric unavailable
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Pods
        value: 1
        periodSeconds: 120
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
      - type: Pods
        value: 4
        periodSeconds: 30
```

**Step 4**: Create Prometheus rule for queue depth per worker

```yaml
# prometheus-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: celery-autoscaling-rules
  namespace: revrx
spec:
  groups:
  - name: celery_autoscaling
    interval: 10s
    rules:
    - record: redis_queue_depth_per_worker
      expr: |
        sum(redis_key_size{key="celery:reports"})
        /
        max(kube_deployment_status_replicas{deployment="revrx-celery-worker"})
```

Monitor autoscaling:
```bash
# Watch HPA status
kubectl get hpa -n revrx -w

# View detailed HPA events
kubectl describe hpa revrx-celery-worker-hpa -n revrx

# Check current queue depth
kubectl exec -n revrx redis-0 -- redis-cli LLEN celery:reports
```

## AWS ECS Autoscaling

### Target Tracking Scaling (Recommended)

#### CPU-Based Autoscaling

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/revrx-cluster/celery-worker-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 20

# Create CPU-based scaling policy
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/revrx-cluster/celery-worker-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name celery-worker-cpu-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'
```

#### Memory-Based Autoscaling

```bash
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/revrx-cluster/celery-worker-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name celery-worker-memory-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 80.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageMemoryUtilization"
    },
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'
```

### Custom CloudWatch Metrics: Queue Depth

**Step 1**: Create Lambda function to publish queue metrics

```python
# lambda/publish_queue_metrics.py
import boto3
import redis
import os
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')
redis_client = redis.from_url(os.environ['REDIS_URL'])

def lambda_handler(event, context):
    """Publish Redis queue depth to CloudWatch"""

    # Get queue depth
    queue_depth = redis_client.llen('celery:reports')

    # Publish to CloudWatch
    cloudwatch.put_metric_data(
        Namespace='RevRx/CeleryWorkers',
        MetricData=[
            {
                'MetricName': 'QueueDepth',
                'Value': queue_depth,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow(),
                'Dimensions': [
                    {'Name': 'Queue', 'Value': 'reports'}
                ]
            }
        ]
    )

    return {'statusCode': 200, 'body': f'Published queue depth: {queue_depth}'}
```

**Step 2**: Create EventBridge rule to run Lambda every minute

```bash
aws events put-rule \
  --name publish-celery-queue-metrics \
  --schedule-expression "rate(1 minute)" \
  --state ENABLED

aws events put-targets \
  --rule publish-celery-queue-metrics \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:ACCOUNT:function:publish-queue-metrics"
```

**Step 3**: Create target tracking policy with custom metric

```bash
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/revrx-cluster/celery-worker-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name celery-worker-queue-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 20.0,
    "CustomizedMetricSpecification": {
      "MetricName": "QueueDepth",
      "Namespace": "RevRx/CeleryWorkers",
      "Dimensions": [
        {"Name": "Queue", "Value": "reports"}
      ],
      "Statistic": "Average",
      "Unit": "Count"
    },
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'
```

Monitor autoscaling:
```bash
# Check current task count
aws ecs describe-services \
  --cluster revrx-cluster \
  --services celery-worker-service \
  --query 'services[0].desiredCount'

# View scaling activities
aws application-autoscaling describe-scaling-activities \
  --service-namespace ecs \
  --resource-id service/revrx-cluster/celery-worker-service
```

## Celery Built-in Autoscaling

### Autoscale Worker Pool

Run worker with built-in autoscaling:

```bash
celery -A app.celery_app worker \
  --autoscale=10,3 \
  --loglevel=info \
  -Q reports
```

- `10`: Maximum concurrency (scale up to)
- `3`: Minimum concurrency (scale down to)

### How It Works

Celery autoscale monitors:
1. **Queue depth** in Redis
2. **Active tasks** per worker
3. **Idle time** of worker processes

Scaling decisions:
- **Scale up**: When queue depth > available processes
- **Scale down**: When processes idle > 30 seconds

### Configuration

```python
# In celery_app.py
celery_app.conf.update(
    # Autoscale settings
    worker_autoscaler='celery.worker.autoscale:Autoscaler',
    worker_autoscale_max=10,
    worker_autoscale_min=3,
    worker_autoscale_keepalive=30,  # Seconds before scaling down
)
```

## Monitoring Autoscaling

### Key Metrics to Track

1. **Queue Depth**: `redis_key_size{key="celery:reports"}`
2. **Worker Count**: `celery_worker_count`
3. **Tasks per Worker**: `queue_depth / worker_count`
4. **CPU Utilization**: `container_cpu_usage_percent`
5. **Memory Utilization**: `container_memory_usage_percent`
6. **Task Processing Rate**: `tasks_completed / minute`
7. **Task Wait Time**: `time_in_queue_seconds`
8. **Autoscaling Events**: `scaling_up_count`, `scaling_down_count`

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Celery Worker Autoscaling",
    "panels": [
      {
        "title": "Worker Count Over Time",
        "targets": [
          {"expr": "kube_deployment_status_replicas{deployment='revrx-celery-worker'}"}
        ]
      },
      {
        "title": "Queue Depth",
        "targets": [
          {"expr": "redis_key_size{key='celery:reports'}"}
        ]
      },
      {
        "title": "Tasks per Worker",
        "targets": [
          {"expr": "redis_key_size{key='celery:reports'} / kube_deployment_status_replicas{deployment='revrx-celery-worker'}"}
        ]
      },
      {
        "title": "CPU Utilization",
        "targets": [
          {"expr": "avg(rate(container_cpu_usage_seconds_total{pod=~'revrx-celery-worker.*'}[5m])) by (pod)"}
        ]
      }
    ]
  }
}
```

## Best Practices

### Scaling Thresholds

- **Min Replicas**: 2 (high availability)
- **Max Replicas**: 10-20 (cost control)
- **Target CPU**: 70% (headroom for spikes)
- **Target Memory**: 80% (prevent OOM kills)
- **Tasks per Worker**: 5-10 (queue-based scaling)

### Cooldown Periods

- **Scale Up Cooldown**: 30-60 seconds (react quickly)
- **Scale Down Cooldown**: 5-10 minutes (avoid flapping)
- **Stabilization Window**: 60-120 seconds (smooth scaling)

### Resource Limits

```yaml
# Kubernetes resource requests/limits
resources:
  requests:
    cpu: 500m      # Guaranteed CPU
    memory: 1Gi    # Guaranteed RAM
  limits:
    cpu: 2000m     # Maximum CPU (burst)
    memory: 4Gi    # Maximum RAM (hard limit)
```

### Avoid Over-Scaling

1. **Set realistic max replicas** based on:
   - Budget constraints
   - Infrastructure capacity
   - Downstream service limits (OpenAI, Comprehend rate limits)

2. **Use scale-down protection**:
   - Minimum replica count
   - Longer cooldown for scale-down
   - Gradual scale-down (max 50% per interval)

3. **Monitor cost**:
   - Set budget alerts
   - Track cost per task
   - Review autoscaling effectiveness weekly

## Testing Autoscaling

### Load Test Script

```python
# scripts/test_autoscaling.py
import asyncio
import httpx
from concurrent.futures import ThreadPoolExecutor

async def create_reports(count: int):
    """Create multiple reports to trigger autoscaling"""
    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(count):
            task = client.post(
                f"http://localhost:8000/api/v1/reports/encounters/{encounter_id}/reports",
                headers={"Authorization": f"Bearer {token}"}
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        return [r.status_code for r in responses]

# Create 100 reports to test autoscaling
asyncio.run(create_reports(100))
```

Run test:
```bash
python backend/scripts/test_autoscaling.py
```

Watch autoscaling in action:
```bash
# Kubernetes
watch kubectl get hpa,pods -n revrx

# AWS ECS
watch aws ecs describe-services --cluster revrx-cluster --services celery-worker-service
```

## Troubleshooting

### Workers Not Scaling Up

1. Check HPA status: `kubectl describe hpa <name>`
2. Verify metrics available: `kubectl get hpa <name> -o yaml`
3. Check resource requests are set
4. Ensure metrics server is running

### Workers Scaling Up Too Aggressively

1. Increase `scaleUpCooldown` to 120 seconds
2. Lower scale-up `percent` value to 50%
3. Increase target utilization threshold

### Workers Not Scaling Down

1. Check `stabilizationWindowSeconds` (may be too long)
2. Verify workers are actually idle
3. Check if there are pending tasks

### Flapping (Rapid Scale Up/Down)

1. Increase both cooldown periods
2. Set wider thresholds (e.g., CPU 60-80% range)
3. Use `stabilizationWindowSeconds` to smooth out spikes

## Next Steps

1. Implement monitoring and alerting (Section 9.4)
2. Set up Grafana dashboards for autoscaling metrics
3. Run load tests to validate autoscaling behavior
4. Fine-tune thresholds based on production patterns

## References

- [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [AWS ECS Autoscaling](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html)
- [Celery Autoscaling](https://docs.celeryq.dev/en/stable/userguide/workers.html#autoscaling)

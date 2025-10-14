# Monitoring and Alerting for Async Report Processing

## Overview

This guide covers comprehensive monitoring and alerting for the async report processing system. It includes metrics, dashboards, and alert rules for Prometheus, Grafana, and CloudWatch.

## Key Metrics to Monitor

### Queue Metrics

1. **Queue Depth** (`celery_queue_depth`)
   - Current number of pending tasks in queue
   - Alert if >100 for >5 minutes

2. **Queue Wait Time** (`celery_task_wait_time_seconds`)
   - Time tasks spend in queue before processing
   - Alert if p95 >30 seconds

3. **Queue Growth Rate** (`rate(celery_queue_depth[5m])`)
   - Rate of queue size change
   - Alert if positive for >10 minutes (backlog growing)

### Worker Metrics

4. **Worker Count** (`celery_worker_count`)
   - Number of active workers
   - Alert if <2 (no redundancy)

5. **Worker Utilization** (`celery_worker_busy_ratio`)
   - Percentage of workers actively processing tasks
   - Alert if >90% for >5 minutes (workers saturated)

6. **Tasks per Worker** (`celery_active_tasks / celery_worker_count`)
   - Load distribution across workers
   - Alert if >10 per worker

### Task Metrics

7. **Processing Time** (`celery_task_runtime_seconds`)
   - Time to complete report processing
   - Alert if p95 >60 seconds

8. **Task Success Rate** (`celery_task_succeeded / celery_task_total`)
   - Percentage of successfully completed tasks
   - Alert if <95%

9. **Task Failure Rate** (`rate(celery_task_failed[5m])`)
   - Rate of task failures
   - Alert if >5% of total tasks

10. **Retry Count** (`celery_task_retry_count`)
    - Number of task retries
    - Alert if average >2 per task

### System Metrics

11. **CPU Utilization** (`container_cpu_usage_percent`)
    - Worker container CPU usage
    - Alert if >80% for >5 minutes

12. **Memory Utilization** (`container_memory_usage_percent`)
    - Worker container memory usage
    - Alert if >85% (approaching OOM)

13. **Redis Memory Usage** (`redis_memory_used_bytes / redis_memory_max_bytes`)
    - Redis memory utilization
    - Alert if >80%

14. **Redis Connections** (`redis_connected_clients`)
    - Number of Redis connections
    - Alert if >90% of max connections

## Prometheus Configuration

### Install Prometheus Operator (Kubernetes)

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

### ServiceMonitor for Celery Workers

```yaml
# celery-worker-servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: celery-worker-metrics
  namespace: revrx
  labels:
    app: celery-worker
spec:
  selector:
    matchLabels:
      app: celery-worker
  endpoints:
  - port: metrics
    interval: 15s
    path: /metrics
```

### Custom Metrics Exporter

Create a Flask app to expose Celery metrics:

```python
# app/monitoring/celery_exporter.py
from flask import Flask, Response
from prometheus_client import generate_latest, REGISTRY, Gauge, Counter, Histogram
from app.celery_app import celery_app, get_celery_stats
import redis
import os

app = Flask(__name__)

# Define metrics
queue_depth = Gauge('celery_queue_depth', 'Number of tasks in queue', ['queue'])
worker_count = Gauge('celery_worker_count', 'Number of active workers')
active_tasks = Gauge('celery_active_tasks', 'Number of currently processing tasks')
scheduled_tasks = Gauge('celery_scheduled_tasks', 'Number of scheduled tasks')
task_runtime = Histogram('celery_task_runtime_seconds', 'Task execution time', ['task'])
task_succeeded = Counter('celery_task_succeeded_total', 'Number of successful tasks', ['task'])
task_failed = Counter('celery_task_failed_total', 'Number of failed tasks', ['task'])
task_retry = Counter('celery_task_retry_total', 'Number of task retries', ['task'])

# Redis client for queue metrics
redis_client = redis.from_url(os.getenv('REDIS_URL'))

@app.route('/metrics')
def metrics():
    """Expose Celery metrics for Prometheus"""

    # Get Celery stats
    stats = get_celery_stats()

    # Update gauges
    worker_count.set(stats.get('worker_count', 0))
    active_tasks.set(stats.get('active_tasks', 0))
    scheduled_tasks.set(stats.get('scheduled_tasks', 0))

    # Get queue depths
    for queue_name in ['reports', 'default']:
        depth = redis_client.llen(f'celery:{queue_name}')
        queue_depth.labels(queue=queue_name).set(depth)

    # Return metrics in Prometheus format
    return Response(generate_latest(REGISTRY), mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090)
```

Deploy exporter:

```yaml
# celery-metrics-exporter.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-metrics-exporter
  namespace: revrx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: celery-metrics-exporter
  template:
    metadata:
      labels:
        app: celery-metrics-exporter
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      containers:
      - name: exporter
        image: revrx/celery-exporter:latest
        ports:
        - containerPort: 9090
          name: metrics
        env:
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: url
---
apiVersion: v1
kind: Service
metadata:
  name: celery-metrics-exporter
  namespace: revrx
  labels:
    app: celery-metrics-exporter
spec:
  ports:
  - port: 9090
    targetPort: 9090
    name: metrics
  selector:
    app: celery-metrics-exporter
```

### Prometheus Recording Rules

```yaml
# prometheus-recording-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: celery-recording-rules
  namespace: revrx
spec:
  groups:
  - name: celery_aggregations
    interval: 30s
    rules:
    # Worker utilization
    - record: celery_worker_busy_ratio
      expr: |
        celery_active_tasks / (celery_worker_count * 4)

    # Tasks per worker
    - record: celery_tasks_per_worker
      expr: |
        celery_queue_depth{queue="reports"} / celery_worker_count

    # Task success rate (5 minute window)
    - record: celery_task_success_rate_5m
      expr: |
        sum(rate(celery_task_succeeded_total[5m]))
        /
        (
          sum(rate(celery_task_succeeded_total[5m]))
          +
          sum(rate(celery_task_failed_total[5m]))
        )

    # Average task runtime (5 minute window)
    - record: celery_task_runtime_seconds_avg_5m
      expr: |
        rate(celery_task_runtime_seconds_sum[5m])
        /
        rate(celery_task_runtime_seconds_count[5m])
```

### Prometheus Alert Rules

```yaml
# prometheus-alert-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: celery-alerts
  namespace: revrx
spec:
  groups:
  - name: celery_alerts
    interval: 30s
    rules:
    # Queue depth too high
    - alert: CeleryQueueDepthHigh
      expr: celery_queue_depth{queue="reports"} > 100
      for: 5m
      labels:
        severity: warning
        component: celery
      annotations:
        summary: "Celery queue depth is too high"
        description: "Queue '{{ $labels.queue }}' has {{ $value }} pending tasks for more than 5 minutes"

    # Queue growing (backlog)
    - alert: CeleryQueueGrowing
      expr: rate(celery_queue_depth{queue="reports"}[5m]) > 0
      for: 10m
      labels:
        severity: warning
        component: celery
      annotations:
        summary: "Celery queue is growing"
        description: "Queue '{{ $labels.queue }}' is growing at {{ $value }} tasks/sec for 10+ minutes"

    # No workers available
    - alert: CeleryNoWorkers
      expr: celery_worker_count == 0
      for: 1m
      labels:
        severity: critical
        component: celery
      annotations:
        summary: "No Celery workers available"
        description: "All Celery workers are down. Reports cannot be processed."

    # Low worker redundancy
    - alert: CeleryLowRedundancy
      expr: celery_worker_count < 2
      for: 5m
      labels:
        severity: warning
        component: celery
      annotations:
        summary: "Low Celery worker redundancy"
        description: "Only {{ $value }} worker(s) available. Consider scaling up."

    # Workers saturated
    - alert: CeleryWorkersSaturated
      expr: celery_worker_busy_ratio > 0.90
      for: 5m
      labels:
        severity: warning
        component: celery
      annotations:
        summary: "Celery workers are saturated"
        description: "Workers are {{ $value | humanizePercentage }} busy. Consider scaling up."

    # High task failure rate
    - alert: CeleryHighFailureRate
      expr: celery_task_success_rate_5m < 0.95
      for: 5m
      labels:
        severity: critical
        component: celery
      annotations:
        summary: "High Celery task failure rate"
        description: "Task success rate is {{ $value | humanizePercentage }} (below 95%)"

    # Slow task processing
    - alert: CelerySlowProcessing
      expr: |
        histogram_quantile(0.95,
          rate(celery_task_runtime_seconds_bucket[5m])
        ) > 60
      for: 10m
      labels:
        severity: warning
        component: celery
      annotations:
        summary: "Celery tasks are slow"
        description: "p95 task runtime is {{ $value }}s (above 60s threshold)"

    # High Redis memory usage
    - alert: RedisMemoryHigh
      expr: |
        redis_memory_used_bytes / redis_memory_max_bytes > 0.80
      for: 5m
      labels:
        severity: warning
        component: redis
      annotations:
        summary: "Redis memory usage is high"
        description: "Redis using {{ $value | humanizePercentage }} of available memory"

    # Redis connection saturation
    - alert: RedisConnectionsSaturated
      expr: redis_connected_clients > redis_maxclients * 0.90
      for: 5m
      labels:
        severity: critical
        component: redis
      annotations:
        summary: "Redis connections near limit"
        description: "{{ $value }} connections active (near maxclients)"
```

## Grafana Dashboards

### Celery Overview Dashboard

```json
{
  "dashboard": {
    "title": "Celery Async Report Processing",
    "panels": [
      {
        "id": 1,
        "title": "Queue Depth Over Time",
        "type": "graph",
        "targets": [
          {
            "expr": "celery_queue_depth{queue='reports'}",
            "legendFormat": "Reports Queue"
          }
        ],
        "alert": {
          "conditions": [
            {
              "evaluator": {"params": [100], "type": "gt"},
              "operator": {"type": "and"},
              "query": {"params": ["A", "5m", "now"]},
              "reducer": {"params": [], "type": "avg"},
              "type": "query"
            }
          ],
          "frequency": "1m",
          "handler": 1,
          "name": "Queue Depth Alert"
        }
      },
      {
        "id": 2,
        "title": "Worker Count",
        "type": "stat",
        "targets": [
          {
            "expr": "celery_worker_count",
            "legendFormat": "Active Workers"
          }
        ]
      },
      {
        "id": 3,
        "title": "Task Success Rate",
        "type": "gauge",
        "targets": [
          {
            "expr": "celery_task_success_rate_5m * 100",
            "legendFormat": "Success Rate (%)"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "mode": "absolute",
              "steps": [
                {"color": "red", "value": 0},
                {"color": "yellow", "value": 90},
                {"color": "green", "value": 95}
              ]
            },
            "max": 100,
            "min": 0
          }
        }
      },
      {
        "id": 4,
        "title": "Task Processing Time (p50, p95, p99)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(celery_task_runtime_seconds_bucket[5m]))",
            "legendFormat": "p50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(celery_task_runtime_seconds_bucket[5m]))",
            "legendFormat": "p95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(celery_task_runtime_seconds_bucket[5m]))",
            "legendFormat": "p99"
          }
        ]
      },
      {
        "id": 5,
        "title": "Worker CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "avg(rate(container_cpu_usage_seconds_total{pod=~'revrx-celery-worker.*'}[5m])) by (pod) * 100",
            "legendFormat": "{{ pod }}"
          }
        ]
      },
      {
        "id": 6,
        "title": "Worker Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "avg(container_memory_usage_bytes{pod=~'revrx-celery-worker.*'}) by (pod) / 1024 / 1024",
            "legendFormat": "{{ pod }} (MB)"
          }
        ]
      },
      {
        "id": 7,
        "title": "Active Tasks",
        "type": "stat",
        "targets": [
          {
            "expr": "celery_active_tasks",
            "legendFormat": "Processing Now"
          }
        ]
      },
      {
        "id": 8,
        "title": "Tasks Completed vs Failed",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(celery_task_succeeded_total[5m])",
            "legendFormat": "Succeeded"
          },
          {
            "expr": "rate(celery_task_failed_total[5m])",
            "legendFormat": "Failed"
          }
        ]
      }
    ]
  }
}
```

Import dashboard:
```bash
# Save JSON to celery-dashboard.json
kubectl create configmap grafana-celery-dashboard \
  --from-file=celery-dashboard.json \
  --namespace=monitoring

# Or import via Grafana UI: http://grafana.local/dashboard/import
```

## CloudWatch Monitoring (AWS)

### CloudWatch Metrics

Publish custom metrics from Lambda:

```python
# lambda/publish_celery_metrics.py
import boto3
import redis
import os
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')
redis_client = redis.from_url(os.environ['REDIS_URL'])

def lambda_handler(event, context):
    """Publish Celery metrics to CloudWatch"""

    namespace = 'RevRx/CeleryWorkers'
    timestamp = datetime.utcnow()

    # Get queue depth
    queue_depth = redis_client.llen('celery:reports')

    # Get worker stats from Celery
    from app.celery_app import get_celery_stats
    stats = get_celery_stats()

    # Publish metrics
    cloudwatch.put_metric_data(
        Namespace=namespace,
        MetricData=[
            {
                'MetricName': 'QueueDepth',
                'Value': queue_depth,
                'Unit': 'Count',
                'Timestamp': timestamp,
                'Dimensions': [{'Name': 'Queue', 'Value': 'reports'}]
            },
            {
                'MetricName': 'WorkerCount',
                'Value': stats.get('worker_count', 0),
                'Unit': 'Count',
                'Timestamp': timestamp
            },
            {
                'MetricName': 'ActiveTasks',
                'Value': stats.get('active_tasks', 0),
                'Unit': 'Count',
                'Timestamp': timestamp
            },
            {
                'MetricName': 'TasksPerWorker',
                'Value': queue_depth / max(stats.get('worker_count', 1), 1),
                'Unit': 'Count',
                'Timestamp': timestamp
            }
        ]
    )

    return {'statusCode': 200}
```

### CloudWatch Alarms

```bash
# Queue depth alarm
aws cloudwatch put-metric-alarm \
  --alarm-name celery-queue-depth-high \
  --alarm-description "Alert when Celery queue depth > 100" \
  --metric-name QueueDepth \
  --namespace RevRx/CeleryWorkers \
  --dimensions Name=Queue,Value=reports \
  --statistic Average \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:celery-alerts

# No workers alarm
aws cloudwatch put-metric-alarm \
  --alarm-name celery-no-workers \
  --alarm-description "Alert when no Celery workers available" \
  --metric-name WorkerCount \
  --namespace RevRx/CeleryWorkers \
  --statistic Minimum \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:celery-critical-alerts

# High tasks per worker
aws cloudwatch put-metric-alarm \
  --alarm-name celery-high-load-per-worker \
  --alarm-description "Alert when tasks per worker > 10" \
  --metric-name TasksPerWorker \
  --namespace RevRx/CeleryWorkers \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:celery-alerts
```

### CloudWatch Dashboard

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["RevRx/CeleryWorkers", "QueueDepth", {"stat": "Average"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Queue Depth",
        "yAxis": {"left": {"min": 0}}
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["RevRx/CeleryWorkers", "WorkerCount", {"stat": "Average"}]
        ],
        "period": 60,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Worker Count"
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["RevRx/CeleryWorkers", "ActiveTasks", {"stat": "Sum"}]
        ],
        "period": 60,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "Active Tasks"
      }
    }
  ]
}
```

## Alert Notification Channels

### Slack Integration (Prometheus)

```yaml
# alertmanager-config.yaml
apiVersion: v1
kind: Secret
metadata:
  name: alertmanager-config
  namespace: monitoring
stringData:
  alertmanager.yml: |
    global:
      resolve_timeout: 5m
      slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'

    route:
      group_by: ['alertname', 'cluster', 'service']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 12h
      receiver: 'slack-notifications'
      routes:
      - match:
          severity: critical
        receiver: 'pagerduty'
        continue: true

    receivers:
    - name: 'slack-notifications'
      slack_configs:
      - channel: '#celery-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
        send_resolved: true

    - name: 'pagerduty'
      pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

### PagerDuty Integration

```yaml
receivers:
- name: 'pagerduty'
  pagerduty_configs:
  - service_key: 'YOUR_PAGERDUTY_INTEGRATION_KEY'
    description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'
    details:
      firing: '{{ range .Alerts.Firing }}{{ .Labels.alertname }}: {{ .Annotations.description }}{{ end }}'
```

### Email Notifications (AWS SNS)

```bash
# Create SNS topic
aws sns create-topic --name celery-alerts

# Subscribe email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:celery-alerts \
  --protocol email \
  --notification-endpoint ops@example.com
```

## Health Check Endpoints

Add health check endpoint to FastAPI:

```python
# app/api/v1/monitoring.py
from fastapi import APIRouter
from app.services.task_queue import get_queue_stats
from app.celery_app import celery_app
import redis

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

@router.get("/health/celery")
async def celery_health():
    """Check Celery worker health"""
    try:
        # Ping workers
        inspect = celery_app.control.inspect()
        ping = inspect.ping()

        if not ping:
            return {"status": "unhealthy", "reason": "No workers responding"}

        return {
            "status": "healthy",
            "workers": list(ping.keys()),
            "worker_count": len(ping)
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@router.get("/health/redis")
async def redis_health():
    """Check Redis connectivity"""
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        return {"status": "healthy", "connected": True}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@router.get("/metrics/queue")
async def queue_metrics():
    """Get queue statistics"""
    stats = get_queue_stats()
    return {
        "queue_depth": stats.get("total_tasks", 0),
        "worker_count": stats.get("worker_count", 0),
        "backend": stats.get("backend", "unknown")
    }
```

## Logging

### Structured Logging with Structlog

Already configured in `app/core/logging.py`. Add correlation IDs:

```python
# Middleware to add correlation IDs
from uuid import uuid4
import structlog

@app.middleware("http")
async def add_correlation_id(request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
```

### Log Aggregation (ELK Stack)

Forward logs to Elasticsearch:

```yaml
# filebeat-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: filebeat-config
  namespace: revrx
data:
  filebeat.yml: |
    filebeat.inputs:
    - type: container
      paths:
        - /var/log/containers/revrx-celery-worker*.log
      processors:
      - add_kubernetes_metadata:
          host: ${NODE_NAME}
          matchers:
          - logs_path:
              logs_path: "/var/log/containers/"

    output.elasticsearch:
      hosts: ['${ELASTICSEARCH_HOST:elasticsearch}:${ELASTICSEARCH_PORT:9200}']
      username: ${ELASTICSEARCH_USERNAME}
      password: ${ELASTICSEARCH_PASSWORD}

    setup.kibana:
      host: '${KIBANA_HOST:kibana}:${KIBANA_PORT:5601}'
```

## Best Practices

1. **Start with fewer alerts**, add more as you understand patterns
2. **Use severity levels**: critical, warning, info
3. **Set appropriate thresholds** based on baseline performance
4. **Test alerts** before production deployment
5. **Document runbooks** for each alert
6. **Review alerts weekly** to reduce noise
7. **Use dashboards** for proactive monitoring
8. **Set up escalation policies** for critical alerts
9. **Monitor monitoring system** (who watches the watchers?)
10. **Track MTTR** (mean time to resolution) for incidents

## Troubleshooting

See logs:
```bash
# Kubernetes
kubectl logs -n revrx -l app=celery-worker --tail=100

# Docker
docker logs celery-worker-1

# Systemd
journalctl -u revrx-celery-worker -f
```

## Next Steps

1. Deploy monitoring stack to production
2. Set up Grafana dashboards
3. Configure alert notification channels
4. Test alerts with load testing
5. Create runbooks for common incidents

## References

- [Prometheus Docs](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)
- [CloudWatch Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html)
- [Celery Monitoring](https://docs.celeryq.dev/en/stable/userguide/monitoring.html)

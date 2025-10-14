# Redis Setup for Async Report Processing

## Overview

Redis serves as the message broker and result backend for Celery-based distributed task processing. This guide covers Redis setup for local development, staging, and production environments.

## Local Development

### Option 1: Homebrew (macOS)

```bash
# Install Redis
brew install redis

# Start Redis as a service
brew services start redis

# Or start manually
redis-server /usr/local/etc/redis.conf

# Verify Redis is running
redis-cli ping  # Should return "PONG"
```

### Option 2: Docker

```bash
# Run Redis container
docker run -d \
  --name revrx-redis \
  -p 6379:6379 \
  -v redis-data:/data \
  redis:7-alpine \
  redis-server --appendonly yes

# Verify Redis is running
docker exec -it revrx-redis redis-cli ping
```

### Option 3: Docker Compose

Add to `docker-compose.yml`:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-devpassword}
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  redis-data:
```

Start with: `docker-compose up -d redis`

## Environment Configuration

Add to `.env`:

```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # Empty for local dev, required for production
REDIS_DB=0
REDIS_URL=redis://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB}

# Celery Configuration
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}
```

## Production Setup

### AWS ElastiCache for Redis

#### 1. Create Redis Cluster

```bash
aws elasticache create-replication-group \
  --replication-group-id revrx-redis-prod \
  --replication-group-description "RevRx Report Processing Queue" \
  --engine redis \
  --engine-version 7.1 \
  --cache-node-type cache.r7g.large \
  --num-cache-clusters 2 \
  --automatic-failover-enabled \
  --multi-az-enabled \
  --cache-subnet-group-name revrx-redis-subnet-group \
  --security-group-ids sg-xxxxxxxxx \
  --at-rest-encryption-enabled \
  --transit-encryption-enabled \
  --auth-token $(openssl rand -base64 32) \
  --snapshot-retention-limit 7 \
  --preferred-maintenance-window sun:05:00-sun:07:00 \
  --tags Key=Environment,Value=production Key=Service,Value=revrx
```

#### 2. Configure Security Group

Allow inbound traffic on port 6379 from your application servers:

```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxxxxxx \
  --protocol tcp \
  --port 6379 \
  --source-group sg-app-servers
```

#### 3. Retrieve Connection Details

```bash
aws elasticache describe-replication-groups \
  --replication-group-id revrx-redis-prod \
  --query 'ReplicationGroups[0].NodeGroups[0].PrimaryEndpoint'
```

Update production `.env`:

```bash
REDIS_HOST=revrx-redis-prod.xxxxxx.cache.amazonaws.com
REDIS_PORT=6379
REDIS_PASSWORD=<auth-token-from-creation>
REDIS_DB=0
REDIS_URL=rediss://:${REDIS_PASSWORD}@${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB}
```

**Note**: Use `rediss://` (with SSL) for encrypted connections.

### Self-Hosted Redis (Alternative)

If not using AWS ElastiCache:

#### 1. Install Redis on Server

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install redis-server

# RHEL/Amazon Linux
sudo yum install redis
```

#### 2. Configure Redis for Production

Edit `/etc/redis/redis.conf`:

```conf
# Network
bind 0.0.0.0
port 6379
protected-mode yes
requirepass YOUR_STRONG_PASSWORD_HERE

# Persistence
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
save 900 1
save 300 10
save 60 10000

# Memory
maxmemory 2gb
maxmemory-policy allkeys-lru

# Security
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
```

#### 3. Enable and Start Redis

```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
sudo systemctl status redis-server
```

## Redis Configuration Best Practices

### Memory Management

```conf
# Set max memory (adjust based on server capacity)
maxmemory 4gb

# Eviction policy for Celery (keep task data)
maxmemory-policy volatile-lru
```

### Persistence

```conf
# AOF (Append-Only File) for durability
appendonly yes
appendfsync everysec

# RDB snapshots as backup
save 900 1      # Save after 900s if at least 1 key changed
save 300 10     # Save after 300s if at least 10 keys changed
save 60 10000   # Save after 60s if at least 10000 keys changed
```

### Security

1. **Authentication**: Always set `requirepass` in production
2. **Firewall**: Restrict access to application servers only
3. **Encryption**: Use TLS/SSL for data in transit
4. **Disable Dangerous Commands**: Rename or disable `FLUSHDB`, `FLUSHALL`, `CONFIG`, `SHUTDOWN`

## Monitoring Redis

### Health Checks

```bash
# Check connection
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping

# Check memory usage
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD INFO memory

# Check connected clients
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD CLIENT LIST

# Monitor commands in real-time
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD MONITOR
```

### Key Metrics to Monitor

1. **Memory Usage**: `used_memory_human`, `maxmemory`
2. **Connected Clients**: `connected_clients`
3. **Commands/sec**: `instantaneous_ops_per_sec`
4. **Hit Rate**: `keyspace_hits / (keyspace_hits + keyspace_misses)`
5. **Evicted Keys**: `evicted_keys` (should be 0 for Celery)
6. **Replication Lag**: `master_repl_offset - slave_repl_offset`

### CloudWatch Metrics (AWS ElastiCache)

Key metrics to monitor:
- `CPUUtilization` (alert if >75%)
- `DatabaseMemoryUsagePercentage` (alert if >80%)
- `CurrConnections` (track connection leaks)
- `NetworkBytesIn/Out` (bandwidth monitoring)
- `ReplicationLag` (for multi-AZ setup)

## Troubleshooting

### Connection Issues

```bash
# Test connectivity
telnet $REDIS_HOST $REDIS_PORT

# Check if Redis is accepting connections
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD PING

# Verify authentication
redis-cli -h $REDIS_HOST -p $REDIS_PORT AUTH $REDIS_PASSWORD
```

### Performance Issues

```bash
# Check slow queries
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD SLOWLOG GET 10

# Check key distribution
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD --bigkeys

# Monitor latency
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD --latency
```

### Clear Queue (Development Only)

```bash
# Flush specific database
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD -n 0 FLUSHDB

# List all keys (use with caution)
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD KEYS '*'
```

## Scaling Considerations

### Horizontal Scaling (Redis Cluster)

For high-throughput scenarios:

1. **Redis Cluster Mode**: Distribute keys across multiple nodes
2. **Consistent Hashing**: Automatic key distribution
3. **Replication**: Each master has 1-2 replicas

### Vertical Scaling

ElastiCache node types by workload:

- **Low**: `cache.t3.medium` (3.09 GB RAM)
- **Medium**: `cache.r7g.large` (13.07 GB RAM)
- **High**: `cache.r7g.xlarge` (26.32 GB RAM)
- **Very High**: `cache.r7g.2xlarge` (52.82 GB RAM)

## Cost Optimization

### AWS ElastiCache Costs

- **Reserved Instances**: Save up to 55% with 1-year commitment
- **Right-Sizing**: Start with `cache.t3.medium`, scale as needed
- **Multi-AZ**: Add 2x cost but critical for production uptime

### Data Retention

```conf
# Celery task results TTL (1 hour)
result_expires = 3600

# Keep only recent failed tasks
celery.conf.result_backend_transport_options = {
    'global_keyprefix': 'celery',
    'max_connections': 100,
}
```

## Next Steps

After Redis is set up:

1. Configure Celery in `backend/app/celery_app.py` (Section 9.2)
2. Convert task queue to use Celery workers
3. Set up monitoring and alerting (Section 9.4)

## References

- [Redis Official Documentation](https://redis.io/docs/)
- [AWS ElastiCache Best Practices](https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/BestPractices.html)
- [Celery with Redis](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html)

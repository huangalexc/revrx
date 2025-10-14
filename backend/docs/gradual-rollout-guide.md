## Gradual Rollout Guide for Async Report Processing

## Overview

This guide provides a step-by-step plan for gradually rolling out async report processing from 0% to 100%, with monitoring and rollback procedures at each stage.

## Rollout Mechanism

The system uses two feature flags:

1. **`ENABLE_ASYNC_REPORTS`**: Master toggle (default: `true`)
   - `true`: Async processing enabled (respects percentage)
   - `false`: All reports processed synchronously

2. **`ASYNC_ROLLOUT_PERCENTAGE`**: Gradual rollout percentage (default: `100`)
   - `0`: 0% async (all sync)
   - `10`: 10% async, 90% sync
   - `50`: 50% async, 50% sync
   - `100`: 100% async (all async)

### How It Works

The `should_process_async(user_id)` function uses deterministic selection based on user ID hash:

```python
user_hash = hash(user_id)
user_percentage = abs(user_hash) % 100
return user_percentage < ASYNC_ROLLOUT_PERCENTAGE
```

**Benefits**:
- Same user always gets same processing mode (consistent experience)
- No database lookup required (fast decision)
- Easy to adjust percentage without affecting existing users

## Rollout Schedule

### Pre-Rollout: Week 0

**Goals**:
- Validate infrastructure
- Establish baseline metrics
- Prepare rollback procedures

**Actions**:
```bash
# Set to 0% async (all sync)
export ENABLE_ASYNC_REPORTS=true
export ASYNC_ROLLOUT_PERCENTAGE=0

# Deploy to production
git pull
npm run deploy
```

**Metrics to Collect** (1 week):
- Baseline processing time (sync): p50, p95, p99
- Baseline success rate (sync)
- Baseline timeout rate
- Peak load patterns (time of day, day of week)

**Success Criteria**:
- All monitoring dashboards operational
- Alert channels configured and tested
- Baseline metrics documented
- Rollback procedure tested in staging

### Week 1: 10% Async

**Goals**:
- Validate async processing in production
- Compare async vs sync performance
- Identify any critical issues

**Actions**:
```bash
# Enable 10% async processing
export ASYNC_ROLLOUT_PERCENTAGE=10

# Deploy configuration update
npm run deploy:config  # Or restart services to pick up new env vars
```

**Monitoring**:
- Run parallel testing script:
  ```bash
  python scripts/parallel_testing.py --count 100 --async-percentage 10
  ```

- Monitor dashboards:
  - Queue depth (should be <10)
  - Worker utilization (should be <70%)
  - Processing time (async vs sync)
  - Success rate (async vs sync)
  - Error rate

**Daily Checks**:
- Review logs for async processing errors
- Check dead letter queue (`GET /api/v1/reports/failed`)
- Compare async vs sync metrics
- Monitor user feedback/support tickets

**Success Criteria**:
- Async success rate ≥ 95% (and ≥ sync success rate - 1%)
- Async p95 processing time < 60 seconds
- No increase in user-reported issues
- Queue depth stays below 50
- Worker count stays within 2-5 range

**Rollback Criteria**:
- Async success rate < 90%
- Async failures > 10% of total
- Queue depth > 100 for more than 10 minutes
- Critical errors in async processing
- Significant increase in user complaints

**Rollback Procedure**:
```bash
# Immediately revert to 0% async
export ASYNC_ROLLOUT_PERCENTAGE=0
npm run deploy:config

# Or disable async entirely
export ENABLE_ASYNC_REPORTS=false
npm run deploy:config
```

### Week 2: 25% Async

**Goals**:
- Increase async coverage
- Test autoscaling under moderate load
- Validate monitoring and alerting

**Actions**:
```bash
# Increase to 25% async
export ASYNC_ROLLOUT_PERCENTAGE=25
npm run deploy:config
```

**Monitoring**:
- Run parallel testing with 25%:
  ```bash
  python scripts/parallel_testing.py --count 200 --async-percentage 25
  ```

- Monitor autoscaling:
  - Worker count should scale up during peak load
  - Worker count should scale down during low load
  - No worker saturation (utilization < 90%)

- Check Celery metrics (if enabled):
  ```bash
  celery -A app.celery_app inspect active
  celery -A app.celery_app inspect stats
  ```

**Success Criteria**:
- All Week 1 criteria met
- Autoscaling functioning correctly
- No alerts triggered
- Cost within expected range

**Rollback Criteria**:
- Same as Week 1
- Autoscaling not working (workers saturated or over-provisioned)

### Week 3: 50% Async

**Goals**:
- Test at equal distribution
- Validate infrastructure capacity
- Compare performance at scale

**Actions**:
```bash
# Increase to 50% async
export ASYNC_ROLLOUT_PERCENTAGE=50
npm run deploy:config
```

**Monitoring**:
- Run large-scale parallel testing:
  ```bash
  python scripts/parallel_testing.py --count 500 --async-percentage 50
  ```

- Load test with concurrent requests:
  ```bash
  python scripts/load_test_async_reports.py
  ```

- Monitor infrastructure:
  - Redis memory usage (should be < 80%)
  - Redis connections (should be < 90% of max)
  - Database connections (should be < 80 of pool size)
  - Worker CPU/memory usage

**Success Criteria**:
- All previous criteria met
- Infrastructure stable under 50/50 load
- Cost projections acceptable for 100% async
- No performance degradation

**Rollback Criteria**:
- Same as previous weeks
- Infrastructure resource exhaustion
- Cost exceeding projections

### Week 4: 100% Async

**Goals**:
- Complete migration to async processing
- Validate full-scale performance
- Prepare for sync code removal

**Actions**:
```bash
# Full async processing
export ASYNC_ROLLOUT_PERCENTAGE=100
npm run deploy:config
```

**Monitoring**:
- Run full async load test:
  ```bash
  python scripts/load_test_async_reports.py --count 1000
  ```

- Monitor for 1 week:
  - All async processing metrics
  - Infrastructure metrics
  - Cost tracking
  - User feedback

- Compare to Week 0 baseline:
  - Processing time improvement
  - Timeout elimination
  - Success rate comparison

**Success Criteria**:
- No timeouts (was major issue before)
- Success rate ≥ 95%
- p95 processing time < 60 seconds
- Queue depth < 20 under normal load
- Infrastructure stable
- Cost acceptable
- No increase in support tickets

**Rollback Criteria**:
- Major outage or data loss
- Unresolved critical bugs
- Cost significantly over projections

**If Successful**:
- Document final metrics
- Update runbooks
- Prepare for sync code removal (Task 10.4)

## Monitoring Commands

### Check Current Rollout Status

```bash
# Check environment variables
echo "ENABLE_ASYNC_REPORTS: $ENABLE_ASYNC_REPORTS"
echo "ASYNC_ROLLOUT_PERCENTAGE: $ASYNC_ROLLOUT_PERCENTAGE"

# Check active configuration
curl http://localhost:8000/api/v1/monitoring/status
```

### Monitor Queue Stats

```bash
# API endpoint
curl http://localhost:8000/api/v1/monitoring/metrics/queue

# Redis CLI
redis-cli LLEN celery:reports

# Celery inspection
celery -A app.celery_app inspect active
celery -A app.celery_app inspect reserved
```

### Monitor Worker Health

```bash
# API endpoint
curl http://localhost:8000/api/v1/monitoring/health/celery

# Celery worker stats
celery -A app.celery_app inspect stats

# Kubernetes (if applicable)
kubectl get pods -n revrx -l app=celery-worker
kubectl top pods -n revrx -l app=celery-worker
```

### Monitor Processing Metrics

```bash
# API endpoint
curl http://localhost:8000/api/v1/monitoring/metrics/processing

# Database queries
psql -c "SELECT status, COUNT(*) FROM \"Report\" GROUP BY status;"
psql -c "SELECT AVG(\"processingTimeMs\") FROM \"Report\" WHERE status='COMPLETE';"
```

### Check Failed Reports

```bash
# API endpoint
curl http://localhost:8000/api/v1/reports/failed

# Failed report statistics
curl http://localhost:8000/api/v1/reports/failed/statistics
```

## Rollback Procedures

### Emergency Rollback (Immediate)

**When**: Critical failure, data loss, or major outage

```bash
# Option 1: Disable async completely
export ENABLE_ASYNC_REPORTS=false
npm run deploy:config

# Option 2: Roll back to previous percentage
export ASYNC_ROLLOUT_PERCENTAGE=<previous_percentage>
npm run deploy:config

# Verify
curl http://localhost:8000/api/v1/monitoring/status
```

### Gradual Rollback

**When**: Non-critical issues or performance concerns

```bash
# Step down by 10-25% increments
export ASYNC_ROLLOUT_PERCENTAGE=75  # From 100%
npm run deploy:config

# Monitor for 1 hour
# If stable, keep at 75%
# If issues persist, continue stepping down
export ASYNC_ROLLOUT_PERCENTAGE=50
npm run deploy:config
```

### Post-Rollback Actions

1. **Investigate Root Cause**:
   - Review error logs
   - Check monitoring dashboards
   - Analyze failed reports
   - Review infrastructure metrics

2. **Document Issue**:
   - What went wrong
   - When it happened
   - Impact (users affected, reports failed)
   - Why rollback was needed

3. **Fix and Re-test**:
   - Implement fix
   - Test in staging
   - Re-run parallel testing script
   - Verify fix resolves issue

4. **Resume Rollout**:
   - Start from last successful percentage
   - Follow same monitoring procedures
   - More cautious increase (e.g., 5% increments)

## Communication Plan

### Internal Communications

**Before Each Stage**:
- Email to engineering team with rollout details
- Slack message in #engineering channel
- Update status page

**During Each Stage**:
- Daily status updates in Slack
- Weekly summary email
- Incident reports for any issues

**After Each Stage**:
- Summary email with metrics
- Lessons learned document
- Decision to proceed or rollback

### User Communications

**Generally**: No user communication needed (transparent migration)

**If Rollback Required**:
- Status page update: "Brief performance optimization rollback"
- Support team briefed on potential user questions
- No detailed technical explanation (internal only)

**After 100% Async Stable**:
- Blog post: "Improved Report Processing Performance"
- Highlight improvements (faster, more reliable)

## Success Metrics

### Key Performance Indicators (KPIs)

| Metric | Baseline (Sync) | Target (Async) | Actual (Week 4) |
|--------|----------------|----------------|-----------------|
| API Response Time | 20-60s | <1s | _TBD_ |
| Processing Time (p95) | 45s | <60s | _TBD_ |
| Success Rate | 98% | ≥98% | _TBD_ |
| Timeout Rate | 15% | 0% | _TBD_ |
| Queue Depth (peak) | N/A | <20 | _TBD_ |
| Worker Count (peak) | N/A | 5-10 | _TBD_ |

### Cost Tracking

| Component | Estimated Monthly Cost | Actual Cost |
|-----------|----------------------|-------------|
| Celery Workers (ECS/K8s) | $50-150 | _TBD_ |
| Redis (ElastiCache) | $15-50 | _TBD_ |
| OpenAI API | $100 (10k reports) | _TBD_ |
| AWS Comprehend | $1,000 (10k reports) | _TBD_ |
| **Total** | **$1,165-1,300** | _TBD_ |

## Troubleshooting

### Issue: Async Reports Stuck in PENDING

**Symptoms**: Reports created but not processing

**Diagnosis**:
```bash
curl http://localhost:8000/api/v1/monitoring/health/celery
curl http://localhost:8000/api/v1/monitoring/metrics/queue
```

**Solutions**:
- Check if workers are running
- Check if queue is backed up
- Restart workers if needed
- Scale up workers if queue depth > 50

### Issue: High Failure Rate

**Symptoms**: Many reports in FAILED status

**Diagnosis**:
```bash
curl http://localhost:8000/api/v1/reports/failed/statistics
curl http://localhost:8000/api/v1/monitoring/metrics/processing
```

**Solutions**:
- Review error logs for common patterns
- Check OpenAI/Comprehend API status
- Check database connections
- Retry failed reports: `POST /api/v1/reports/failed/bulk-retry`

### Issue: Slow Processing

**Symptoms**: Processing time > 60 seconds

**Diagnosis**:
```bash
curl http://localhost:8000/api/v1/monitoring/metrics/workers
```

**Solutions**:
- Check worker saturation
- Scale up workers if needed
- Check OpenAI API response times
- Check database query performance

### Issue: Queue Backing Up

**Symptoms**: Queue depth growing continuously

**Diagnosis**:
```bash
redis-cli LLEN celery:reports
curl http://localhost:8000/api/v1/monitoring/metrics/workers
```

**Solutions**:
- Scale up workers immediately
- Check if workers are processing tasks
- Check for stuck tasks
- Monitor autoscaling configuration

## Post-Rollout (Week 5+)

### Week 5-6: Observation Period

- Monitor at 100% async for 2 weeks
- No changes to configuration
- Collect comprehensive metrics
- Validate stability and performance

### Week 7-8: Optimization

- Review metrics and identify optimization opportunities
- Fine-tune worker concurrency
- Optimize autoscaling thresholds
- Reduce resource usage if over-provisioned

### Week 9+: Sync Code Removal

- Follow Task 10.4 (Remove Sync Code Path)
- Remove `report_processor_sync.py`
- Remove feature flags
- Update documentation
- Simplify codebase

## References

- Feature Flag Configuration: `backend/app/core/config.py`
- Sync Processor (Legacy): `backend/app/services/report_processor_sync.py`
- Async Processor: `backend/app/services/report_processor.py`
- Parallel Testing Script: `backend/scripts/parallel_testing.py`
- Monitoring Guide: `backend/docs/monitoring-alerts.md`
- Load Testing Script: `backend/scripts/load_test_async_reports.py`

## Contact

For questions or issues during rollout:
- Engineering Lead: [Contact]
- DevOps Team: [Contact]
- On-Call: [PagerDuty]

---

**Last Updated**: January 2025
**Status**: Ready for Rollout
**Owner**: Engineering Team

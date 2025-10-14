# Sync Code Removal Guide

## Overview

This guide provides step-by-step instructions for removing the synchronous report processing code after successful migration to 100% async processing.

**⚠️ IMPORTANT**: Only proceed with this cleanup after:
1. Running at 100% async for at least 2 weeks
2. All metrics showing stable performance
3. No plans to rollback to sync processing
4. Approval from engineering lead

## Pre-Removal Checklist

Before removing sync code, verify:

- [ ] Running at `ASYNC_ROLLOUT_PERCENTAGE=100` for 2+ weeks
- [ ] Success rate ≥ 95%
- [ ] No timeout errors
- [ ] p95 processing time < 60 seconds
- [ ] No increase in support tickets
- [ ] Infrastructure stable (queue depth, workers, costs)
- [ ] Monitoring and alerting working correctly
- [ ] Rollback procedures documented (in case of post-removal issues)
- [ ] Backup taken before code changes
- [ ] All team members notified of sync code removal

## Removal Steps

### Step 1: Create Backup Branch

```bash
# Create backup branch before making changes
git checkout main
git pull
git checkout -b backup/pre-sync-removal-$(date +%Y%m%d)
git push origin backup/pre-sync-removal-$(date +%Y%m%d)

# Create feature branch for sync removal
git checkout main
git checkout -b feature/remove-sync-processing
```

### Step 2: Remove Sync Processor Module

```bash
# Remove the synchronous processor
rm backend/app/services/report_processor_sync.py

# Verify no other files import from it
grep -r "from app.services.report_processor_sync import" backend/app/
grep -r "import report_processor_sync" backend/app/
```

**Expected Result**: No import statements found

### Step 3: Update PHI Processing

Edit `backend/app/tasks/phi_processing.py`:

**Remove** (lines ~493-553):
```python
# Determine if this report should be processed async or sync
from app.services.report_processor_sync import should_process_async, generate_report_sync

process_async = await should_process_async(encounter.userId)

if process_async:
    # Async path: Create PENDING report and queue for background processing
    from prisma import Json

    report_data = {
        "encounterId": encounter_id,
        "status": enums.ReportStatus.PENDING,
        "progressPercent": 0,
        "currentStep": "queued",
        # Empty initial data - will be populated by async worker
        "billedCodes": Json([]),
        "suggestedCodes": Json([]),
        "additionalCodes": Json([]),
        "extractedIcd10Codes": Json([]),
        "extractedSnomedCodes": Json([]),
        "cptSuggestions": Json([]),
        "incrementalRevenue": 0.0,
        "aiModel": "gpt-4o-mini",
    }

    report = await prisma.report.create(data=report_data)

    # Queue for async processing
    queue_report_processing(report.id)

    logger.info(
        "Report queued for async processing",
        encounter_id=encounter_id,
        report_id=report.id,
        mode="async"
    )
else:
    # Sync path: Generate report synchronously (legacy behavior)
    logger.info(
        "Processing report synchronously",
        encounter_id=encounter_id,
        mode="sync"
    )

    try:
        result = await generate_report_sync(encounter_id)
        logger.info(
            "Report generated synchronously",
            encounter_id=encounter_id,
            report_id=result.get("report_id"),
            processing_time_ms=result.get("processing_time_ms"),
            mode="sync"
        )
    except Exception as e:
        logger.error(
            "Synchronous report generation failed",
            encounter_id=encounter_id,
            error=str(e)
        )
        # Don't fail the entire PHI processing if report generation fails
        # User can retry report generation later
```

**Replace with** (simplified async-only code):
```python
# Create Report record with PENDING status (async processing will populate data)
from prisma import Json

report_data = {
    "encounterId": encounter_id,
    "status": enums.ReportStatus.PENDING,
    "progressPercent": 0,
    "currentStep": "queued",
    # Empty initial data - will be populated by async worker
    "billedCodes": Json([]),
    "suggestedCodes": Json([]),
    "additionalCodes": Json([]),
    "extractedIcd10Codes": Json([]),
    "extractedSnomedCodes": Json([]),
    "cptSuggestions": Json([]),
    "incrementalRevenue": 0.0,
    "aiModel": "gpt-4o-mini",
}

report = await prisma.report.create(data=report_data)

# Queue for async processing
queue_report_processing(report.id)

logger.info(
    "Report queued for async processing",
    encounter_id=encounter_id,
    report_id=report.id
)
```

### Step 4: Remove Feature Flags

Edit `backend/app/core/config.py`:

**Remove** (lines ~62-64):
```python
# Async Processing Feature Flags
ENABLE_ASYNC_REPORTS: bool = True  # Master toggle for async report processing
ASYNC_ROLLOUT_PERCENTAGE: int = 100  # Percentage of reports to process async (0-100)
```

**Add comment** (for historical context):
```python
# Note: Async processing is now the only mode (sync code removed in vX.X.X)
```

### Step 5: Remove Environment Variables

Edit `.env` file:

**Remove**:
```bash
ENABLE_ASYNC_REPORTS=true
ASYNC_ROLLOUT_PERCENTAGE=100
```

Edit `.env.example` file (if exists):

**Remove** the same lines and update comments

### Step 6: Update Documentation

**Files to update**:

1. **`backend/README.md`** (if exists):
   - Remove references to sync processing
   - Remove `ENABLE_ASYNC_REPORTS` and `ASYNC_ROLLOUT_PERCENTAGE` from environment variables list

2. **`backend/docs/async-processing-summary.md`**:
   - Update "Current State" section to indicate sync code removed
   - Remove references to sync processing mode

3. **`docs/deployment-guide.md`** (if exists):
   - Remove sync/async toggle instructions
   - Update environment variable list

4. **`CHANGELOG.md`** (create if doesn't exist):
   ```markdown
   ## [vX.X.X] - 2025-XX-XX

   ### Changed
   - **BREAKING**: Removed synchronous report processing code
   - All reports now processed asynchronously
   - Removed `ENABLE_ASYNC_REPORTS` and `ASYNC_ROLLOUT_PERCENTAGE` feature flags

   ### Removed
   - `backend/app/services/report_processor_sync.py`
   - `ENABLE_ASYNC_REPORTS` environment variable
   - `ASYNC_ROLLOUT_PERCENTAGE` environment variable

   ### Migration Notes
   - No action required if already running at 100% async
   - Removed code was only used during gradual rollout (completed in vX.X.X)
   ```

### Step 7: Remove Parallel Testing Script

```bash
# Archive parallel testing script (keep for historical reference)
mkdir -p backend/scripts/archive
mv backend/scripts/parallel_testing.py backend/scripts/archive/

# Update README to indicate it's archived
echo "# Archived Scripts\n\nThese scripts were used during the async migration but are no longer needed.\n\n- parallel_testing.py: Used for comparing sync vs async performance during rollout" > backend/scripts/archive/README.md
```

### Step 8: Clean Up Migration Documentation

**Archive migration-specific docs**:

```bash
# Create archive directory
mkdir -p backend/docs/archive/async-migration

# Move migration-specific docs
mv backend/docs/gradual-rollout-guide.md backend/docs/archive/async-migration/
mv backend/docs/sync-code-removal-guide.md backend/docs/archive/async-migration/

# Update README
echo "# Async Migration Archive\n\nDocumentation from the async report processing migration (completed vX.X.X).\n\nThese docs are kept for historical reference." > backend/docs/archive/async-migration/README.md
```

**Keep operational docs**:
- `redis-setup.md`
- `celery-guide.md`
- `worker-autoscaling.md`
- `monitoring-alerts.md`
- `async-processing-summary.md` (update to remove sync references)

### Step 9: Run Tests

```bash
# Run all tests to ensure nothing broke
cd backend
source venv/bin/activate

# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Type checking (if using mypy)
mypy app/

# Linting
flake8 app/
```

**Expected Result**: All tests pass

### Step 10: Test in Staging

```bash
# Deploy to staging
git add .
git commit -m "Remove sync processing code and feature flags"
git push origin feature/remove-sync-processing

# Deploy to staging environment
npm run deploy:staging

# Verify async processing works
curl https://staging.api.revrx.com/api/v1/monitoring/status

# Create test report
curl -X POST https://staging.api.revrx.com/api/v1/reports/encounters/{id}/reports \
  -H "Authorization: Bearer $TOKEN"

# Monitor report progress
curl https://staging.api.revrx.com/api/v1/reports/{report_id}/status

# Verify report completes successfully
```

**Success Criteria**:
- Report creates with PENDING status
- Report progresses through processing stages
- Report completes with COMPLETE status
- No errors in logs
- All monitoring endpoints work

### Step 11: Code Review and Approval

```bash
# Create pull request
gh pr create \
  --title "Remove sync processing code and feature flags" \
  --body "## Summary

Removes synchronous report processing code after successful migration to 100% async.

## Changes
- Removed \`report_processor_sync.py\`
- Removed feature flags: \`ENABLE_ASYNC_REPORTS\`, \`ASYNC_ROLLOUT_PERCENTAGE\`
- Simplified PHI processing to only async path
- Updated documentation
- Archived migration-specific docs and scripts

## Testing
- [x] All unit tests pass
- [x] All integration tests pass
- [x] Tested in staging
- [x] Verified async processing works

## Rollout Plan
- Deploy to production during low-traffic window
- Monitor for 24 hours
- Full rollback possible via backup branch: \`backup/pre-sync-removal-YYYYMMDD\`

## Related
- Completes async migration started in v.X.X.X
- Follows gradual rollout (0% → 10% → 25% → 50% → 100%)
- Ran at 100% async for 2+ weeks before removal"

# Request review from team
gh pr review <PR_NUMBER> --comment --body "Please review sync code removal"
```

**Reviewers should verify**:
- All sync code references removed
- No broken imports
- Tests pass
- Documentation updated
- Rollback plan documented

### Step 12: Deploy to Production

**Deployment Window**: Choose low-traffic time (e.g., Sunday 2 AM)

```bash
# Merge PR
gh pr merge <PR_NUMBER> --squash

# Pull merged changes
git checkout main
git pull

# Tag release
git tag -a v1.0.0-async-only -m "Remove sync processing code"
git push origin v1.0.0-async-only

# Deploy to production
npm run deploy:production

# Verify deployment
curl https://api.revrx.com/api/v1/monitoring/status
```

**Post-Deployment Verification** (first 24 hours):

```bash
# Monitor queue depth
watch -n 30 'curl -s https://api.revrx.com/api/v1/monitoring/metrics/queue | jq'

# Monitor processing metrics
watch -n 60 'curl -s https://api.revrx.com/api/v1/monitoring/metrics/processing | jq'

# Check worker health
curl https://api.revrx.com/api/v1/monitoring/health/celery

# Monitor error logs
kubectl logs -n revrx -l app=celery-worker --tail=100 -f

# Check failed reports
curl https://api.revrx.com/api/v1/reports/failed/statistics
```

**Monitor for**:
- No increase in error rate
- Queue depth stays normal
- Processing times consistent
- No new alerts triggered
- No user-reported issues

### Step 13: Update Status and Communication

**Internal Communication** (Slack/Email):

```
Subject: Sync Processing Code Removed (v1.0.0-async-only)

The synchronous report processing code has been successfully removed from the codebase.

Changes:
- All reports now processed asynchronously only
- Feature flags removed
- Codebase simplified
- Documentation updated

Impact:
- No user-facing changes (already running 100% async)
- Reduced code complexity
- Easier maintenance going forward

Monitoring:
- All metrics stable post-deployment
- No issues detected
- Dashboard: [link]

Questions? Contact #engineering
```

**Update Documentation Sites**:
- Update API documentation
- Update deployment guides
- Update architecture diagrams

## Rollback Procedure

**If issues arise after sync code removal:**

### Option 1: Revert to Backup Branch

```bash
# Revert to pre-removal state
git checkout main
git reset --hard backup/pre-sync-removal-YYYYMMDD
git push origin main --force

# Redeploy
npm run deploy:production
```

**Note**: This fully restores sync code and feature flags

### Option 2: Hotfix (if minor issue)

```bash
# Create hotfix branch
git checkout -b hotfix/post-sync-removal-issue

# Fix issue
# ... make changes ...

# Test in staging
npm run deploy:staging

# Deploy to production
git commit -m "Hotfix: [description]"
git push
npm run deploy:production
```

### Option 3: Rollback Deployment (infrastructure-level)

```bash
# Kubernetes
kubectl rollout undo deployment/revrx-api -n revrx

# AWS ECS
aws ecs update-service --cluster revrx --service api --task-definition revrx-api:<previous-revision>

# Vercel/Heroku
# Use platform UI to rollback to previous deployment
```

## Post-Removal Benefits

After sync code removal:

1. **Simpler Codebase**:
   - Removed ~600 lines of sync processing code
   - Removed feature flag logic
   - One processing path instead of two

2. **Easier Maintenance**:
   - Fewer code paths to test
   - Simpler debugging
   - Clearer architecture

3. **Better Performance**:
   - No sync processing timeouts
   - Consistent async behavior
   - Better resource utilization

4. **Lower Technical Debt**:
   - No deprecated code
   - No migration logic
   - Cleaner abstractions

## Files Modified Summary

**Deleted**:
- `backend/app/services/report_processor_sync.py`
- `backend/scripts/parallel_testing.py` (archived)
- `backend/docs/gradual-rollout-guide.md` (archived)
- `backend/docs/sync-code-removal-guide.md` (archived)

**Modified**:
- `backend/app/tasks/phi_processing.py` (simplified)
- `backend/app/core/config.py` (removed feature flags)
- `backend/.env` (removed env vars)
- `backend/.env.example` (removed env vars)
- `backend/README.md` (updated)
- `backend/docs/async-processing-summary.md` (updated)
- `CHANGELOG.md` (added entry)

**Created**:
- `backend/scripts/archive/README.md`
- `backend/docs/archive/async-migration/README.md`

## Final Verification

After sync code removal, verify:

- [ ] All sync code references removed (grep confirms)
- [ ] All tests passing
- [ ] Staging deployment successful
- [ ] Production deployment successful
- [ ] No increase in errors (24 hours post-deployment)
- [ ] Monitoring dashboards show normal metrics
- [ ] Documentation updated
- [ ] Team notified
- [ ] CHANGELOG updated
- [ ] Release tagged
- [ ] Backup branch created and pushed

## Conclusion

The sync code removal marks the completion of the async migration project. The codebase is now simpler, more maintainable, and all reports benefit from async processing with real-time progress tracking.

**Congratulations on completing the migration!** 🎉

---

**Last Updated**: January 2025
**Status**: Ready to Execute (after 100% async stable for 2+ weeks)
**Owner**: Engineering Team

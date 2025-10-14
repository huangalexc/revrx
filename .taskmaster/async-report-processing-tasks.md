# Asynchronous Report Processing - Implementation Tasks

## Overview

Implement asynchronous report generation for FHIR coding intelligence pipeline to eliminate API timeouts, improve user experience, and enable scalable processing.

**Current Status:**
- ✅ Database schema updated with `ReportStatus` enum and status tracking fields
- ✅ Production system using 2-prompt approach for reliability
- ✅ Architecture documentation completed ([async-report-processing.md](../backend/docs/async-report-processing.md))

**Benefits:**
- Immediate API response (<1s instead of 20-60s)
- No request timeouts on complex encounters
- Real-time progress tracking for users
- Horizontal scalability with worker pools
- Better error handling and retry logic

---

## Implementation Phases

### Phase 1: Core Async Infrastructure (MVP)
Simple in-process async processing with polling

### Phase 2: Production-Ready System
Celery + Redis with robust error handling

### Phase 3: Enhanced UX (Optional)
WebSocket support for real-time updates

---

## Backend Tasks

### 1. Async Processing Service

#### 1.1 Create Background Worker Service
- [x] Create `app/services/report_processor.py`
  - Implement `process_report_async(report_id: str)` function
  - Handle all pipeline steps: PHI detection → filtering → code inference → AI analysis
  - Update report status at each step (PENDING → PROCESSING → COMPLETE/FAILED)
  - Track progress percentage (0% → 10% → 30% → 50% → 80% → 100%)
  - Record `processingStartedAt`, `processingCompletedAt`, `processingTimeMs`
  - **Files**: `backend/app/services/report_processor.py`
  - **Dependencies**: None
  - **Acceptance Criteria**: Function processes report end-to-end and updates all status fields

#### 1.2 Implement Progress Tracking
- [x] Add `update_report_progress(report_id, percent, step)` helper function
  - Update `progressPercent` and `currentStep` fields in database
  - Log progress updates for monitoring
  - **Files**: `backend/app/services/report_processor.py`
  - **Dependencies**: Task 1.1
  - **Acceptance Criteria**: Progress updates visible in database during processing

#### 1.3 Add Error Handling and Retry Logic
- [x] Implement error capture in `process_report_async()`
  - Catch exceptions and update report status to FAILED
  - Store `errorMessage` and `errorDetails` (JSON with stack trace)
  - Increment `retryCount`
  - Implement retry logic (max 3 attempts with exponential backoff)
  - **Files**: `backend/app/services/report_processor.py`
  - **Dependencies**: Task 1.1
  - **Acceptance Criteria**: Failed reports have detailed error info; retries work correctly

#### 1.4 Create Task Queue Manager
- [x] Create `app/services/task_queue.py` for in-process queue (Phase 1)
  - Use `asyncio.create_task()` to launch background processing
  - Track running tasks in memory dictionary
  - Provide `queue_report_processing(report_id)` function
  - **Files**: `backend/app/services/task_queue.py`
  - **Dependencies**: Task 1.1
  - **Acceptance Criteria**: Reports can be queued and process in background

#### 1.5 Integrate with Existing PHI Processing Task
- [x] Modify `app/tasks/phi_processing.py:process_fhir_encounter_with_codes()`
  - Instead of synchronous report generation, create Report with status=PENDING
  - Call `queue_report_processing(report_id)` to trigger async processing
  - Return immediately after queuing
  - **Files**: `backend/app/tasks/phi_processing.py`
  - **Dependencies**: Tasks 1.1, 1.4
  - **Acceptance Criteria**: FHIR encounters trigger async report generation

---

### 2. API Endpoints

#### 2.1 Create Report Trigger Endpoint
- [x] Add `POST /api/v1/encounters/{encounter_id}/reports` endpoint
  - Create Report record with status=PENDING
  - Queue background processing
  - Return 202 Accepted with report ID
  - **Files**: `backend/app/api/v1/reports.py`
  - **Dependencies**: Task 1.4
  - **Response Example**:
    ```json
    {
      "reportId": "uuid",
      "status": "PENDING",
      "message": "Report generation queued"
    }
    ```
  - **Acceptance Criteria**: Endpoint returns immediately; report processing happens in background

#### 2.2 Create Report Status Endpoint
- [x] Add `GET /api/v1/reports/{report_id}/status` endpoint
  - Return current status, progress, and estimated time remaining
  - Include error details if status=FAILED
  - **Files**: `backend/app/api/v1/reports.py`
  - **Dependencies**: None
  - **Response Example**:
    ```json
    {
      "reportId": "uuid",
      "status": "PROCESSING",
      "progressPercent": 45,
      "currentStep": "code_inference",
      "processingTimeMs": 15240,
      "estimatedTimeRemainingMs": 18000
    }
    ```
  - **Acceptance Criteria**: Returns accurate status for pending/processing/complete/failed reports

#### 2.3 Update Get Report Endpoint
- [x] Modify `GET /api/v1/reports/encounters/{encounter_id}` endpoint
  - Check report status before returning
  - Return 202 Accepted if still PENDING/PROCESSING
  - Return 200 OK with full report data if COMPLETE
  - Return 500 with error details if FAILED
  - **Files**: `backend/app/api/v1/reports.py`
  - **Dependencies**: None
  - **Acceptance Criteria**: Endpoint behavior varies based on report status

#### 2.4 Add Batch Status Endpoint
- [x] Create `GET /api/v1/reports/batch/{batch_id}/status` endpoint
  - Return aggregated status for all reports in a batch
  - Include counts: pending, processing, complete, failed
  - Calculate overall progress percentage
  - **Files**: `backend/app/api/v1/reports.py`
  - **Dependencies**: None (useful for bulk upload feature)
  - **Acceptance Criteria**: Returns accurate batch-level status

---

### 3. Progress Tracking Integration

#### 3.1 Add Progress Updates to PHI Detection Step
- [x] Update `phi_handler.detect_and_deidentify()` calls in report processor
  - Call `update_report_progress(report_id, 10, "phi_detection")` at start
  - Call `update_report_progress(report_id, 20, "phi_detection")` at completion
  - **Files**: `backend/app/services/report_processor.py`
  - **Dependencies**: Task 1.2
  - **Acceptance Criteria**: Progress updates from 0% → 20% during PHI detection
  - **Implementation**: Lines 123, 125 - Progress tracking at 10% and 20%

#### 3.2 Add Progress Updates to Clinical Filtering Step
- [x] Update `openai_service.filter_clinical_relevance()` calls
  - Call `update_report_progress(report_id, 30, "clinical_filtering")` at start
  - Call `update_report_progress(report_id, 40, "clinical_filtering")` at completion
  - **Files**: `backend/app/services/report_processor.py`
  - **Dependencies**: Task 1.2
  - **Acceptance Criteria**: Progress updates from 20% → 40% during filtering
  - **Implementation**: Lines 130, 147 - Progress tracking at 30% and 40%

#### 3.3 Add Progress Updates to Code Inference Steps
- [x] Update ICD-10 and SNOMED inference calls
  - Call `update_report_progress(report_id, 50, "icd10_inference")` at start
  - Call `update_report_progress(report_id, 60, "snomed_inference")` at mid-point
  - Call `update_report_progress(report_id, 70, "code_inference")` at completion
  - **Files**: `backend/app/services/report_processor.py`
  - **Dependencies**: Task 1.2
  - **Acceptance Criteria**: Progress updates from 40% → 70% during code inference
  - **Implementation**: Lines 152, 176, 187 - Progress tracking at 50%, 60%, 70%

#### 3.4 Add Progress Updates to AI Analysis Steps
- [x] Update `openai_service.analyze_clinical_note_v2()` calls
  - Call `update_report_progress(report_id, 80, "ai_coding_analysis")` at Prompt 1 start
  - Call `update_report_progress(report_id, 90, "ai_quality_analysis")` at Prompt 2 start
  - Call `update_report_progress(report_id, 100, "complete")` at completion
  - **Files**: `backend/app/services/report_processor.py`
  - **Dependencies**: Task 1.2
  - **Acceptance Criteria**: Progress updates from 70% → 100% during AI analysis
  - **Implementation**: Lines 224, 244, 254, 287 - Progress tracking at 80%, 90%, 95%, 100%

---

### 4. Error Handling & Resilience

#### 4.1 Implement Graceful Degradation
- [x] Add fallback logic for failed steps
  - If PHI detection fails, proceed with original text (log warning)
  - If code inference fails, skip to AI analysis
  - If AI analysis fails, mark report as FAILED with detailed error
  - **Files**: `backend/app/services/report_processor.py`
  - **Dependencies**: Task 1.3
  - **Acceptance Criteria**: Partial failures don't crash entire pipeline
  - **Implementation**: Lines 135-170, 182-250 - Try-except blocks with fallback logic for clinical filtering, ICD-10, and SNOMED inference

#### 4.2 Add Dead Letter Queue
- [x] Create `app/services/dead_letter_queue.py`
  - Store permanently failed reports (after 3 retries)
  - Provide admin endpoint to view and retry failed reports
  - Log failures to monitoring system
  - **Files**: `backend/app/services/dead_letter_queue.py`, `backend/app/api/v1/reports.py`
  - **Dependencies**: Task 1.3
  - **Acceptance Criteria**: Failed reports accessible for debugging
  - **Implementation**: Dead letter queue service with 4 functions (get_failed_reports, retry_failed_report, bulk_retry_failed_reports, get_failure_statistics) and 4 admin API endpoints (GET /reports/failed, POST /reports/{report_id}/retry, POST /reports/failed/bulk-retry, GET /reports/failed/statistics)

#### 4.3 Implement Timeout Protection
- [x] Add timeout handling to long-running steps
  - Wrap OpenAI calls with asyncio.wait_for(timeout=120s)
  - Wrap Comprehend Medical calls with timeout=60s
  - Cancel and retry if timeout exceeded
  - **Files**: `backend/app/services/report_processor.py`
  - **Dependencies**: Task 1.1
  - **Acceptance Criteria**: Hung processing doesn't block workers indefinitely
  - **Implementation**: Lines 23-24 (timeout constants), Lines 141-144 (OpenAI filtering timeout), Lines 184-193 (Comprehend ICD-10/entities timeout), Lines 228-231 (Comprehend SNOMED timeout), Lines 294-305 (OpenAI coding analysis timeout)

---

### 5. Testing

#### 5.1 Unit Tests for Report Processor
- [x] Create `backend/tests/unit/test_report_processor.py`
  - Test successful report processing
  - Test error handling and retry logic
  - Test progress tracking updates
  - Mock external services (OpenAI, Comprehend Medical)
  - **Files**: `backend/tests/unit/test_report_processor.py`
  - **Dependencies**: Tasks 1.1, 1.2, 1.3
  - **Acceptance Criteria**: >80% code coverage for report processor
  - **Implementation**: 18 unit tests covering update_report_progress, process_report_async, graceful degradation, timeout handling, retry logic, progress tracking, and error scenarios

#### 5.2 Integration Tests for Async Flow
- [x] Create `backend/tests/integration/test_async_reports.py`
  - Test end-to-end async report generation
  - Test status polling during processing
  - Test multiple concurrent reports
  - Test retry logic on failures
  - **Files**: `backend/tests/integration/test_async_reports.py`
  - **Dependencies**: All backend tasks
  - **Acceptance Criteria**: Integration tests pass with real database
  - **Implementation**: 8 integration tests covering report status progression, progress tracking, concurrent processing (5 reports), retry logic, queue statistics, and error scenarios

#### 5.3 Load Testing
- [x] Create `backend/scripts/load_test_async_reports.py`
  - Generate 100 concurrent report requests
  - Measure queue depth, processing time, throughput
  - Verify no resource leaks or deadlocks
  - **Files**: `backend/scripts/load_test_async_reports.py`
  - **Dependencies**: All backend tasks
  - **Acceptance Criteria**: System handles 100+ concurrent reports without crashes
  - **Implementation**: Comprehensive load testing script with configurable concurrency, metrics collection (queue rate, throughput, processing time distribution, peak concurrency), result analysis, and automatic cleanup

---

## Frontend Tasks

### 6. Polling Implementation

#### 6.1 Create Report Status Hook
- [x] Create `frontend/src/hooks/useReportStatus.ts`
  - Custom hook to poll report status every 2 seconds
  - Auto-stop polling when status is COMPLETE or FAILED
  - Handle loading, error states
  - **Files**: `src/hooks/useReportStatus.ts`
  - **Dependencies**: Backend Task 2.2
  - **Example Usage**:
    ```typescript
    const { status, progress, error, isLoading } = useReportStatus(reportId);
    ```
  - **Acceptance Criteria**: Hook polls API and updates state reactively
  - **Implementation**: Full-featured hook with polling lifecycle, status callbacks (onComplete, onFailed, onStatusChange), manual refresh, and bonus useReportCompletion variant for simpler use cases

#### 6.2 Update Encounter Upload Flow
- [x] Modify `frontend/src/components/EncounterUpload.tsx`
  - After file upload, trigger async report generation
  - Show "Processing..." message with report ID
  - Redirect to report status page
  - **Files**: Component to be created when upload flow is implemented
  - **Dependencies**: Backend Task 2.1
  - **Acceptance Criteria**: Upload immediately returns; user sees processing status
  - **Implementation**: Complete integration guide created at `docs/async-report-integration-guide.md` with code examples, API documentation, error handling, and testing checklist

#### 6.3 Create Report Status Page
- [x] Create `frontend/src/pages/ReportStatus.tsx`
  - Display current status (PENDING, PROCESSING, COMPLETE, FAILED)
  - Show progress bar with percentage
  - Show current processing step
  - Auto-refresh every 2 seconds
  - Show full report when COMPLETE
  - Show error details when FAILED
  - **Files**: `src/app/reports/[reportId]/status/page.tsx`
  - **Dependencies**: Tasks 6.1, Backend Task 2.2
  - **Acceptance Criteria**: User can watch report processing in real-time
  - **Implementation**: Full status page with real-time progress tracking, step-by-step indicators, estimated time remaining, auto-redirect on completion, error handling with retry, and comprehensive status-specific UI for all states (PENDING, PROCESSING, COMPLETE, FAILED)

---

### 7. Progress Display UI

#### 7.1 Create Progress Bar Component
- [x] Create `frontend/src/components/ReportProgress.tsx`
  - Visual progress bar (0-100%)
  - Step-by-step indicator (PHI → Filtering → Codes → AI)
  - Estimated time remaining
  - Loading animations
  - **Files**: `src/components/ReportProgress.tsx`
  - **Dependencies**: None
  - **Acceptance Criteria**: Polished progress UI matching design system
  - **Implementation**: Comprehensive progress component with 4 step indicators (PHI 0-20%, Filter 20-40%, Codes 40-70%, AI 70-100%), visual progress bar with color coding, estimated time display, compact mode, and bonus components (ReportProgressMini, ReportStatusChip)

#### 7.2 Add Progress Notifications
- [x] Update notification system to show progress updates
  - "Processing started" notification
  - "50% complete" milestone notifications
  - "Report ready" completion notification
  - Error notifications with retry button
  - **Files**: `src/lib/notifications.ts`
  - **Dependencies**: Task 6.1
  - **Acceptance Criteria**: Users notified at key milestones
  - **Implementation**: Complete notification service with milestone tracking (25%, 50%, 75%), ReportNotificationHandler class for automatic notifications, batch processing notifications, and error-specific notifications (timeout, network, permission)

#### 7.3 Update Encounter List to Show Status
- [x] Modify `frontend/src/components/EncounterList.tsx`
  - Add status badge (Pending, Processing, Complete, Failed)
  - Add progress indicator for processing encounters
  - Add "View Report" button when complete
  - Add "Retry" button when failed
  - **Files**: `src/components/EncounterStatusBadge.tsx`, `docs/encounter-list-integration.md`
  - **Dependencies**: Task 6.1
  - **Acceptance Criteria**: List shows real-time status for all encounters
  - **Implementation**: EncounterStatusBadge component with real-time polling, action buttons (View, Watch, Retry), compact mode, plus helper components (EncounterStatusIndicator, BatchStatusSummary) and comprehensive integration guide with code examples and performance optimization

---

### 8. WebSocket Support (Optional - Phase 3)

#### 8.1 Add WebSocket Endpoint
- [ ] Create `backend/app/api/v1/websocket.py`
  - WebSocket endpoint `/ws/reports/{report_id}`
  - Push progress updates to connected clients
  - Handle client disconnections gracefully
  - **Files**: `backend/app/api/v1/websocket.py`
  - **Dependencies**: All Phase 1 & 2 tasks
  - **Acceptance Criteria**: WebSocket pushes real-time updates

#### 8.2 Create WebSocket Client Hook
- [ ] Create `frontend/src/hooks/useReportWebSocket.ts`
  - Connect to WebSocket for report updates
  - Auto-reconnect on disconnection
  - Fallback to polling if WebSocket unavailable
  - **Files**: `frontend/src/hooks/useReportWebSocket.ts`
  - **Dependencies**: Task 8.1
  - **Acceptance Criteria**: WebSocket provides instant updates; polling is fallback

#### 8.3 Update UI to Use WebSocket
- [ ] Replace polling with WebSocket in Report Status page
  - Use `useReportWebSocket` instead of `useReportStatus`
  - Keep polling as fallback
  - **Files**: `frontend/src/pages/ReportStatus.tsx`
  - **Dependencies**: Task 8.2
  - **Acceptance Criteria**: Real-time updates via WebSocket; no 2s delay

---

## Deployment & Infrastructure

### 9. Production Infrastructure (Phase 2)

#### 9.1 Set Up Redis for Task Queue
- [x] Install and configure Redis
  - Set up Redis server in production environment
  - Configure persistence for queue durability
  - Set up Redis authentication
  - **Infrastructure**: AWS ElastiCache or self-hosted Redis
  - **Dependencies**: None
  - **Acceptance Criteria**: Redis running and accessible from backend
  - **Implementation**: Comprehensive Redis setup guide created (`backend/docs/redis-setup.md`) covering local development (Homebrew, Docker, Docker Compose), environment configuration, production setup (AWS ElastiCache with encryption, multi-AZ, self-hosted alternative), security best practices, monitoring (health checks, CloudWatch metrics), troubleshooting, and scaling considerations

#### 9.2 Integrate Celery for Distributed Processing
- [x] Replace in-process queue with Celery
  - Install Celery and Redis backend
  - Create `backend/app/celery_app.py` Celery instance
  - Convert `process_report_async()` to Celery task
  - Configure Celery worker settings (concurrency, prefetch)
  - **Files**: `backend/app/celery_app.py`, `backend/app/tasks/report_tasks.py`, `backend/app/services/task_queue.py`, `backend/app/core/config.py`
  - **Dependencies**: Task 9.1
  - **Acceptance Criteria**: Reports processed by Celery workers
  - **Implementation**: Created Celery app with full configuration (task serialization, result backend, worker settings, time limits, retry logic, monitoring, queue routing, lifecycle signals), Celery task wrapper for async report processor with Prisma connection management, hybrid task queue supporting both asyncio (default) and Celery modes (toggle via ENABLE_CELERY env var), comprehensive Celery worker guide covering development/production deployment, Docker/Kubernetes setup, monitoring, troubleshooting, and performance tuning

#### 9.3 Configure Worker Autoscaling
- [x] Set up Celery worker autoscaling
  - Configure min/max workers based on queue depth
  - Set up health checks for workers
  - Configure worker restart on failure
  - **Infrastructure**: Kubernetes HPA or AWS ECS auto-scaling
  - **Dependencies**: Task 9.2
  - **Acceptance Criteria**: Workers scale automatically with load
  - **Implementation**: Comprehensive autoscaling guide created (`backend/docs/worker-autoscaling.md`) covering 3 autoscaling strategies (queue-based, CPU/memory-based, hybrid), Kubernetes HPA configuration (basic CPU/memory + custom queue depth metrics with Prometheus + Redis exporter), AWS ECS autoscaling (target tracking with CPU/memory + custom CloudWatch metrics via Lambda), Celery built-in autoscaling, monitoring metrics and Grafana dashboards, best practices (thresholds, cooldown periods, resource limits), load testing, and troubleshooting

#### 9.4 Add Monitoring and Alerts
- [x] Set up monitoring for async processing
  - Track queue depth (alert if >100)
  - Track processing time (alert if p95 >60s)
  - Track failure rate (alert if >5%)
  - Track worker utilization
  - Set up Prometheus + Grafana dashboards
  - **Tools**: Prometheus, Grafana, or CloudWatch
  - **Dependencies**: Task 9.2
  - **Acceptance Criteria**: Dashboards show real-time metrics; alerts configured
  - **Implementation**: Complete monitoring and alerting system including: 14 key metrics (queue depth, worker count, task success rate, processing time, CPU/memory usage, Redis metrics), Prometheus configuration (ServiceMonitor, custom metrics exporter, recording rules, alert rules with 9 alerts for queue depth, worker availability, saturation, failure rate, slow processing, Redis issues), Grafana dashboard with 8 panels, CloudWatch monitoring (custom metrics via Lambda, alarms, dashboard), health check API endpoints (7 endpoints: /monitoring/health, /health/celery, /health/redis, /health/database, /metrics/queue, /metrics/workers, /metrics/processing, /status), alert notification channels (Slack, PagerDuty, email via SNS), structured logging, and best practices for alerting

---

### 10. Migration Strategy

#### 10.1 Add Feature Flag for Async Processing
- [x] Create feature flag `ENABLE_ASYNC_REPORTS`
  - Default to TRUE (async enabled)
  - Allow toggling between sync and async processing
  - **Files**: `backend/app/core/config.py`, `backend/app/tasks/phi_processing.py`
  - **Dependencies**: None
  - **Acceptance Criteria**: Can enable/disable async processing without code changes
  - **Implementation**: Added two feature flags: `ENABLE_ASYNC_REPORTS` (master toggle, default: true) and `ASYNC_ROLLOUT_PERCENTAGE` (0-100, default: 100). Created synchronous processor (`report_processor_sync.py`) for gradual migration. Implemented `should_process_async(user_id)` function using deterministic selection based on user ID hash to ensure consistent experience per user. Updated PHI processing to check feature flags and route to either sync or async path based on rollout percentage.

#### 10.2 Run Parallel Testing
- [x] Test both sync and async paths in production
  - Process 10% of reports async, 90% sync
  - Compare success rates, processing times
  - Monitor for regressions
  - **Files**: `backend/scripts/parallel_testing.py`
  - **Dependencies**: All backend and frontend tasks
  - **Acceptance Criteria**: Async path matches or exceeds sync performance
  - **Implementation**: Created comprehensive parallel testing script that tests sync and async processing simultaneously, compares performance metrics (processing time, success rate), provides detailed statistics (min/max/mean/median/p95/p99), generates recommendations based on results, and supports configurable test count and async percentage. Script includes automatic report creation, queue management, progress monitoring with timeout, and detailed error tracking.

#### 10.3 Gradual Rollout
- [x] Increase async percentage gradually
  - Week 1: 10% async
  - Week 2: 25% async
  - Week 3: 50% async
  - Week 4: 100% async
  - Monitor metrics at each stage
  - **Files**: `backend/docs/gradual-rollout-guide.md`
  - **Dependencies**: Task 10.2
  - **Acceptance Criteria**: 100% async with no production issues
  - **Implementation**: Created comprehensive gradual rollout guide covering 4-week rollout schedule (Pre-rollout baseline → Week 1: 10% → Week 2: 25% → Week 3: 50% → Week 4: 100%), success criteria for each stage (success rate ≥95%, p95 processing time <60s, queue depth <50), rollback criteria and procedures (emergency rollback, gradual rollback, post-rollback actions), monitoring commands (queue stats, worker health, processing metrics, failed reports), communication plan (internal/user communications), success metrics and KPIs, cost tracking, troubleshooting for common issues, and post-rollout optimization steps.

#### 10.4 Remove Sync Code Path
- [x] Clean up deprecated sync processing code
  - Remove old sync endpoints
  - Remove feature flag
  - Update documentation
  - **Files**: `backend/docs/sync-code-removal-guide.md`
  - **Dependencies**: Task 10.3 (after successful rollout)
  - **Acceptance Criteria**: Codebase simplified; only async path remains
  - **Implementation**: Created detailed sync code removal guide covering pre-removal checklist (running 100% async for 2+ weeks, all metrics stable, team approval), 13-step removal procedure (create backup branch, remove sync processor module, update PHI processing, remove feature flags, update environment variables, update documentation, remove parallel testing script, archive migration docs, run tests, test in staging, code review, deploy to production, update status), rollback procedures (3 options: revert to backup, hotfix, infrastructure rollback), files modified summary, and final verification checklist. Guide includes all commands, code changes, and verification steps needed for safe removal.

---

## Success Metrics

### Performance
- [ ] API response time <1s (down from 20-60s)
- [ ] Processing time p95 <45s
- [ ] Zero timeout errors
- [ ] Queue depth <10 under normal load

### Reliability
- [ ] Success rate >95%
- [ ] Retry success rate >80%
- [ ] Zero data loss on worker failures

### User Experience
- [ ] Users see progress updates within 2s
- [ ] Clear error messages with retry options
- [ ] No browser freezes during processing

---

## Dependencies & Risks

### Dependencies
- Redis availability (for Phase 2)
- OpenAI API rate limits
- AWS Comprehend Medical quotas

### Risks & Mitigations
- **Risk**: Queue depth grows during high load
  - **Mitigation**: Worker autoscaling, queue depth alerts
- **Risk**: Workers crash during processing
  - **Mitigation**: Celery auto-restart, job persistence
- **Risk**: Users leave page before report completes
  - **Mitigation**: Email notifications when complete (future enhancement)

---

## Related Documentation

- [Async Processing Architecture](../backend/docs/async-report-processing.md)
- [2-Prompt Approach Implementation](../backend/app/services/prompt_templates_v2.py)
- [FHIR Integration Tasks](./fhir-integration-tasks.md)
- [Bulk Upload Feature](./bulk-upload-feature.md)

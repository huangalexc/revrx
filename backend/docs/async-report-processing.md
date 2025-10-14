# Asynchronous Report Processing Architecture

## Overview

The FHIR coding intelligence pipeline processes encounters asynchronously to avoid blocking API requests and improve user experience.

## Current Architecture

### Synchronous Flow (Before)
```
API Request → Process Encounter → Generate Report → Return Response
   |              (20-60s)              |
   └─────────── User Waits ─────────────┘
```

**Issues:**
- Long request times (20-60 seconds)
- API timeouts on complex encounters
- Poor user experience
- No progress visibility

### Asynchronous Flow (After)
```
API Request → Queue Encounter → Return 202 Accepted
                    ↓
              Background Worker
                    ↓
         Process → Update Status → Notify User
```

**Benefits:**
- Immediate API response (<1s)
- No timeout issues
- Progress tracking
- Scalable processing
- Better error handling

## Implementation Design

### 1. Report Status States

```prisma
enum ReportStatus {
  PENDING         // Queued for processing
  PROCESSING      // Currently being analyzed
  COMPLETE        // Successfully generated
  FAILED          // Error occurred
}
```

### 2. Database Schema Update

Add status tracking to Report model:

```prisma
model Report {
  // ... existing fields ...

  // Processing status
  status            ReportStatus @default(PENDING)
  processingStartedAt DateTime? @map("processing_started_at")
  processingCompletedAt DateTime? @map("processing_completed_at")
  processingTimeMs  Int?     @map("processing_time_ms")

  // Error handling
  errorMessage      String?  @map("error_message")
  errorDetails      Json?    @map("error_details")
  retryCount        Int      @default(0) @map("retry_count")

  // Progress tracking (optional for detailed status)
  progressPercent   Int?     @default(0) @map("progress_percent")
  currentStep       String?  @map("current_step") // e.g., "phi_detection", "code_inference"
}
```

### 3. API Endpoints

#### Trigger Report Generation
```http
POST /api/encounters/{encounterId}/reports
Authorization: Bearer {token}

Response: 202 Accepted
{
  "reportId": "uuid",
  "status": "PENDING",
  "message": "Report generation queued"
}
```

#### Check Report Status
```http
GET /api/encounters/{encounterId}/reports/{reportId}
Authorization: Bearer {token}

Response: 200 OK
{
  "reportId": "uuid",
  "status": "PROCESSING",
  "progressPercent": 45,
  "currentStep": "code_inference",
  "processingTime": 15240
}
```

#### Get Completed Report
```http
GET /api/encounters/{encounterId}/reports/{reportId}
Authorization: Bearer {token}

Response: 200 OK (when status=COMPLETE)
{
  "reportId": "uuid",
  "status": "COMPLETE",
  "suggestedCodes": [...],
  "incrementalRevenue": 1234.56,
  // ... full report data
}
```

### 4. Background Worker

Use Python `asyncio` for background processing:

**Option A: Simple In-Process Queue**
- Use `asyncio.create_task()` for immediate background processing
- Good for: Low volume, single server deployment
- Limitations: No persistence across restarts

```python
@app.post("/encounters/{encounter_id}/reports")
async def create_report(encounter_id: str):
    # Create pending report
    report = await prisma.report.create({
        "encounterId": encounter_id,
        "status": "PENDING"
    })

    # Queue background task
    asyncio.create_task(process_report_async(report.id))

    return {"reportId": report.id, "status": "PENDING"}
```

**Option B: Celery + Redis (Recommended for Production)**
- Distributed task queue
- Persistent queue (survives restarts)
- Retry logic and error handling
- Multiple workers for scalability

```python
from celery import Celery

celery = Celery('tasks', broker='redis://localhost:6379')

@celery.task(bind=True, max_retries=3)
def process_report_task(self, report_id: str):
    try:
        # Process report
        result = process_report_sync(report_id)
        return result
    except Exception as e:
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
```

### 5. Processing Pipeline

```python
async def process_report_async(report_id: str):
    """Background task to process encounter and generate report"""

    try:
        # Update status to PROCESSING
        await prisma.report.update(
            where={"id": report_id},
            data={
                "status": "PROCESSING",
                "processingStartedAt": datetime.now()
            }
        )

        # Get encounter data
        report = await prisma.report.findUnique(
            where={"id": report_id},
            include={"encounter": True}
        )

        # Step 1: PHI Detection (10%)
        await update_progress(report_id, 10, "phi_detection")
        phi_result = await detect_phi(report.encounter)

        # Step 2: Clinical Filtering (30%)
        await update_progress(report_id, 30, "clinical_filtering")
        filtered_text = await filter_clinical_relevance(phi_result.text)

        # Step 3: Code Inference (50%)
        await update_progress(report_id, 50, "code_inference")
        icd10_codes = await infer_icd10_codes(filtered_text)
        snomed_codes = await infer_snomed_codes(filtered_text)

        # Step 4: AI Analysis (80%)
        await update_progress(report_id, 80, "ai_analysis")
        ai_result = await openai_service.analyze_clinical_note_v2(
            clinical_note=filtered_text,
            billed_codes=billed_codes,
            extracted_icd10_codes=icd10_codes,
            snomed_to_cpt_suggestions=[]
        )

        # Step 5: Finalize Report (100%)
        await update_progress(report_id, 100, "finalizing")
        processing_time = (datetime.now() - report.processingStartedAt).total_seconds() * 1000

        await prisma.report.update(
            where={"id": report_id},
            data={
                "status": "COMPLETE",
                "processingCompletedAt": datetime.now(),
                "processingTimeMs": int(processing_time),
                "suggestedCodes": ai_result.suggested_codes,
                "incrementalRevenue": ai_result.total_incremental_revenue,
                # ... other fields
            }
        )

    except Exception as e:
        # Handle errors
        await prisma.report.update(
            where={"id": report_id},
            data={
                "status": "FAILED",
                "errorMessage": str(e),
                "errorDetails": {
                    "type": type(e).__name__,
                    "traceback": traceback.format_exc()
                },
                "retryCount": report.retryCount + 1
            }
        )
```

### 6. Frontend Integration

**Polling Strategy:**
```typescript
async function pollReportStatus(reportId: string) {
  const poll = async () => {
    const response = await fetch(`/api/reports/${reportId}`);
    const data = await response.json();

    if (data.status === 'COMPLETE') {
      // Show report
      displayReport(data);
    } else if (data.status === 'FAILED') {
      // Show error
      showError(data.errorMessage);
    } else {
      // Update progress
      updateProgress(data.progressPercent, data.currentStep);
      // Poll again in 2 seconds
      setTimeout(poll, 2000);
    }
  };

  poll();
}
```

**WebSocket Strategy (Better UX):**
```typescript
const ws = new WebSocket(`/ws/reports/${reportId}`);

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);

  switch (update.status) {
    case 'PROCESSING':
      updateProgress(update.progressPercent, update.currentStep);
      break;
    case 'COMPLETE':
      displayReport(update.report);
      ws.close();
      break;
    case 'FAILED':
      showError(update.errorMessage);
      ws.close();
      break;
  }
};
```

## Deployment Considerations

### Development
- Use in-process `asyncio` tasks
- Simple polling from frontend

### Production
- Use Celery + Redis for task queue
- Add monitoring (Prometheus + Grafana)
- Configure worker autoscaling
- Implement dead-letter queue for failed tasks
- Add WebSocket support for real-time updates

## Migration Strategy

1. **Phase 1**: Add database schema changes
2. **Phase 2**: Implement async processing (keep sync as fallback)
3. **Phase 3**: Update frontend to poll for status
4. **Phase 4**: Switch default to async processing
5. **Phase 5**: Remove sync processing code

## Monitoring & Observability

Track these metrics:
- Queue depth
- Processing time (p50, p95, p99)
- Success/failure rate
- Retry count
- Worker utilization

## Error Handling

- Automatic retry with exponential backoff (3 attempts)
- Dead-letter queue for permanently failed reports
- Admin notifications for repeated failures
- User-friendly error messages

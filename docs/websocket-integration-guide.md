# WebSocket Integration Guide

This guide explains how to integrate WebSocket support for real-time report updates.

## Overview

WebSocket provides instant updates without polling delays. The system automatically falls back to polling if WebSocket is unavailable.

## Task 8.3: Update Report Status Page

### Option 1: Drop-in Replacement

The simplest approach is to replace `useReportStatus` with `useReportWebSocket`:

```typescript
// Before (Polling)
import { useReportStatus } from '@/hooks/useReportStatus';

const { status, progress, error } = useReportStatus(reportId);

// After (WebSocket with polling fallback)
import { useReportWebSocket } from '@/hooks/useReportWebSocket';

const { status, progress, error, isConnected, isPolling } = useReportWebSocket(reportId);
```

### Option 2: Optimized Hook

Use the optimized hook that automatically chooses the best transport:

```typescript
import { useReportStatusOptimized } from '@/hooks/useReportWebSocket';

const { status, progress, error, isConnected } = useReportStatusOptimized(reportId, {
  onComplete: (data) => {
    console.log('Report complete!', data);
  },
  onFailed: (data) => {
    console.error('Report failed:', data.errorMessage);
  },
});
```

## Complete Example: Updated Report Status Page

```typescript
'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Card, CardBody, CardHeader } from '@nextui-org/card';
import { Badge } from '@nextui-org/badge';
import { WifiIcon, ArrowPathIcon } from '@heroicons/react/24/outline';

import { useReportWebSocket } from '@/hooks/useReportWebSocket';
import { ReportProgress } from '@/components/ReportProgress';

export default function ReportStatusPage() {
  const params = useParams();
  const router = useRouter();
  const reportId = params?.reportId as string;

  const {
    data,
    status,
    progress,
    currentStep,
    estimatedTimeRemaining,
    error,
    isLoading,
    isConnected,
    isPolling,
    reconnect,
  } = useReportWebSocket(reportId, {
    onComplete: () => {
      console.log('Report complete! Redirecting...');
    },
  });

  // Auto-redirect when complete
  useEffect(() => {
    if (status === 'COMPLETE' && data?.encounterId) {
      const timer = setTimeout(() => {
        router.push(`/reports/encounters/${data.encounterId}`);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [status, data?.encounterId, router]);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="container max-w-4xl mx-auto py-8">
      <Card>
        <CardHeader className="flex justify-between">
          <h1 className="text-2xl font-bold">Report Status</h1>

          {/* Connection Indicator */}
          <div className="flex items-center gap-2">
            {isConnected ? (
              <Badge content="Live" color="success" variant="flat">
                <WifiIcon className="w-5 h-5 text-success" />
              </Badge>
            ) : isPolling ? (
              <Badge content="Polling" color="warning" variant="flat">
                <ArrowPathIcon className="w-5 h-5 text-warning animate-spin" />
              </Badge>
            ) : (
              <button
                onClick={reconnect}
                className="text-sm text-primary hover:underline"
              >
                Reconnect
              </button>
            )}
          </div>
        </CardHeader>

        <CardBody className="gap-6">
          {/* Progress Display */}
          <ReportProgress
            progress={progress}
            currentStep={currentStep}
            status={status || 'PENDING'}
            estimatedTimeRemaining={estimatedTimeRemaining}
          />

          {/* Status Messages */}
          {status === 'PROCESSING' && (
            <div className="p-4 bg-primary-50 rounded-lg">
              <p className="text-sm text-primary-700">
                ⚡ Receiving real-time updates via{' '}
                {isConnected ? 'WebSocket' : 'polling'}
              </p>
            </div>
          )}

          {error && (
            <div className="p-4 bg-danger-50 rounded-lg">
              <p className="text-sm text-danger-700">{error}</p>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
```

## Backend Integration

### Pushing Updates from Report Processor

To push WebSocket updates from the backend, integrate with the report processor:

```python
# backend/app/services/report_processor.py

async def update_report_progress(
    report_id: str,
    progress_percent: int,
    current_step: str
) -> None:
    """Update report progress in database and push to WebSocket clients"""
    # Update database
    await prisma.report.update(
        where={"id": report_id},
        data={
            "progressPercent": progress_percent,
            "currentStep": current_step,
        }
    )

    # Push WebSocket update
    try:
        from app.api.v1.websocket import notify_report_update

        await notify_report_update(report_id, {
            "reportId": report_id,
            "status": "PROCESSING",
            "progressPercent": progress_percent,
            "currentStep": current_step,
        })
    except Exception as e:
        # WebSocket notification is optional - don't fail if it errors
        logger.warning(f"Failed to push WebSocket update: {e}")
```

### Register WebSocket Router

Add the WebSocket router to your FastAPI app:

```python
# backend/app/main.py or backend/app/api/v1/router.py

from app.api.v1 import websocket

# Add to your router includes
app.include_router(websocket.router, prefix="/api/v1")
```

## Connection States

The hook provides several connection states:

| State | Description |
|-------|-------------|
| `isLoading` | Initial connection being established |
| `isConnected` | WebSocket connected and receiving updates |
| `isPolling` | Using polling fallback (WebSocket failed) |
| `error` | Connection or processing error |

## Configuration Options

### Disable Polling Fallback

```typescript
useReportWebSocket(reportId, {
  enablePollingFallback: false, // Fail if WebSocket unavailable
});
```

### Custom Reconnect Attempts

```typescript
useReportWebSocket(reportId, {
  maxReconnectAttempts: 5, // Default: 3
});
```

### Connection Callbacks

```typescript
useReportWebSocket(reportId, {
  onConnect: () => console.log('WebSocket connected'),
  onDisconnect: () => console.log('WebSocket disconnected'),
  onComplete: (data) => notifyReportComplete(data),
  onFailed: (data) => notifyReportFailed(data),
});
```

## Performance Benefits

### WebSocket vs Polling

| Metric | Polling (2s) | WebSocket |
|--------|--------------|-----------|
| Update Latency | 0-2 seconds | <100ms |
| Server Load | High (constant requests) | Low (push only) |
| Network Usage | ~30 requests/min | ~10 messages/min |
| Battery Impact | Higher | Lower |

### Bandwidth Comparison

For a 60-second report:
- **Polling**: ~30 HTTP requests × 500 bytes = 15 KB
- **WebSocket**: 1 connection + ~10 updates × 200 bytes = 2 KB

**Savings**: 87% less bandwidth

## Error Handling

### Automatic Reconnection

The hook automatically reconnects with exponential backoff:

```
Attempt 1: Reconnect after 2 seconds
Attempt 2: Reconnect after 4 seconds
Attempt 3: Reconnect after 8 seconds
After 3 attempts: Fall back to polling (if enabled)
```

### Manual Reconnection

```typescript
const { reconnect } = useReportWebSocket(reportId);

// Trigger manual reconnect
<button onClick={reconnect}>Reconnect</button>
```

## Security Considerations

### Authentication

WebSocket connections should verify user access:

```python
# backend/app/api/v1/websocket.py

@router.websocket("/reports/{report_id}")
async def websocket_report_status(
    websocket: WebSocket,
    report_id: str
):
    # Get user from WebSocket connection
    user = await get_current_user_ws(websocket)

    # Verify access
    report = await prisma.report.find_unique(
        where={"id": report_id},
        include={"encounter": True}
    )

    if user.role != "ADMIN" and report.encounter.userId != user.id:
        await websocket.close(code=1008)  # Policy violation
        return
```

### Rate Limiting

Implement connection limits per user:

```python
# Limit to 10 concurrent WebSocket connections per user
if len(manager.get_user_connections(user.id)) >= 10:
    await websocket.close(code=1008)
    return
```

## Testing

### Test WebSocket Connection

```typescript
describe('useReportWebSocket', () => {
  it('connects to WebSocket', async () => {
    const { result } = renderHook(() => useReportWebSocket('report-123'));

    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });
  });

  it('falls back to polling on WebSocket failure', async () => {
    // Mock WebSocket failure
    global.WebSocket = jest.fn(() => {
      throw new Error('WebSocket unavailable');
    });

    const { result } = renderHook(() =>
      useReportWebSocket('report-123', { enablePollingFallback: true })
    );

    await waitFor(() => {
      expect(result.current.isPolling).toBe(true);
    });
  });
});
```

## Migration Checklist

- [ ] Backend WebSocket endpoint implemented
- [ ] WebSocket router registered in FastAPI app
- [ ] Frontend hook integrated into status page
- [ ] Connection indicator visible to users
- [ ] Polling fallback tested
- [ ] Reconnection logic tested
- [ ] Authentication/authorization implemented
- [ ] Load tested with multiple concurrent connections
- [ ] WebSocket close codes handled properly
- [ ] Ping/pong keep-alive working

## Troubleshooting

### WebSocket Connection Fails

1. Check WebSocket URL protocol (ws:// vs wss://)
2. Verify CORS/proxy configuration
3. Check firewall rules for WebSocket traffic
4. Test with browser DevTools Network tab

### Updates Not Received

1. Verify backend is calling `notify_report_update()`
2. Check WebSocket connection is open
3. Look for errors in browser console
4. Verify report_id matches

### High Memory Usage

1. Ensure connections are properly closed
2. Check for memory leaks in ConnectionManager
3. Implement connection limits per user
4. Monitor with WebSocket stats endpoint

## Related Documentation

- [WebSocket Backend](../backend/app/api/v1/websocket.py)
- [WebSocket Hook](../src/hooks/useReportWebSocket.ts)
- [Report Status Hook](../src/hooks/useReportStatus.ts)
- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)

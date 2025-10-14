# Encounter List - Status Integration Guide

This guide explains how to integrate real-time report status into the encounter list component.

## Overview

The encounter list should display the current report status for each encounter, with:
- Real-time progress updates for processing reports
- Action buttons (View Report, Watch Progress, Retry)
- Visual indicators (status chips, progress bars)
- Polling for pending/processing reports only

## Implementation

### Step 1: Import Required Components

```typescript
import { EncounterStatusBadge } from '@/components/EncounterStatusBadge';
import { useReportStatus } from '@/hooks/useReportStatus';
```

### Step 2: Update Encounter List Item

```typescript
interface Encounter {
  id: string;
  createdAt: string;
  status: string;
  report?: {
    id: string;
    status: 'PENDING' | 'PROCESSING' | 'COMPLETE' | 'FAILED';
    progressPercent: number;
  };
}

function EncounterListItem({ encounter }: { encounter: Encounter }) {
  return (
    <div className="flex items-center justify-between p-4 border rounded-lg">
      {/* Encounter Info */}
      <div>
        <h3 className="font-semibold">Encounter {encounter.id.slice(0, 8)}</h3>
        <p className="text-sm text-default-500">
          {new Date(encounter.createdAt).toLocaleDateString()}
        </p>
      </div>

      {/* Report Status */}
      <EncounterStatusBadge
        encounterId={encounter.id}
        reportId={encounter.report?.id}
        showActions={true}
      />
    </div>
  );
}
```

### Step 3: Optimize Polling for Lists

For lists with many encounters, only poll reports that are pending or processing:

```typescript
function EncounterList({ encounters }: { encounters: Encounter[] }) {
  // Filter encounters that need polling
  const activeReports = encounters.filter(
    (e) => e.report?.status === 'PENDING' || e.report?.status === 'PROCESSING'
  );

  return (
    <div className="space-y-3">
      {encounters.map((encounter) => (
        <EncounterListItem key={encounter.id} encounter={encounter} />
      ))}

      {activeReports.length > 0 && (
        <div className="text-sm text-default-500 text-center py-2">
          {activeReports.length} report{activeReports.length > 1 ? 's' : ''} processing...
        </div>
      )}
    </div>
  );
}
```

### Step 4: Add Batch Actions (Optional)

```typescript
import { Button } from '@nextui-org/button';
import { BatchStatusSummary } from '@/components/EncounterStatusBadge';

function EncounterListHeader({ encounters }: { encounters: Encounter[] }) {
  const statusCounts = encounters.reduce((acc, e) => {
    const status = e.report?.status || 'NO_REPORT';
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const statusSummary = Object.entries(statusCounts).map(([status, count]) => ({
    status: status as any,
    count,
  }));

  return (
    <div className="flex items-center justify-between mb-4">
      <h2 className="text-2xl font-bold">Encounters</h2>

      <div className="flex items-center gap-4">
        {/* Status Summary */}
        <BatchStatusSummary statuses={statusSummary} />

        {/* Batch Actions */}
        <Button
          color="primary"
          size="sm"
          onPress={() => {
            // Generate reports for all encounters without reports
            // Implementation depends on your API
          }}
        >
          Generate All Reports
        </Button>
      </div>
    </div>
  );
}
```

## Example: Complete Encounter List Component

```typescript
'use client';

import { useState, useEffect } from 'react';
import { Card, CardBody } from '@nextui-org/card';
import { Spinner } from '@nextui-org/spinner';
import { EncounterStatusBadge } from '@/components/EncounterStatusBadge';

interface Encounter {
  id: string;
  userId: string;
  status: string;
  createdAt: string;
  report?: {
    id: string;
    status: 'PENDING' | 'PROCESSING' | 'COMPLETE' | 'FAILED';
    progressPercent: number;
  };
}

export default function EncounterList() {
  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch encounters
  useEffect(() => {
    fetch('/api/v1/encounters')
      .then((res) => res.json())
      .then((data) => {
        setEncounters(data.encounters);
        setIsLoading(false);
      })
      .catch((err) => {
        console.error('Failed to fetch encounters:', err);
        setIsLoading(false);
      });
  }, []);

  // Refresh list when any report completes
  useEffect(() => {
    const interval = setInterval(() => {
      // Only refresh if there are active reports
      const hasActiveReports = encounters.some(
        (e) => e.report?.status === 'PENDING' || e.report?.status === 'PROCESSING'
      );

      if (hasActiveReports) {
        // Refresh encounter list
        fetch('/api/v1/encounters')
          .then((res) => res.json())
          .then((data) => setEncounters(data.encounters))
          .catch((err) => console.error('Refresh failed:', err));
      }
    }, 10000); // Refresh every 10 seconds

    return () => clearInterval(interval);
  }, [encounters]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-3xl font-bold">Encounters</h1>

      {encounters.length === 0 ? (
        <Card>
          <CardBody className="text-center py-12">
            <p className="text-default-500">No encounters found</p>
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-3">
          {encounters.map((encounter) => (
            <Card key={encounter.id}>
              <CardBody>
                <div className="flex items-center justify-between">
                  {/* Encounter Details */}
                  <div>
                    <h3 className="font-semibold text-lg">
                      Encounter #{encounter.id.slice(0, 8)}
                    </h3>
                    <p className="text-sm text-default-500">
                      {new Date(encounter.createdAt).toLocaleString()}
                    </p>
                    <p className="text-xs text-default-400 mt-1">
                      Status: {encounter.status}
                    </p>
                  </div>

                  {/* Report Status with Actions */}
                  <EncounterStatusBadge
                    encounterId={encounter.id}
                    reportId={encounter.report?.id}
                    showActions={true}
                  />
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
```

## Performance Considerations

### Polling Optimization

1. **Only poll active reports**: Filter encounters with PENDING/PROCESSING status
2. **Stagger polling**: Add random offset to avoid thundering herd
3. **Increase poll interval for lists**: Use 5-10 seconds instead of 2 seconds
4. **Stop polling on unmount**: Clean up intervals properly

```typescript
// Staggered polling example
const pollInterval = 5000 + Math.random() * 2000; // 5-7 seconds
```

### Conditional Rendering

Only render status badges for encounters with reports:

```typescript
{
  encounter.report ? (
    <EncounterStatusBadge
      encounterId={encounter.id}
      reportId={encounter.report.id}
      compact={true}
    />
  ) : (
    <Button size="sm" variant="flat">
      Generate Report
    </Button>
  );
}
```

## Styling Options

### Compact Mode
```typescript
<EncounterStatusBadge reportId={reportId} compact={true} showActions={false} />
```

### With Tooltip
```typescript
import { Tooltip } from '@nextui-org/tooltip';

<Tooltip content="Click to view progress">
  <div>
    <EncounterStatusBadge reportId={reportId} />
  </div>
</Tooltip>
```

### In Table
```typescript
<table>
  <tbody>
    {encounters.map(encounter => (
      <tr key={encounter.id}>
        <td>{encounter.id}</td>
        <td>
          <EncounterStatusBadge
            reportId={encounter.report?.id}
            compact={true}
          />
        </td>
      </tr>
    ))}
  </tbody>
</table>
```

## Related Components

- [EncounterStatusBadge](../src/components/EncounterStatusBadge.tsx) - Status badge with actions
- [ReportProgress](../src/components/ReportProgress.tsx) - Progress visualization
- [useReportStatus](../src/hooks/useReportStatus.ts) - Status polling hook
- [Notifications](../src/lib/notifications.ts) - Toast notifications

## Testing Checklist

- [ ] Status badges display correctly for all states
- [ ] Progress updates in real-time
- [ ] Actions work (View, Watch, Retry)
- [ ] Polling stops when reports complete
- [ ] List performance is acceptable with 50+ encounters
- [ ] Error states display properly
- [ ] Tooltips show helpful information

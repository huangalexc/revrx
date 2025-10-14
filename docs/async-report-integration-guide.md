# Async Report Generation - Frontend Integration Guide

This guide explains how to integrate async report generation into the encounter upload flow.

## Task 6.2: Update Encounter Upload Flow

### Overview

When implementing the encounter upload component, you'll need to:

1. After file upload completes, trigger async report generation via API
2. Receive the report ID from the API
3. Redirect user to the report status page to watch progress in real-time

### Implementation Steps

#### Step 1: Trigger Async Report Generation

After the encounter file is uploaded and processed, call the async report generation endpoint:

```typescript
// After encounter upload completes
async function triggerReportGeneration(encounterId: string) {
  try {
    const response = await fetch(
      `/api/v1/reports/encounters/${encounterId}/reports`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      throw new Error('Failed to trigger report generation');
    }

    const data = await response.json();
    // data = { reportId, status: 'PENDING', message, progressPercent, currentStep }

    return data;
  } catch (error) {
    console.error('Error triggering report generation:', error);
    throw error;
  }
}
```

#### Step 2: Redirect to Report Status Page

After triggering report generation, redirect the user to the status page:

```typescript
import { useRouter } from 'next/navigation';

const router = useRouter();

// After triggering report generation
const { reportId } = await triggerReportGeneration(encounterId);

// Show success message
toast.success('Report generation started!');

// Redirect to status page
router.push(`/reports/${reportId}/status`);
```

#### Step 3: Handle Errors

Handle various error scenarios:

```typescript
try {
  const { reportId } = await triggerReportGeneration(encounterId);
  router.push(`/reports/${reportId}/status`);
} catch (error) {
  if (error.response?.status === 404) {
    toast.error('Encounter not found');
  } else if (error.response?.status === 403) {
    toast.error('You do not have permission to generate reports for this encounter');
  } else {
    toast.error('Failed to start report generation. Please try again.');
  }
}
```

### Complete Example: EncounterUpload Component

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@nextui-org/button';
import { Card, CardBody } from '@nextui-org/card';
import { toast } from 'sonner';

export default function EncounterUpload() {
  const router = useRouter();
  const [isUploading, setIsUploading] = useState(false);
  const [encounterId, setEncounterId] = useState<string | null>(null);

  async function handleFileUpload(file: File) {
    setIsUploading(true);

    try {
      // Step 1: Upload file and create encounter
      const formData = new FormData();
      formData.append('file', file);

      const uploadResponse = await fetch('/api/v1/encounters/upload', {
        method: 'POST',
        body: formData,
      });

      if (!uploadResponse.ok) {
        throw new Error('File upload failed');
      }

      const { encounterId } = await uploadResponse.json();
      setEncounterId(encounterId);

      toast.success('File uploaded successfully!');

      // Step 2: Trigger async report generation
      const reportResponse = await fetch(
        `/api/v1/reports/encounters/${encounterId}/reports`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (!reportResponse.ok) {
        throw new Error('Failed to trigger report generation');
      }

      const { reportId } = await reportResponse.json();

      toast.success('Report generation started!');

      // Step 3: Redirect to status page
      router.push(`/reports/${reportId}/status`);
    } catch (error) {
      console.error('Upload error:', error);
      toast.error('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <Card>
      <CardBody>
        <h2 className="text-xl font-semibold mb-4">Upload Clinical Note</h2>

        <input
          type="file"
          accept=".pdf,.txt,.docx"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              handleFileUpload(file);
            }
          }}
          disabled={isUploading}
        />

        {isUploading && (
          <div className="mt-4">
            <p>Uploading file and starting report generation...</p>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
```

### API Response Format

The async report generation endpoint returns:

```typescript
interface ReportGenerationResponse {
  reportId: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETE';
  message: string;
  progressPercent?: number;
  currentStep?: string;
}
```

### User Experience Flow

1. **Upload File** → User selects and uploads clinical note file
2. **Processing...** → Show loading indicator during file upload
3. **Report Queued** → API returns report ID with PENDING status
4. **Redirect** → User is redirected to `/reports/{reportId}/status`
5. **Watch Progress** → User sees real-time progress updates (0-100%)
6. **View Report** → When complete, user is redirected to full report

### Benefits of Async Approach

- **Immediate Response**: User sees confirmation within 1-2 seconds
- **No Timeouts**: Long processing (30-60s) doesn't cause API timeouts
- **Real-time Feedback**: User can watch progress and estimated time
- **Better UX**: Clear status updates at each processing step
- **Scalable**: Backend can process multiple reports concurrently

### Error Handling

The status page handles all error scenarios:

- **Report Not Found**: Shows 404 error with retry button
- **Processing Failed**: Displays error message and details
- **Timeout**: Backend handles timeouts with automatic retry
- **Retry Logic**: Failed reports can be retried up to 3 times

### Testing Checklist

- [ ] File upload triggers report generation
- [ ] User sees loading state during upload
- [ ] Success toast appears on completion
- [ ] User is redirected to status page
- [ ] Status page polls every 2 seconds
- [ ] Progress bar updates correctly
- [ ] Final report displays when complete
- [ ] Error messages show when processing fails
- [ ] Retry button works for failed reports

## Related Documentation

- [Report Status Hook](../src/hooks/useReportStatus.ts)
- [Report Status Page](../src/app/reports/[reportId]/status/page.tsx)
- [Backend API Documentation](../backend/docs/async-report-processing.md)

/**
 * Report Status Page
 *
 * Real-time report generation status page with progress tracking.
 * Automatically polls status every 2 seconds and displays full report when complete.
 */

'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Card, CardBody, CardHeader } from '@nextui-org/card';
import { Progress } from '@nextui-org/progress';
import { Button } from '@nextui-org/button';
import { Spinner } from '@nextui-org/spinner';
import { Chip } from '@nextui-org/chip';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';

import { useReportStatus } from '@/hooks/useReportStatus';

/**
 * Format milliseconds to human-readable time
 */
function formatTime(ms: number | null): string {
  if (!ms) return 'Unknown';

  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);

  if (minutes > 0) {
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  }

  return `${seconds}s`;
}

/**
 * Get step display name
 */
function getStepDisplayName(step: string | null): string {
  const stepMap: Record<string, string> = {
    queued: 'Queued for Processing',
    initializing: 'Initializing',
    phi_detection: 'Detecting PHI',
    phi_detection_complete: 'PHI Detection Complete',
    clinical_filtering: 'Filtering Clinical Content',
    clinical_filtering_complete: 'Clinical Filtering Complete',
    icd10_inference: 'Extracting ICD-10 Codes',
    snomed_inference: 'Extracting SNOMED Codes',
    code_inference_complete: 'Code Inference Complete',
    ai_coding_analysis: 'AI Coding Analysis',
    ai_quality_analysis: 'AI Quality Analysis',
    finalizing_report: 'Finalizing Report',
    complete: 'Complete',
  };

  return stepMap[step || ''] || step || 'Processing';
}

/**
 * Get status color
 */
function getStatusColor(
  status: string
): 'default' | 'primary' | 'success' | 'warning' | 'danger' {
  switch (status) {
    case 'COMPLETE':
      return 'success';
    case 'FAILED':
      return 'danger';
    case 'PROCESSING':
      return 'primary';
    case 'PENDING':
      return 'warning';
    default:
      return 'default';
  }
}

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
    refresh,
  } = useReportStatus(reportId, {
    onComplete: () => {
      // Optionally show success notification
      console.log('Report complete!');
    },
    onFailed: () => {
      // Optionally show error notification
      console.error('Report failed!');
    },
  });

  // Redirect to full report when complete
  useEffect(() => {
    if (status === 'COMPLETE' && data?.encounterId) {
      // Wait a moment to show success state
      const timer = setTimeout(() => {
        router.push(`/reports/encounters/${data.encounterId}`);
      }, 2000);

      return () => clearTimeout(timer);
    }
  }, [status, data?.encounterId, router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-md">
          <CardBody className="flex flex-col items-center gap-4 p-8">
            <Spinner size="lg" />
            <p className="text-lg">Loading report status...</p>
          </CardBody>
        </Card>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="w-full max-w-md">
          <CardBody className="flex flex-col items-center gap-4 p-8">
            <ExclamationTriangleIcon className="w-16 h-16 text-danger" />
            <h2 className="text-xl font-semibold">Error Loading Report</h2>
            <p className="text-center text-default-500">{error}</p>
            <Button color="primary" onPress={refresh}>
              Try Again
            </Button>
          </CardBody>
        </Card>
      </div>
    );
  }

  return (
    <div className="container max-w-4xl mx-auto py-8 px-4">
      <Card className="mb-6">
        <CardHeader className="flex flex-col gap-2 items-start">
          <div className="flex items-center justify-between w-full">
            <h1 className="text-2xl font-bold">Report Generation Status</h1>
            <Chip color={getStatusColor(status || '')} variant="flat" size="lg">
              {status}
            </Chip>
          </div>
          <p className="text-default-500">Report ID: {reportId}</p>
        </CardHeader>

        <CardBody className="gap-6">
          {/* Progress Bar */}
          {status !== 'FAILED' && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="font-medium">
                  {getStepDisplayName(currentStep)}
                </span>
                <span className="text-default-500">{progress}%</span>
              </div>
              <Progress
                value={progress}
                color={status === 'COMPLETE' ? 'success' : 'primary'}
                size="lg"
                className="w-full"
              />
            </div>
          )}

          {/* Status-specific Content */}
          {status === 'PENDING' && (
            <div className="flex items-center gap-3 p-4 bg-warning-50 rounded-lg">
              <ClockIcon className="w-6 h-6 text-warning" />
              <div>
                <p className="font-semibold text-warning-800">
                  Queued for Processing
                </p>
                <p className="text-sm text-warning-600">
                  Your report is in the queue and will begin processing shortly.
                </p>
              </div>
            </div>
          )}

          {status === 'PROCESSING' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-4 bg-primary-50 rounded-lg">
                <Spinner color="primary" size="sm" />
                <div className="flex-1">
                  <p className="font-semibold text-primary-800">
                    Processing Report
                  </p>
                  <p className="text-sm text-primary-600">
                    Analyzing clinical notes and generating coding suggestions...
                  </p>
                </div>
              </div>

              {/* Processing Details */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="p-3 bg-default-100 rounded-lg">
                  <p className="text-default-500">Started</p>
                  <p className="font-semibold">
                    {data?.processingStartedAt
                      ? new Date(data.processingStartedAt).toLocaleTimeString()
                      : 'N/A'}
                  </p>
                </div>

                {estimatedTimeRemaining && (
                  <div className="p-3 bg-default-100 rounded-lg">
                    <p className="text-default-500">Est. Time Remaining</p>
                    <p className="font-semibold">
                      {formatTime(estimatedTimeRemaining)}
                    </p>
                  </div>
                )}
              </div>

              {/* Processing Steps */}
              <div className="space-y-2">
                <p className="text-sm font-semibold text-default-700">
                  Processing Steps:
                </p>
                <div className="space-y-1 text-sm">
                  {[
                    { name: 'PHI Detection', range: [0, 20] },
                    { name: 'Clinical Filtering', range: [20, 40] },
                    { name: 'Code Inference', range: [40, 70] },
                    { name: 'AI Analysis', range: [70, 100] },
                  ].map((step) => {
                    const isActive =
                      progress >= step.range[0] && progress < step.range[1];
                    const isComplete = progress >= step.range[1];

                    return (
                      <div
                        key={step.name}
                        className={`flex items-center gap-2 p-2 rounded ${
                          isActive
                            ? 'bg-primary-50'
                            : isComplete
                            ? 'bg-success-50'
                            : 'bg-default-50'
                        }`}
                      >
                        {isComplete ? (
                          <CheckCircleIcon className="w-4 h-4 text-success" />
                        ) : isActive ? (
                          <Spinner size="sm" color="primary" />
                        ) : (
                          <div className="w-4 h-4 border-2 border-default-300 rounded-full" />
                        )}
                        <span
                          className={
                            isActive || isComplete
                              ? 'font-semibold'
                              : 'text-default-500'
                          }
                        >
                          {step.name}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {status === 'COMPLETE' && (
            <div className="flex items-center gap-3 p-4 bg-success-50 rounded-lg">
              <CheckCircleIcon className="w-8 h-8 text-success" />
              <div className="flex-1">
                <p className="font-semibold text-success-800">
                  Report Complete!
                </p>
                <p className="text-sm text-success-600">
                  Processing completed in{' '}
                  {formatTime(data?.processingTimeMs || null)}
                </p>
              </div>
            </div>
          )}

          {status === 'FAILED' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-4 bg-danger-50 rounded-lg">
                <ExclamationTriangleIcon className="w-8 h-8 text-danger" />
                <div className="flex-1">
                  <p className="font-semibold text-danger-800">
                    Processing Failed
                  </p>
                  <p className="text-sm text-danger-600">
                    {data?.errorMessage || error || 'An unknown error occurred'}
                  </p>
                </div>
              </div>

              {/* Error Details */}
              {data?.errorDetails && (
                <details className="p-4 bg-default-100 rounded-lg">
                  <summary className="cursor-pointer font-semibold text-sm">
                    Technical Details
                  </summary>
                  <pre className="mt-2 text-xs overflow-x-auto">
                    {JSON.stringify(data.errorDetails, null, 2)}
                  </pre>
                </details>
              )}

              {/* Retry Info */}
              {data?.retryCount !== undefined && (
                <p className="text-sm text-default-500">
                  Retry attempts: {data.retryCount} / 3
                </p>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            {status === 'FAILED' && (
              <Button
                color="primary"
                variant="flat"
                startContent={<ArrowPathIcon className="w-4 h-4" />}
                onPress={refresh}
              >
                Retry
              </Button>
            )}

            {status === 'COMPLETE' && (
              <Button
                color="primary"
                onPress={() =>
                  data?.encounterId &&
                  router.push(`/reports/encounters/${data.encounterId}`)
                }
              >
                View Full Report
              </Button>
            )}

            <Button
              variant="light"
              onPress={() => router.push('/members/encounters')}
            >
              Back to Encounters
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* Debug Info (Development Only) */}
      {process.env.NODE_ENV === 'development' && data && (
        <Card>
          <CardHeader>
            <h3 className="text-sm font-semibold">Debug Info</h3>
          </CardHeader>
          <CardBody>
            <pre className="text-xs overflow-x-auto">
              {JSON.stringify(data, null, 2)}
            </pre>
          </CardBody>
        </Card>
      )}
    </div>
  );
}

/**
 * EncounterStatusBadge Component
 *
 * Displays the current report status for an encounter with real-time updates.
 * Can be embedded in encounter lists, cards, or detail views.
 */

'use client';

import { Button } from '@nextui-org/button';
import { Tooltip } from '@nextui-org/tooltip';
import { useRouter } from 'next/navigation';
import {
  ArrowPathIcon,
  EyeIcon,
  ClockIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

import { useReportStatus } from '@/hooks/useReportStatus';
import { ReportProgressMini, ReportStatusChip } from './ReportProgress';
import type { ReportStatus } from '@/hooks/useReportStatus';

export interface EncounterStatusBadgeProps {
  /** Encounter ID */
  encounterId: string;
  /** Report ID (if known) */
  reportId?: string;
  /** Show actions (View Report, Retry) */
  showActions?: boolean;
  /** Compact mode */
  compact?: boolean;
  /** Custom class name */
  className?: string;
}

/**
 * Badge showing encounter report status with actions
 */
export function EncounterStatusBadge({
  encounterId,
  reportId,
  showActions = true,
  compact = false,
  className = '',
}: EncounterStatusBadgeProps) {
  const router = useRouter();

  // Poll report status if reportId is provided
  const { status, progress, error, data } = useReportStatus(reportId || null, {
    enabled: !!reportId,
  });

  // No report yet - show generate button
  if (!reportId) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <ReportStatusChip status="PENDING" />
        {showActions && (
          <Button
            size="sm"
            color="primary"
            variant="flat"
            onPress={() => {
              // Trigger report generation
              fetch(`/api/v1/reports/encounters/${encounterId}/reports`, {
                method: 'POST',
              })
                .then((res) => res.json())
                .then(({ reportId: newReportId }) => {
                  router.push(`/reports/${newReportId}/status`);
                })
                .catch((err) => {
                  console.error('Failed to generate report:', err);
                });
            }}
          >
            Generate Report
          </Button>
        )}
      </div>
    );
  }

  // Loading state
  if (!status) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="w-20 h-6 bg-default-200 animate-pulse rounded" />
      </div>
    );
  }

  // Compact mode - just show status and progress
  if (compact) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <ReportStatusChip status={status} />
        {(status === 'PENDING' || status === 'PROCESSING') && (
          <ReportProgressMini progress={progress} status={status} />
        )}
      </div>
    );
  }

  // Full mode with actions
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* Status Chip */}
      <ReportStatusChip status={status} />

      {/* Progress Indicator for Processing Reports */}
      {(status === 'PENDING' || status === 'PROCESSING') && (
        <div className="flex items-center gap-2">
          <ReportProgressMini progress={progress} status={status} />
          {data?.estimatedTimeRemainingMs && (
            <Tooltip content="Estimated time remaining">
              <div className="flex items-center gap-1 text-xs text-default-500">
                <ClockIcon className="w-3 h-3" />
                <span>{Math.ceil(data.estimatedTimeRemainingMs / 1000)}s</span>
              </div>
            </Tooltip>
          )}
        </div>
      )}

      {/* Actions */}
      {showActions && (
        <div className="flex items-center gap-2">
          {/* View Report Button (Complete) */}
          {status === 'COMPLETE' && (
            <Tooltip content="View full report">
              <Button
                size="sm"
                color="primary"
                variant="flat"
                isIconOnly
                onPress={() => router.push(`/reports/encounters/${encounterId}`)}
              >
                <EyeIcon className="w-4 h-4" />
              </Button>
            </Tooltip>
          )}

          {/* Watch Progress Button (Processing) */}
          {(status === 'PENDING' || status === 'PROCESSING') && (
            <Tooltip content="Watch progress">
              <Button
                size="sm"
                color="primary"
                variant="light"
                isIconOnly
                onPress={() => router.push(`/reports/${reportId}/status`)}
              >
                <ClockIcon className="w-4 h-4" />
              </Button>
            </Tooltip>
          )}

          {/* Retry Button (Failed) */}
          {status === 'FAILED' && (
            <Tooltip content={error || 'Retry report generation'}>
              <Button
                size="sm"
                color="danger"
                variant="flat"
                isIconOnly
                onPress={() => {
                  // Retry failed report
                  fetch(`/api/v1/reports/${reportId}/retry`, {
                    method: 'POST',
                  })
                    .then(() => {
                      router.push(`/reports/${reportId}/status`);
                    })
                    .catch((err) => {
                      console.error('Failed to retry report:', err);
                    });
                }}
              >
                <ArrowPathIcon className="w-4 h-4" />
              </Button>
            </Tooltip>
          )}
        </div>
      )}

      {/* Error Indicator */}
      {status === 'FAILED' && error && (
        <Tooltip content={error}>
          <ExclamationTriangleIcon className="w-5 h-5 text-danger" />
        </Tooltip>
      )}
    </div>
  );
}

/**
 * Simple status indicator for table rows
 */
export function EncounterStatusIndicator({
  status,
  progress,
}: {
  status: ReportStatus | null;
  progress: number;
}) {
  if (!status) {
    return <span className="text-xs text-default-400">No report</span>;
  }

  return (
    <div className="flex items-center gap-2">
      <ReportStatusChip status={status} />
      {(status === 'PENDING' || status === 'PROCESSING') && (
        <span className="text-xs text-default-500">{progress}%</span>
      )}
    </div>
  );
}

/**
 * Batch status display for multiple encounters
 */
export function BatchStatusSummary({
  statuses,
}: {
  statuses: { status: ReportStatus; count: number }[];
}) {
  const total = statuses.reduce((sum, s) => sum + s.count, 0);

  return (
    <div className="flex flex-wrap gap-2">
      {statuses.map(({ status, count }) => (
        <div key={status} className="flex items-center gap-1.5">
          <ReportStatusChip status={status} />
          <span className="text-sm text-default-600">
            {count} / {total}
          </span>
        </div>
      ))}
    </div>
  );
}

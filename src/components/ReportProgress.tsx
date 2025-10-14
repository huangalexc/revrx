/**
 * ReportProgress Component
 *
 * Visual progress indicator for async report generation.
 * Displays progress bar, step indicators, and estimated time remaining.
 */

'use client';

import { useMemo } from 'react';
import { Progress } from '@nextui-org/progress';
import { Chip } from '@nextui-org/chip';
import { CheckCircleIcon, ClockIcon } from '@heroicons/react/24/solid';
import { SparklesIcon } from '@heroicons/react/24/outline';
import type { ReportStatus } from '@/hooks/useReportStatus';

export interface ReportProgressProps {
  /** Current progress percentage (0-100) */
  progress: number;
  /** Current processing step */
  currentStep?: string | null;
  /** Report status */
  status: ReportStatus;
  /** Estimated time remaining in milliseconds */
  estimatedTimeRemaining?: number | null;
  /** Compact mode - smaller size */
  compact?: boolean;
  /** Show step details */
  showSteps?: boolean;
  /** Custom class name */
  className?: string;
}

interface ProcessingStep {
  id: string;
  name: string;
  shortName: string;
  icon: string;
  progressRange: [number, number];
}

const PROCESSING_STEPS: ProcessingStep[] = [
  {
    id: 'phi',
    name: 'PHI Detection',
    shortName: 'PHI',
    icon: '🔒',
    progressRange: [0, 20],
  },
  {
    id: 'filter',
    name: 'Clinical Filtering',
    shortName: 'Filter',
    icon: '🔍',
    progressRange: [20, 40],
  },
  {
    id: 'codes',
    name: 'Code Inference',
    shortName: 'Codes',
    icon: '📋',
    progressRange: [40, 70],
  },
  {
    id: 'ai',
    name: 'AI Analysis',
    shortName: 'AI',
    icon: '✨',
    progressRange: [70, 100],
  },
];

/**
 * Format milliseconds to human-readable time
 */
function formatTimeRemaining(ms: number | null | undefined): string {
  if (!ms || ms <= 0) return '';

  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);

  if (minutes > 0) {
    const remainingSeconds = seconds % 60;
    return `~${minutes}m ${remainingSeconds}s remaining`;
  }

  return `~${seconds}s remaining`;
}

/**
 * Get step status based on progress
 */
function getStepStatus(
  step: ProcessingStep,
  progress: number
): 'pending' | 'active' | 'complete' {
  if (progress >= step.progressRange[1]) {
    return 'complete';
  }
  if (progress >= step.progressRange[0]) {
    return 'active';
  }
  return 'pending';
}

/**
 * Get progress bar color based on status
 */
function getProgressColor(
  status: ReportStatus
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

export function ReportProgress({
  progress,
  currentStep,
  status,
  estimatedTimeRemaining,
  compact = false,
  showSteps = true,
  className = '',
}: ReportProgressProps) {
  // Calculate which step is currently active
  const activeStepIndex = useMemo(() => {
    return PROCESSING_STEPS.findIndex(
      (step) => progress >= step.progressRange[0] && progress < step.progressRange[1]
    );
  }, [progress]);

  // Clamp progress to 0-100
  const clampedProgress = Math.max(0, Math.min(100, progress));

  if (compact) {
    return (
      <div className={`flex items-center gap-3 ${className}`}>
        <Progress
          value={clampedProgress}
          color={getProgressColor(status)}
          size="sm"
          className="flex-1"
          aria-label={`Report processing progress: ${clampedProgress}%`}
        />
        <span className="text-sm font-medium text-default-600 min-w-[45px] text-right">
          {clampedProgress}%
        </span>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between items-center text-sm">
          <span className="font-medium text-default-700">
            {status === 'COMPLETE' ? 'Complete' : 'Processing Report'}
          </span>
          <div className="flex items-center gap-2">
            <span className="text-default-500">{clampedProgress}%</span>
            {estimatedTimeRemaining && estimatedTimeRemaining > 0 && (
              <span className="text-xs text-default-400 flex items-center gap-1">
                <ClockIcon className="w-3 h-3" />
                {formatTimeRemaining(estimatedTimeRemaining)}
              </span>
            )}
          </div>
        </div>

        <Progress
          value={clampedProgress}
          color={getProgressColor(status)}
          size="lg"
          className="w-full"
          aria-label={`Report processing progress: ${clampedProgress}%`}
        />
      </div>

      {/* Step Indicators */}
      {showSteps && (
        <div className="grid grid-cols-4 gap-2">
          {PROCESSING_STEPS.map((step, index) => {
            const stepStatus = getStepStatus(step, clampedProgress);
            const isActive = index === activeStepIndex;

            return (
              <div
                key={step.id}
                className={`relative flex flex-col items-center gap-2 p-3 rounded-lg transition-all ${
                  stepStatus === 'complete'
                    ? 'bg-success-50'
                    : stepStatus === 'active'
                    ? 'bg-primary-50 ring-2 ring-primary-200'
                    : 'bg-default-100'
                }`}
              >
                {/* Step Icon/Status */}
                <div
                  className={`flex items-center justify-center w-10 h-10 rounded-full transition-all ${
                    stepStatus === 'complete'
                      ? 'bg-success-500'
                      : stepStatus === 'active'
                      ? 'bg-primary-500'
                      : 'bg-default-300'
                  }`}
                >
                  {stepStatus === 'complete' ? (
                    <CheckCircleIcon className="w-6 h-6 text-white" />
                  ) : stepStatus === 'active' ? (
                    <div className="relative">
                      <span className="text-xl">{step.icon}</span>
                      {isActive && (
                        <SparklesIcon className="absolute -top-1 -right-1 w-4 h-4 text-primary-500 animate-pulse" />
                      )}
                    </div>
                  ) : (
                    <span className="text-xl opacity-50">{step.icon}</span>
                  )}
                </div>

                {/* Step Name */}
                <div className="text-center">
                  <p
                    className={`text-xs font-medium ${
                      stepStatus === 'complete'
                        ? 'text-success-700'
                        : stepStatus === 'active'
                        ? 'text-primary-700'
                        : 'text-default-500'
                    }`}
                  >
                    {step.shortName}
                  </p>
                  <p className="text-[10px] text-default-400 mt-0.5">
                    {step.progressRange[0]}-{step.progressRange[1]}%
                  </p>
                </div>

                {/* Active indicator */}
                {isActive && (
                  <div className="absolute -bottom-1 left-1/2 -translate-x-1/2">
                    <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Current Step Details */}
      {currentStep && status === 'PROCESSING' && (
        <div className="flex items-center gap-2 p-3 bg-primary-50 rounded-lg">
          <div className="w-2 h-2 bg-primary-500 rounded-full animate-pulse" />
          <p className="text-sm text-primary-700">
            <span className="font-semibold">Current: </span>
            {currentStep.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
          </p>
        </div>
      )}
    </div>
  );
}

/**
 * Minimal progress indicator for inline use
 */
export function ReportProgressMini({
  progress,
  status,
}: {
  progress: number;
  status: ReportStatus;
}) {
  const clampedProgress = Math.max(0, Math.min(100, progress));

  return (
    <div className="flex items-center gap-2">
      <Progress
        value={clampedProgress}
        color={getProgressColor(status)}
        size="sm"
        className="w-24"
        aria-label={`${clampedProgress}%`}
      />
      <span className="text-xs font-medium text-default-500 min-w-[35px]">
        {clampedProgress}%
      </span>
    </div>
  );
}

/**
 * Status chip with icon
 */
export function ReportStatusChip({ status }: { status: ReportStatus }) {
  const config = {
    PENDING: {
      color: 'warning' as const,
      icon: '⏳',
      label: 'Pending',
    },
    PROCESSING: {
      color: 'primary' as const,
      icon: '⚡',
      label: 'Processing',
    },
    COMPLETE: {
      color: 'success' as const,
      icon: '✓',
      label: 'Complete',
    },
    FAILED: {
      color: 'danger' as const,
      icon: '✗',
      label: 'Failed',
    },
  };

  const { color, icon, label } = config[status] || config.PENDING;

  return (
    <Chip color={color} variant="flat" size="sm" startContent={<span>{icon}</span>}>
      {label}
    </Chip>
  );
}

/**
 * Notification Service for Report Processing
 *
 * Provides toast notifications for report processing events and milestones.
 * Integrates with the report status hook to show progress updates.
 */

import { toast } from 'sonner';
import type { ReportStatus, ReportStatusData } from '@/hooks/useReportStatus';

export interface NotificationOptions {
  /** Auto-dismiss duration in milliseconds */
  duration?: number;
  /** Show action button */
  action?: {
    label: string;
    onClick: () => void;
  };
  /** Toast position */
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'top-center' | 'bottom-center';
}

/**
 * Show notification when report processing starts
 */
export function notifyProcessingStarted(reportId: string, options?: NotificationOptions) {
  return toast.info('Report Processing Started', {
    description: 'Your report is being generated. This may take up to 60 seconds.',
    duration: options?.duration ?? 5000,
    action: options?.action,
  });
}

/**
 * Show notification when report reaches a milestone
 */
export function notifyMilestone(
  progress: number,
  milestone: number,
  options?: NotificationOptions
) {
  if (progress >= milestone && progress < milestone + 10) {
    const messages: Record<number, { title: string; description: string }> = {
      25: {
        title: '25% Complete',
        description: 'PHI detection and clinical filtering in progress...',
      },
      50: {
        title: 'Halfway There! 🎉',
        description: 'Code inference completed. Starting AI analysis...',
      },
      75: {
        title: '75% Complete',
        description: 'AI coding analysis in progress...',
      },
    };

    const message = messages[milestone];
    if (message) {
      return toast.info(message.title, {
        description: message.description,
        duration: options?.duration ?? 4000,
      });
    }
  }
}

/**
 * Show notification when report is complete
 */
export function notifyReportComplete(
  data: ReportStatusData,
  options?: NotificationOptions
) {
  const processingTime = data.processingTimeMs
    ? `in ${Math.round(data.processingTimeMs / 1000)}s`
    : '';

  return toast.success('Report Ready! ✨', {
    description: `Your coding intelligence report has been generated ${processingTime}.`,
    duration: options?.duration ?? 6000,
    action: options?.action ?? {
      label: 'View Report',
      onClick: () => {
        window.location.href = `/reports/encounters/${data.encounterId}`;
      },
    },
  });
}

/**
 * Show notification when report processing fails
 */
export function notifyReportFailed(
  data: ReportStatusData,
  options?: NotificationOptions
) {
  const retryAction = options?.action ?? {
    label: 'Retry',
    onClick: () => {
      window.location.reload();
    },
  };

  return toast.error('Report Processing Failed', {
    description: data.errorMessage || 'An error occurred while generating your report.',
    duration: options?.duration ?? 10000,
    action: retryAction,
  });
}

/**
 * Show notification with custom message
 */
export function notifyCustom(
  status: 'info' | 'success' | 'warning' | 'error',
  title: string,
  description?: string,
  options?: NotificationOptions
) {
  const toastFn = {
    info: toast.info,
    success: toast.success,
    warning: toast.warning,
    error: toast.error,
  }[status];

  return toastFn(title, {
    description,
    duration: options?.duration ?? 5000,
    action: options?.action,
  });
}

/**
 * Hook-compatible notification handler
 * Automatically shows notifications based on status changes
 */
export class ReportNotificationHandler {
  private lastProgress = 0;
  private notifiedMilestones = new Set<number>();
  private hasNotifiedStart = false;

  /**
   * Handle status change event
   */
  onStatusChange(status: ReportStatus, data: ReportStatusData | null) {
    // Notify when processing starts
    if (status === 'PROCESSING' && !this.hasNotifiedStart) {
      notifyProcessingStarted(data?.reportId || '');
      this.hasNotifiedStart = true;
    }

    // Notify on completion
    if (status === 'COMPLETE' && data) {
      notifyReportComplete(data);
    }

    // Notify on failure
    if (status === 'FAILED' && data) {
      notifyReportFailed(data);
    }
  }

  /**
   * Handle progress update
   */
  onProgressUpdate(progress: number) {
    // Check for milestone achievements
    const milestones = [25, 50, 75];

    for (const milestone of milestones) {
      if (
        progress >= milestone &&
        this.lastProgress < milestone &&
        !this.notifiedMilestones.has(milestone)
      ) {
        notifyMilestone(progress, milestone);
        this.notifiedMilestones.add(milestone);
      }
    }

    this.lastProgress = progress;
  }

  /**
   * Reset handler state (useful when monitoring a new report)
   */
  reset() {
    this.lastProgress = 0;
    this.notifiedMilestones.clear();
    this.hasNotifiedStart = false;
  }
}

/**
 * Create a notification handler instance
 */
export function createNotificationHandler() {
  return new ReportNotificationHandler();
}

/**
 * Batch notification helpers for multiple reports
 */
export function notifyBatchProcessingStarted(count: number) {
  return toast.info(`Processing ${count} Reports`, {
    description: 'Your reports are being generated in the background.',
    duration: 5000,
  });
}

export function notifyBatchComplete(completed: number, failed: number) {
  if (failed === 0) {
    return toast.success(`${completed} Reports Complete! 🎉`, {
      description: 'All reports have been generated successfully.',
      duration: 6000,
    });
  } else {
    return toast.warning(`Batch Processing Complete`, {
      description: `${completed} succeeded, ${failed} failed.`,
      duration: 8000,
      action: {
        label: 'View Details',
        onClick: () => {
          window.location.href = '/reports';
        },
      },
    });
  }
}

/**
 * Error-specific notifications
 */
export function notifyTimeout(reportId: string) {
  return toast.error('Processing Timeout', {
    description: 'Report processing took too long. The system will automatically retry.',
    duration: 8000,
  });
}

export function notifyNetworkError() {
  return toast.error('Network Error', {
    description: 'Unable to connect to the server. Please check your connection.',
    duration: 8000,
    action: {
      label: 'Retry',
      onClick: () => window.location.reload(),
    },
  });
}

export function notifyPermissionError() {
  return toast.error('Permission Denied', {
    description: 'You do not have permission to access this report.',
    duration: 6000,
  });
}

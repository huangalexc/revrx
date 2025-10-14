/**
 * useReportStatus Hook
 *
 * Custom React hook to poll report status from the backend API.
 * Automatically polls every 2 seconds and stops when report is complete or failed.
 *
 * @example
 * ```tsx
 * const { status, progress, currentStep, error, isLoading } = useReportStatus(reportId);
 *
 * if (isLoading) return <Spinner />;
 * if (error) return <ErrorMessage>{error}</ErrorMessage>;
 * if (status === 'COMPLETE') return <ReportView reportId={reportId} />;
 *
 * return <ProgressBar progress={progress} step={currentStep} />;
 * ```
 */

import { useState, useEffect, useRef, useCallback } from 'react';

export type ReportStatus = 'PENDING' | 'PROCESSING' | 'COMPLETE' | 'FAILED';

export interface ReportStatusData {
  reportId: string;
  encounterId: string;
  status: ReportStatus;
  progressPercent: number | null;
  currentStep: string | null;
  processingStartedAt?: string;
  processingCompletedAt?: string;
  processingTimeMs?: number;
  estimatedTimeRemainingMs?: number;
  errorMessage?: string;
  errorDetails?: any;
  retryCount?: number;
}

export interface UseReportStatusResult {
  /** Current report status data */
  data: ReportStatusData | null;
  /** Report status (PENDING, PROCESSING, COMPLETE, FAILED) */
  status: ReportStatus | null;
  /** Progress percentage (0-100) */
  progress: number;
  /** Current processing step */
  currentStep: string | null;
  /** Estimated time remaining in milliseconds */
  estimatedTimeRemaining: number | null;
  /** Error message if status is FAILED */
  error: string | null;
  /** Loading state for initial fetch */
  isLoading: boolean;
  /** Whether polling is active */
  isPolling: boolean;
  /** Manually trigger a refresh */
  refresh: () => Promise<void>;
}

export interface UseReportStatusOptions {
  /** Polling interval in milliseconds (default: 2000) */
  pollInterval?: number;
  /** Whether to enable polling (default: true) */
  enabled?: boolean;
  /** Callback when status changes to COMPLETE */
  onComplete?: (data: ReportStatusData) => void;
  /** Callback when status changes to FAILED */
  onFailed?: (data: ReportStatusData) => void;
  /** Callback on any status change */
  onStatusChange?: (status: ReportStatus) => void;
}

/**
 * Hook to fetch and poll report status
 */
export function useReportStatus(
  reportId: string | null | undefined,
  options: UseReportStatusOptions = {}
): UseReportStatusResult {
  const {
    pollInterval = 2000,
    enabled = true,
    onComplete,
    onFailed,
    onStatusChange,
  } = options;

  const [data, setData] = useState<ReportStatusData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState<boolean>(false);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const previousStatusRef = useRef<ReportStatus | null>(null);

  /**
   * Fetch report status from API
   */
  const fetchStatus = useCallback(async () => {
    if (!reportId) {
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch(`/api/v1/reports/${reportId}/status`);

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Report not found');
        }
        throw new Error(`Failed to fetch report status: ${response.statusText}`);
      }

      const statusData: ReportStatusData = await response.json();
      setData(statusData);
      setError(null);
      setIsLoading(false);

      // Handle status changes
      if (previousStatusRef.current !== statusData.status) {
        previousStatusRef.current = statusData.status;
        onStatusChange?.(statusData.status);

        if (statusData.status === 'COMPLETE') {
          onComplete?.(statusData);
        } else if (statusData.status === 'FAILED') {
          onFailed?.(statusData);
        }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      setIsLoading(false);
      console.error('Error fetching report status:', err);
    }
  }, [reportId, onComplete, onFailed, onStatusChange]);

  /**
   * Start polling
   */
  const startPolling = useCallback(() => {
    if (!enabled || !reportId) return;

    setIsPolling(true);

    // Initial fetch
    fetchStatus();

    // Set up polling interval
    intervalRef.current = setInterval(() => {
      fetchStatus();
    }, pollInterval);
  }, [enabled, reportId, pollInterval, fetchStatus]);

  /**
   * Stop polling
   */
  const stopPolling = useCallback(() => {
    setIsPolling(false);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  /**
   * Effect to manage polling lifecycle
   */
  useEffect(() => {
    if (!reportId || !enabled) {
      stopPolling();
      return;
    }

    // Start polling
    startPolling();

    // Auto-stop polling when status is terminal (COMPLETE or FAILED)
    if (data?.status === 'COMPLETE' || data?.status === 'FAILED') {
      stopPolling();
    }

    // Cleanup on unmount
    return () => {
      stopPolling();
    };
  }, [reportId, enabled, data?.status, startPolling, stopPolling]);

  /**
   * Manual refresh function
   */
  const refresh = useCallback(async () => {
    await fetchStatus();
  }, [fetchStatus]);

  return {
    data,
    status: data?.status ?? null,
    progress: data?.progressPercent ?? 0,
    currentStep: data?.currentStep ?? null,
    estimatedTimeRemaining: data?.estimatedTimeRemainingMs ?? null,
    error: error ?? data?.errorMessage ?? null,
    isLoading,
    isPolling,
    refresh,
  };
}

/**
 * Hook variant that returns just the terminal status (for simpler use cases)
 */
export function useReportCompletion(reportId: string | null | undefined) {
  const { status, error, progress } = useReportStatus(reportId);

  return {
    isComplete: status === 'COMPLETE',
    isFailed: status === 'FAILED',
    isProcessing: status === 'PROCESSING' || status === 'PENDING',
    progress,
    error,
  };
}

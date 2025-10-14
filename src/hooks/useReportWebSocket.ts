/**
 * useReportWebSocket Hook
 *
 * Custom React hook for real-time report updates via WebSocket.
 * Automatically falls back to polling if WebSocket is unavailable.
 *
 * @example
 * ```tsx
 * const { status, progress, error, isConnected } = useReportWebSocket(reportId);
 *
 * if (!isConnected) return <div>Connecting...</div>;
 * return <ProgressBar progress={progress} />;
 * ```
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useReportStatus, type ReportStatus, type ReportStatusData } from './useReportStatus';

export interface UseReportWebSocketOptions {
  /** Whether to enable WebSocket connection (default: true) */
  enabled?: boolean;
  /** Fallback to polling if WebSocket fails (default: true) */
  enablePollingFallback?: boolean;
  /** WebSocket reconnect attempts (default: 3) */
  maxReconnectAttempts?: number;
  /** Callback when status changes to COMPLETE */
  onComplete?: (data: ReportStatusData) => void;
  /** Callback when status changes to FAILED */
  onFailed?: (data: ReportStatusData) => void;
  /** Callback on any status change */
  onStatusChange?: (status: ReportStatus) => void;
  /** Callback when WebSocket connects */
  onConnect?: () => void;
  /** Callback when WebSocket disconnects */
  onDisconnect?: () => void;
}

export interface UseReportWebSocketResult {
  /** Current report status data */
  data: ReportStatusData | null;
  /** Report status */
  status: ReportStatus | null;
  /** Progress percentage (0-100) */
  progress: number;
  /** Current processing step */
  currentStep: string | null;
  /** Estimated time remaining in milliseconds */
  estimatedTimeRemaining: number | null;
  /** Error message */
  error: string | null;
  /** Loading state for initial connection */
  isLoading: boolean;
  /** WebSocket connection state */
  isConnected: boolean;
  /** Whether using polling fallback */
  isPolling: boolean;
  /** Manually trigger reconnect */
  reconnect: () => void;
}

/**
 * Get WebSocket URL from current location
 */
function getWebSocketUrl(reportId: string): string {
  // Determine protocol (ws or wss)
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;

  return `${protocol}//${host}/api/v1/ws/reports/${reportId}`;
}

/**
 * Hook to connect to WebSocket for real-time report updates
 */
export function useReportWebSocket(
  reportId: string | null | undefined,
  options: UseReportWebSocketOptions = {}
): UseReportWebSocketResult {
  const {
    enabled = true,
    enablePollingFallback = true,
    maxReconnectAttempts = 3,
    onComplete,
    onFailed,
    onStatusChange,
    onConnect,
    onDisconnect,
  } = options;

  const [data, setData] = useState<ReportStatusData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [usePollingFallback, setUsePollingFallback] = useState<boolean>(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const previousStatusRef = useRef<ReportStatus | null>(null);

  // Polling fallback using useReportStatus
  const pollingResult = useReportStatus(
    reportId,
    {
      enabled: usePollingFallback && enablePollingFallback,
      onComplete,
      onFailed,
      onStatusChange,
    }
  );

  /**
   * Connect to WebSocket
   */
  const connect = useCallback(() => {
    if (!reportId || !enabled || usePollingFallback) {
      return;
    }

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    try {
      const wsUrl = getWebSocketUrl(reportId);
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('WebSocket connected:', reportId);
        setIsConnected(true);
        setIsLoading(false);
        setError(null);
        reconnectAttemptsRef.current = 0;
        onConnect?.();

        // Send ping to keep connection alive
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 30000); // Ping every 30 seconds

        // Store interval for cleanup
        (ws as any).pingInterval = pingInterval;
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          switch (message.type) {
            case 'connected':
              console.log('WebSocket handshake complete');
              break;

            case 'status_update':
              const statusData = message.data;
              setData(statusData);
              setError(null);

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
              break;

            case 'final_status':
              console.log('Report reached terminal state:', message.data.status);
              // Connection will close automatically
              break;

            case 'error':
              console.error('WebSocket error message:', message.message);
              setError(message.message);
              break;

            case 'pong':
              // Keep-alive response
              break;

            default:
              console.warn('Unknown WebSocket message type:', message.type);
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError('WebSocket connection error');
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setIsConnected(false);
        onDisconnect?.();

        // Clear ping interval
        if ((ws as any).pingInterval) {
          clearInterval((ws as any).pingInterval);
        }

        // Attempt reconnect if not intentional close
        if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);

          console.log(
            `Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts && enablePollingFallback) {
          // Fall back to polling
          console.log('Max reconnect attempts reached, falling back to polling');
          setUsePollingFallback(true);
          setIsLoading(false);
        } else {
          setIsLoading(false);
        }
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      setError('Failed to establish WebSocket connection');
      setIsLoading(false);

      // Fall back to polling
      if (enablePollingFallback) {
        setUsePollingFallback(true);
      }
    }
  }, [reportId, enabled, usePollingFallback, enablePollingFallback, maxReconnectAttempts, onConnect, onDisconnect, onComplete, onFailed, onStatusChange]);

  /**
   * Disconnect WebSocket
   */
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setIsConnected(false);
  }, []);

  /**
   * Manual reconnect
   */
  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    setUsePollingFallback(false);
    disconnect();
    connect();
  }, [connect, disconnect]);

  /**
   * Effect to manage connection lifecycle
   */
  useEffect(() => {
    if (!reportId || !enabled) {
      disconnect();
      return;
    }

    // Check if report is in terminal state - don't connect
    if (data?.status === 'COMPLETE' || data?.status === 'FAILED') {
      disconnect();
      return;
    }

    // Connect if not using polling fallback
    if (!usePollingFallback) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, [reportId, enabled, data?.status, usePollingFallback, connect, disconnect]);

  // Return polling result if using fallback
  if (usePollingFallback && enablePollingFallback) {
    return {
      ...pollingResult,
      isConnected: false,
      isPolling: true,
      reconnect,
    };
  }

  // Return WebSocket result
  return {
    data,
    status: data?.status ?? null,
    progress: data?.progressPercent ?? 0,
    currentStep: data?.currentStep ?? null,
    estimatedTimeRemaining: data?.estimatedTimeRemainingMs ?? null,
    error: error ?? data?.errorMessage ?? null,
    isLoading,
    isConnected,
    isPolling: false,
    reconnect,
  };
}

/**
 * Hook variant that prefers WebSocket but seamlessly falls back to polling
 */
export function useReportStatusOptimized(
  reportId: string | null | undefined,
  options?: UseReportWebSocketOptions
) {
  return useReportWebSocket(reportId, {
    ...options,
    enablePollingFallback: true,
  });
}

'use client';

import React, { ErrorInfo } from 'react';
import { AlertCircle, RefreshCw, Home } from 'lucide-react';
import { Button } from '@heroui/react';

interface ErrorFallbackProps {
  error: Error | null;
  errorInfo?: ErrorInfo | null;
  onReset?: () => void;
  variant?: 'default' | 'minimal' | 'detailed';
}

/**
 * ErrorFallback Component
 *
 * Displays error information with different variants for different use cases.
 *
 * Variants:
 * - default: Full error display with actions
 * - minimal: Compact inline error message
 * - detailed: Includes error stack trace in development
 */
export default function ErrorFallback({
  error,
  errorInfo,
  onReset,
  variant = 'default',
}: ErrorFallbackProps) {
  const isDevelopment = process.env.NODE_ENV === 'development';

  // Minimal variant - compact inline error
  if (variant === 'minimal') {
    return (
      <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-lg">
        <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
        <div className="flex-1">
          <p className="text-sm text-red-800">
            {error?.message || 'Something went wrong'}
          </p>
        </div>
        {onReset && (
          <Button
            size="sm"
            variant="light"
            color="danger"
            onClick={onReset}
            startContent={<RefreshCw className="w-4 h-4" />}
          >
            Retry
          </Button>
        )}
      </div>
    );
  }

  // Detailed variant - includes stack trace in development
  if (variant === 'detailed') {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-start gap-3 mb-4">
          <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-red-900 mb-1">
              Error Occurred
            </h3>
            <p className="text-sm text-red-700">
              {error?.message || 'An unexpected error occurred'}
            </p>
          </div>
        </div>

        {isDevelopment && error?.stack && (
          <div className="mt-4">
            <details className="text-xs">
              <summary className="cursor-pointer font-medium text-red-800 mb-2">
                Error Details (Development Only)
              </summary>
              <pre className="p-4 bg-red-100 rounded border border-red-300 overflow-auto text-red-900">
                {error.stack}
              </pre>
            </details>
          </div>
        )}

        {isDevelopment && errorInfo?.componentStack && (
          <div className="mt-4">
            <details className="text-xs">
              <summary className="cursor-pointer font-medium text-red-800 mb-2">
                Component Stack (Development Only)
              </summary>
              <pre className="p-4 bg-red-100 rounded border border-red-300 overflow-auto text-red-900">
                {errorInfo.componentStack}
              </pre>
            </details>
          </div>
        )}

        <div className="flex gap-3 mt-6">
          {onReset && (
            <Button
              color="danger"
              variant="flat"
              onClick={onReset}
              startContent={<RefreshCw className="w-4 h-4" />}
            >
              Try Again
            </Button>
          )}
          <Button
            variant="bordered"
            onClick={() => (window.location.href = '/')}
            startContent={<Home className="w-4 h-4" />}
          >
            Go Home
          </Button>
        </div>
      </div>
    );
  }

  // Default variant - full error display
  return (
    <div className="flex items-center justify-center min-h-[400px] p-6">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
          <div className="flex items-start gap-3 mb-4">
            <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
              <AlertCircle className="w-6 h-6 text-red-600" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900 mb-1">
                Something went wrong
              </h3>
              <p className="text-sm text-gray-600">
                {error?.message || 'An unexpected error occurred. Please try again.'}
              </p>
            </div>
          </div>

          {isDevelopment && error && (
            <div className="mb-4 p-3 bg-gray-50 rounded text-xs text-gray-600">
              <p className="font-mono break-all">{error.message}</p>
            </div>
          )}

          <div className="flex gap-3">
            {onReset && (
              <Button
                color="primary"
                onClick={onReset}
                startContent={<RefreshCw className="w-4 h-4" />}
                className="flex-1"
              >
                Try Again
              </Button>
            )}
            <Button
              variant="bordered"
              onClick={() => window.location.reload()}
              startContent={<RefreshCw className="w-4 h-4" />}
              className="flex-1"
            >
              Refresh Page
            </Button>
          </div>

          <Button
            variant="light"
            onClick={() => (window.location.href = '/')}
            startContent={<Home className="w-4 h-4" />}
            className="w-full mt-3"
          >
            Go to Dashboard
          </Button>
        </div>
      </div>
    </div>
  );
}

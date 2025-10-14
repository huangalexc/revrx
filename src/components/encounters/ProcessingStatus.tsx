'use client';

import { useEffect, useState } from 'react';
import { Clock, CheckCircle, AlertCircle, RefreshCw, FileText } from 'lucide-react';

interface ProcessingStep {
  id: string;
  label: string;
  description: string;
  status: 'pending' | 'processing' | 'complete' | 'error';
  timestamp?: string;
}

interface ProcessingStatusProps {
  encounterId: string;
  currentStatus: 'pending' | 'processing' | 'complete' | 'failed';
  processingTime?: number;
  onStatusChange?: (status: string) => void;
}

export default function ProcessingStatus({
  encounterId,
  currentStatus,
  processingTime,
  onStatusChange,
}: ProcessingStatusProps) {
  const [steps, setSteps] = useState<ProcessingStep[]>([
    {
      id: 'upload',
      label: 'File Upload',
      description: 'Clinical note received and validated',
      status: 'complete',
    },
    {
      id: 'extraction',
      label: 'Text Extraction',
      description: 'Extracting text from uploaded file',
      status: currentStatus === 'pending' ? 'pending' : 'complete',
    },
    {
      id: 'phi_detection',
      label: 'PHI Detection',
      description: 'Identifying protected health information',
      status: currentStatus === 'pending' ? 'pending' : currentStatus === 'processing' ? 'processing' : 'complete',
    },
    {
      id: 'ai_analysis',
      label: 'AI Analysis',
      description: 'Analyzing codes with ChatGPT',
      status: currentStatus === 'pending' || currentStatus === 'processing' ? 'pending' : currentStatus === 'complete' ? 'complete' : 'error',
    },
    {
      id: 'report_generation',
      label: 'Report Generation',
      description: 'Compiling coding recommendations',
      status: currentStatus === 'complete' ? 'complete' : currentStatus === 'failed' ? 'error' : 'pending',
    },
  ]);

  useEffect(() => {
    // Update steps based on current status
    const statusMap: Record<string, Partial<Record<string, 'pending' | 'processing' | 'complete' | 'error'>>> = {
      pending: {
        upload: 'complete',
        extraction: 'processing',
      },
      processing: {
        upload: 'complete',
        extraction: 'complete',
        phi_detection: 'complete',
        ai_analysis: 'processing',
      },
      complete: {
        upload: 'complete',
        extraction: 'complete',
        phi_detection: 'complete',
        ai_analysis: 'complete',
        report_generation: 'complete',
      },
      failed: {
        upload: 'complete',
        extraction: 'complete',
        phi_detection: 'error',
        ai_analysis: 'error',
        report_generation: 'error',
      },
    };

    const newStatuses = statusMap[currentStatus] || {};
    setSteps((prevSteps) =>
      prevSteps.map((step) => ({
        ...step,
        status: newStatuses[step.id] || step.status,
      }))
    );
  }, [currentStatus]);

  const getStepIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <div className="w-8 h-8 rounded-full border-2 border-gray-300 bg-white" />;
      case 'processing':
        return (
          <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
            <RefreshCw className="w-4 h-4 text-blue-600 animate-spin" />
          </div>
        );
      case 'complete':
        return (
          <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
            <CheckCircle className="w-5 h-5 text-green-600" />
          </div>
        );
      case 'error':
        return (
          <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center">
            <AlertCircle className="w-5 h-5 text-red-600" />
          </div>
        );
      default:
        return <div className="w-8 h-8 rounded-full border-2 border-gray-300 bg-white" />;
    }
  };

  const getOverallStatusDisplay = () => {
    if (currentStatus === 'complete') {
      return (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
          <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0" />
          <div>
            <h3 className="text-sm font-semibold text-green-900">Processing Complete</h3>
            <p className="text-sm text-green-700">
              Your report is ready to view
              {processingTime && ` (Processed in ${processingTime.toFixed(1)}s)`}
            </p>
          </div>
        </div>
      );
    }

    if (currentStatus === 'failed') {
      return (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0" />
          <div>
            <h3 className="text-sm font-semibold text-red-900">Processing Failed</h3>
            <p className="text-sm text-red-700">
              An error occurred during processing. Please try again or contact support.
            </p>
          </div>
        </div>
      );
    }

    if (currentStatus === 'processing') {
      return (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center gap-3">
          <RefreshCw className="w-6 h-6 text-blue-600 animate-spin flex-shrink-0" />
          <div>
            <h3 className="text-sm font-semibold text-blue-900">Processing In Progress</h3>
            <p className="text-sm text-blue-700">
              Analyzing your clinical note. This typically takes 15-30 seconds.
            </p>
          </div>
        </div>
      );
    }

    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 flex items-center gap-3">
        <Clock className="w-6 h-6 text-gray-600 flex-shrink-0" />
        <div>
          <h3 className="text-sm font-semibold text-gray-900">Pending Processing</h3>
          <p className="text-sm text-gray-700">
            Your encounter is queued for processing.
          </p>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Overall Status */}
      {getOverallStatusDisplay()}

      {/* Processing Steps */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-6">Processing Steps</h3>
        <div className="space-y-6">
          {steps.map((step, index) => (
            <div key={step.id} className="relative">
              {/* Connector Line */}
              {index < steps.length - 1 && (
                <div
                  className={`absolute left-4 top-8 w-0.5 h-10 ${
                    step.status === 'complete'
                      ? 'bg-green-500'
                      : step.status === 'error'
                      ? 'bg-red-500'
                      : 'bg-gray-300'
                  }`}
                />
              )}

              <div className="flex items-start gap-4">
                {getStepIcon(step.status)}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h4
                      className={`text-sm font-medium ${
                        step.status === 'complete'
                          ? 'text-green-900'
                          : step.status === 'processing'
                          ? 'text-blue-900'
                          : step.status === 'error'
                          ? 'text-red-900'
                          : 'text-gray-500'
                      }`}
                    >
                      {step.label}
                    </h4>
                    {step.timestamp && (
                      <span className="text-xs text-gray-500">{step.timestamp}</span>
                    )}
                  </div>
                  <p
                    className={`text-sm ${
                      step.status === 'pending' ? 'text-gray-500' : 'text-gray-700'
                    }`}
                  >
                    {step.description}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Performance Metrics */}
      {processingTime && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Total Processing Time</span>
            <span className="text-lg font-semibold text-gray-900">
              {processingTime.toFixed(2)}s
            </span>
          </div>
          <div className="mt-2 h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full ${
                processingTime < 15
                  ? 'bg-green-500'
                  : processingTime < 30
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
              }`}
              style={{ width: `${Math.min((processingTime / 30) * 100, 100)}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Target: &lt;30s
          </p>
        </div>
      )}
    </div>
  );
}

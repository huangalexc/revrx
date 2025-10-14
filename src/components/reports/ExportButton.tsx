'use client';

import { useState } from 'react';
import { Download, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import apiClient from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';

type ExportFormat = 'pdf' | 'csv' | 'json' | 'yaml';

interface ExportButtonProps {
  encounterId: string;
  className?: string;
}

export default function ExportButton({ encounterId, className = '' }: ExportButtonProps) {
  const [isExporting, setIsExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState<ExportFormat>('pdf');
  const [notification, setNotification] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);

  const formatLabels: Record<ExportFormat, string> = {
    pdf: 'PDF Report',
    csv: 'CSV Data',
    json: 'JSON Data',
    yaml: 'YAML Data',
  };

  const formatDescriptions: Record<ExportFormat, string> = {
    pdf: 'Complete report with all analysis features',
    csv: 'Structured data for Excel/Google Sheets',
    json: 'Raw data for API integration',
    yaml: 'Human-readable structured data',
  };

  const handleExport = async () => {
    setIsExporting(true);
    setNotification(null);

    try {
      const response = await apiClient.get(
        API_ENDPOINTS.REPORTS.EXPORT(encounterId, exportFormat),
        { responseType: 'blob' }
      );

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `report_${encounterId}_${Date.now()}.${exportFormat}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      // Show success notification
      setNotification({
        type: 'success',
        message: `${formatLabels[exportFormat]} downloaded successfully!`,
      });

      // Clear notification after 3 seconds
      setTimeout(() => setNotification(null), 3000);
    } catch (err: any) {
      console.error('Export failed:', err);
      const errorMessage =
        err.response?.data?.detail || 'Failed to export report. Please try again.';

      setNotification({
        type: 'error',
        message: errorMessage,
      });

      // Clear error after 5 seconds
      setTimeout(() => setNotification(null), 5000);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className={`relative ${className}`}>
      {/* Export Controls */}
      <div className="flex items-center gap-3">
        {/* Format Selection Dropdown */}
        <select
          value={exportFormat}
          onChange={(e) => setExportFormat(e.target.value as ExportFormat)}
          disabled={isExporting}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Select export format"
        >
          {(Object.keys(formatLabels) as ExportFormat[]).map((format) => (
            <option key={format} value={format}>
              {formatLabels[format]}
            </option>
          ))}
        </select>

        {/* Export Button */}
        <button
          onClick={handleExport}
          disabled={isExporting}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          aria-label={`Export report as ${formatLabels[exportFormat]}`}
        >
          {isExporting ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Exporting...
            </>
          ) : (
            <>
              <Download className="w-5 h-5" />
              Export
            </>
          )}
        </button>
      </div>

      {/* Format Description */}
      <p className="mt-2 text-xs text-gray-500">
        {formatDescriptions[exportFormat]}
      </p>

      {/* Notification Toast */}
      {notification && (
        <div
          className={`fixed top-4 right-4 z-50 max-w-md p-4 rounded-lg shadow-lg border animate-slide-in ${
            notification.type === 'success'
              ? 'bg-green-50 border-green-200 text-green-800'
              : 'bg-red-50 border-red-200 text-red-800'
          }`}
          role="alert"
        >
          <div className="flex items-start gap-3">
            {notification.type === 'success' ? (
              <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            )}
            <div>
              <p className="font-medium">
                {notification.type === 'success' ? 'Success!' : 'Export Failed'}
              </p>
              <p className="text-sm mt-1">{notification.message}</p>
            </div>
            <button
              onClick={() => setNotification(null)}
              className="ml-auto text-gray-400 hover:text-gray-600"
              aria-label="Dismiss notification"
            >
              ×
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

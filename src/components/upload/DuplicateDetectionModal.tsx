'use client';

import { AlertCircle, Calendar, File, HardDrive } from 'lucide-react';

interface DuplicateInfo {
  file_id: string;
  encounter_id: string;
  original_filename: string;
  upload_timestamp: string;
  file_size: number;
}

interface DuplicateDetectionModalProps {
  isOpen: boolean;
  duplicateInfo: DuplicateInfo;
  currentFilename: string;
  onSkip: () => void;
  onReplace: () => void;
  onProcessAsNew: () => void;
  onClose: () => void;
}

export default function DuplicateDetectionModal({
  isOpen,
  duplicateInfo,
  currentFilename,
  onSkip,
  onReplace,
  onProcessAsNew,
  onClose,
}: DuplicateDetectionModalProps) {
  if (!isOpen) return null;

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center flex-shrink-0">
              <AlertCircle className="w-6 h-6 text-yellow-600" />
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Duplicate File Detected
              </h2>
              <p className="text-gray-600">
                This file appears to have been previously uploaded. Choose how to proceed.
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Current File Info */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Current File</h3>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <File className="w-5 h-5 text-blue-600" />
                <span className="text-sm font-medium text-gray-900">{currentFilename}</span>
              </div>
            </div>
          </div>

          {/* Previous Upload Info */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Previously Uploaded As</h3>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-3">
                <File className="w-5 h-5 text-gray-600" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">
                    {duplicateInfo.original_filename}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 text-sm text-gray-600">
                <Calendar className="w-4 h-4" />
                <span>Uploaded on {formatDate(duplicateInfo.upload_timestamp)}</span>
              </div>
              <div className="flex items-center gap-3 text-sm text-gray-600">
                <HardDrive className="w-4 h-4" />
                <span>{formatFileSize(duplicateInfo.file_size)}</span>
              </div>
            </div>
          </div>

          {/* Options */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Choose an Action</h3>
            <div className="space-y-3">
              {/* Skip */}
              <button
                onClick={onSkip}
                className="w-full text-left border border-gray-300 rounded-lg p-4 hover:bg-gray-50 hover:border-gray-400 transition-colors"
              >
                <div className="font-semibold text-gray-900 mb-1">Skip</div>
                <div className="text-sm text-gray-600">
                  Don't upload this file. Keep the existing upload and move on.
                </div>
              </button>

              {/* Replace */}
              <button
                onClick={onReplace}
                className="w-full text-left border border-gray-300 rounded-lg p-4 hover:bg-gray-50 hover:border-gray-400 transition-colors"
              >
                <div className="font-semibold text-gray-900 mb-1">Replace</div>
                <div className="text-sm text-gray-600">
                  Delete the previous upload and replace it with this new file. The encounter ID will remain the same.
                </div>
              </button>

              {/* Process as New */}
              <button
                onClick={onProcessAsNew}
                className="w-full text-left border border-blue-300 bg-blue-50 rounded-lg p-4 hover:bg-blue-100 hover:border-blue-400 transition-colors"
              >
                <div className="font-semibold text-gray-900 mb-1">Process as New</div>
                <div className="text-sm text-gray-600">
                  Upload this file as a separate encounter with a new ID. Useful if the file content has been updated.
                </div>
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-white transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

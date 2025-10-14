'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { v4 as uuidv4 } from 'uuid';
import FileUpload from '@/components/upload/FileUpload';
import DuplicateDetectionModal from '@/components/upload/DuplicateDetectionModal';
import { useBulkUploadStore } from '@/store/useBulkUploadStore';
import apiClient from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';
import { Upload, CheckCircle, AlertCircle, Loader, FileText, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function BulkUploadPage() {
  const router = useRouter();
  const {
    files,
    addFiles,
    removeFile,
    clearFiles,
    updateFileStatus,
    setFileProgress,
    setFileEncounterId,
    setFileDuplicate,
    setFileDuplicateHandling,
    startBatch,
    completeBatch,
    isUploading,
    getCompletedCount,
    getErrorCount,
    getPendingCount,
  } = useBulkUploadStore();

  const [error, setError] = useState<string | null>(null);
  const [showDuplicateModal, setShowDuplicateModal] = useState(false);
  const [currentDuplicateIndex, setCurrentDuplicateIndex] = useState<number | null>(null);
  const [batchId] = useState(() => uuidv4());

  const handleFilesSelected = (selectedFiles: File | File[]) => {
    const fileArray = Array.isArray(selectedFiles) ? selectedFiles : [selectedFiles];
    addFiles(fileArray);
  };

  const checkForDuplicates = async (file: File, index: number): Promise<boolean> => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await apiClient.post(API_ENDPOINTS.ENCOUNTERS.CHECK_DUPLICATE, formData);

      if (response.data.is_duplicate) {
        setFileDuplicate(index, response.data.duplicate_info);
        setCurrentDuplicateIndex(index);
        setShowDuplicateModal(true);
        return true;
      }

      return false;
    } catch (err) {
      console.error('Error checking duplicate:', err);
      return false;
    }
  };

  const uploadFile = async (file: File, index: number, duplicateHandling?: string) => {
    try {
      updateFileStatus(index, 'uploading');
      setFileProgress(index, 0);

      const formData = new FormData();
      formData.append('file', file);
      formData.append('batch_id', batchId);

      if (duplicateHandling) {
        formData.append('duplicate_handling', duplicateHandling);
      }

      const response = await apiClient.post(
        API_ENDPOINTS.ENCOUNTERS.UPLOAD_NOTE,
        formData,
        {
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const percentage = Math.round((progressEvent.loaded * 100) / progressEvent.total);
              setFileProgress(index, percentage);
            }
          },
        }
      );

      setFileEncounterId(index, response.data.encounter_id);
      updateFileStatus(index, 'processing');

      // File will be processed in background, mark as complete for now
      setTimeout(() => {
        updateFileStatus(index, 'complete');
      }, 1000);

    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Upload failed';
      updateFileStatus(index, 'error', { error: errorMessage });
    }
  };

  const handleBulkUpload = async () => {
    if (files.length === 0) {
      setError('Please select at least one file');
      return;
    }

    setError(null);
    startBatch(batchId);

    for (let i = 0; i < files.length; i++) {
      const fileState = files[i];

      // Skip files that are already complete or have errors
      if (fileState.status === 'complete' || fileState.status === 'error') {
        continue;
      }

      // Skip files marked to skip
      if (fileState.duplicateHandling === 'SKIP') {
        updateFileStatus(i, 'pending', { error: 'Skipped (duplicate)' });
        continue;
      }

      // Check for duplicates
      const isDuplicate = await checkForDuplicates(fileState.file, i);

      if (isDuplicate) {
        // Wait for user decision
        return;
      }

      // Upload the file
      await uploadFile(fileState.file, i, fileState.duplicateHandling);
    }

    completeBatch();
  };

  const handleDuplicateDecision = async (decision: 'SKIP' | 'REPLACE' | 'PROCESS_AS_NEW') => {
    if (currentDuplicateIndex === null) return;

    setFileDuplicateHandling(currentDuplicateIndex, decision);
    setShowDuplicateModal(false);

    if (decision !== 'SKIP') {
      // Continue uploading this file
      await uploadFile(files[currentDuplicateIndex].file, currentDuplicateIndex, decision);
    }

    // Continue with next files
    setCurrentDuplicateIndex(null);

    // Resume bulk upload for remaining files
    for (let i = currentDuplicateIndex + 1; i < files.length; i++) {
      const fileState = files[i];
      if (fileState.status === 'pending' && !fileState.duplicateHandling) {
        const isDuplicate = await checkForDuplicates(fileState.file, i);
        if (isDuplicate) return;
        await uploadFile(fileState.file, i);
      }
    }

    completeBatch();
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'complete':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-600" />;
      case 'uploading':
      case 'processing':
        return <Loader className="w-5 h-5 text-blue-600 animate-spin" />;
      case 'duplicate':
        return <AlertCircle className="w-5 h-5 text-yellow-600" />;
      default:
        return <FileText className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending':
        return 'Pending';
      case 'uploading':
        return 'Uploading...';
      case 'processing':
        return 'Processing...';
      case 'complete':
        return 'Complete';
      case 'error':
        return 'Failed';
      case 'duplicate':
        return 'Duplicate Detected';
      default:
        return status;
    }
  };

  const canStartUpload = files.length > 0 && !isUploading;
  const completedCount = getCompletedCount();
  const errorCount = getErrorCount();
  const pendingCount = getPendingCount();
  const allComplete = files.length > 0 && completedCount === files.length;

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <Link
          href="/encounters"
          className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Encounters
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Bulk Upload</h1>
        <p className="text-gray-600 mt-2">
          Upload multiple clinical notes at once for batch processing
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* File Upload Section */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <FileUpload
          onFileSelect={handleFilesSelected}
          acceptedTypes={['.txt', '.pdf', '.docx']}
          maxSizeMB={5}
          label="Clinical Notes"
          description="Select multiple files (TXT, PDF, or DOCX, up to 5MB each)"
          multiple={true}
        />
      </div>

      {/* Batch Statistics */}
      {files.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Batch Summary</h2>
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{files.length}</div>
              <div className="text-sm text-gray-600">Total Files</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{completedCount}</div>
              <div className="text-sm text-gray-600">Completed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{pendingCount}</div>
              <div className="text-sm text-gray-600">Pending</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{errorCount}</div>
              <div className="text-sm text-gray-600">Failed</div>
            </div>
          </div>
          {isUploading && (
            <div className="mt-4">
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>Progress</span>
                <span>{Math.round((completedCount / files.length) * 100)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${(completedCount / files.length) * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* File List */}
      {files.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Files</h2>
          <div className="space-y-3">
            {files.map((fileState, index) => (
              <div
                key={index}
                className="border border-gray-200 rounded-lg p-4 bg-gray-50"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    {getStatusIcon(fileState.status)}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {fileState.file.name}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-gray-500">
                          {getStatusText(fileState.status)}
                        </span>
                        {fileState.progress > 0 && fileState.progress < 100 && (
                          <span className="text-xs text-blue-600">
                            {fileState.progress}%
                          </span>
                        )}
                        {fileState.error && (
                          <span className="text-xs text-red-600">
                            {fileState.error}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  {fileState.status === 'pending' && !isUploading && (
                    <button
                      onClick={() => removeFile(index)}
                      className="ml-4 px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded transition-colors"
                    >
                      Remove
                    </button>
                  )}
                  {fileState.encounterId && fileState.status === 'complete' && (
                    <Link
                      href={`/reports/${fileState.encounterId}`}
                      className="ml-4 px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded transition-colors"
                    >
                      View Report
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-end gap-4">
        <button
          onClick={clearFiles}
          disabled={isUploading}
          className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Clear All
        </button>
        {!allComplete ? (
          <button
            onClick={handleBulkUpload}
            disabled={!canStartUpload}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Upload className="w-5 h-5" />
            {isUploading ? 'Uploading...' : 'Start Upload'}
          </button>
        ) : (
          <Link
            href="/encounters"
            className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2"
          >
            <CheckCircle className="w-5 h-5" />
            View All Encounters
          </Link>
        )}
      </div>

      {/* Duplicate Detection Modal */}
      {showDuplicateModal && currentDuplicateIndex !== null && files[currentDuplicateIndex].duplicateInfo && (
        <DuplicateDetectionModal
          isOpen={showDuplicateModal}
          duplicateInfo={files[currentDuplicateIndex].duplicateInfo!}
          currentFilename={files[currentDuplicateIndex].file.name}
          onSkip={() => handleDuplicateDecision('SKIP')}
          onReplace={() => handleDuplicateDecision('REPLACE')}
          onProcessAsNew={() => handleDuplicateDecision('PROCESS_AS_NEW')}
          onClose={() => setShowDuplicateModal(false)}
        />
      )}
    </div>
  );
}

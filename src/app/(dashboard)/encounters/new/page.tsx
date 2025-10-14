'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import FileUpload from '@/components/upload/FileUpload';
import apiClient from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';
import { Upload, FileText, Clock, CheckCircle } from 'lucide-react';

interface UploadStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'complete' | 'error';
}

export default function EncountersPage() {
  const router = useRouter();
  const [clinicalNote, setClinicalNote] = useState<File | null>(null);
  const [billingCodes, setBillingCodes] = useState<File | null>(null);

  const handleClinicalNoteSelect = (file: File) => {
    console.log('File selected:', file);
    console.log('File type:', typeof file);
    console.log('Is File?', file instanceof File);
    console.log('File name:', file.name);
    console.log('File size:', file.size);
    setClinicalNote(file);
  };
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [encounterId, setEncounterId] = useState<string | null>(null);
  const [uploadSteps, setUploadSteps] = useState<UploadStep[]>([
    { id: 'note', label: 'Upload clinical note', status: 'pending' },
    { id: 'extract', label: 'Extract text', status: 'pending' },
    { id: 'codes', label: 'Upload billing codes (optional)', status: 'pending' },
    { id: 'complete', label: 'Ready for processing', status: 'pending' },
  ]);

  const updateStepStatus = (
    stepId: string,
    status: 'pending' | 'active' | 'complete' | 'error'
  ) => {
    setUploadSteps((steps) =>
      steps.map((step) => (step.id === stepId ? { ...step, status } : step))
    );
  };

  const handleClinicalNoteUpload = async () => {
    if (!clinicalNote) return;

    setIsUploading(true);
    setError(null);

    try {
      // Step 1: Upload clinical note
      updateStepStatus('note', 'active');

      console.log('Before FormData - clinicalNote:', clinicalNote);
      console.log('Before FormData - clinicalNote instanceof File:', clinicalNote instanceof File);
      console.log('Before FormData - clinicalNote.name:', clinicalNote.name);

      const formData = new FormData();
      formData.append('file', clinicalNote);

      console.log('After FormData - formData has file:', formData.has('file'));
      console.log('After FormData - formData.get(file):', formData.get('file'));

      // Get token from localStorage
      const token = localStorage.getItem('auth_token');
      console.log('Upload - Token available:', !!token);
      console.log('Upload - Token preview:', token ? token.substring(0, 20) + '...' : 'NULL');
      console.log('Upload - All localStorage keys:', Object.keys(localStorage));

      const response = await apiClient.post(
        API_ENDPOINTS.ENCOUNTERS.UPLOAD_NOTE,
        formData,
        {
          headers: token ? {
            'Authorization': `Bearer ${token}`
          } : {}
        }
      );

      const { encounter_id } = response.data;
      setEncounterId(encounter_id);

      updateStepStatus('note', 'complete');
      updateStepStatus('extract', 'complete');

      // If billing codes uploaded, proceed to step 3
      if (billingCodes) {
        await handleBillingCodesUpload(encounter_id);
      } else {
        updateStepStatus('codes', 'complete');
      }

      updateStepStatus('complete', 'complete');

      // Redirect to encounter detail after 2 seconds
      setTimeout(() => {
        router.push(`/reports/${encounter_id}`);
      }, 2000);
    } catch (err: any) {
      updateStepStatus('note', 'error');
      const errorDetail = err.response?.data?.detail;
      const errorMessage = Array.isArray(errorDetail)
        ? errorDetail.map((e: any) => e.msg).join(', ')
        : typeof errorDetail === 'string'
        ? errorDetail
        : 'Failed to upload clinical note';
      setError(errorMessage);
    } finally {
      setIsUploading(false);
    }
  };

  const handleBillingCodesUpload = async (encounter_id: string) => {
    if (!billingCodes) return;

    try {
      updateStepStatus('codes', 'active');

      const formData = new FormData();
      formData.append('file', billingCodes);

      await apiClient.post(
        API_ENDPOINTS.ENCOUNTERS.UPLOAD_CODES(encounter_id),
        formData
      );

      updateStepStatus('codes', 'complete');
    } catch (err: any) {
      updateStepStatus('codes', 'error');
      // Don't fail entire upload if billing codes fail
      console.error('Failed to upload billing codes:', err);
    }
  };

  const canSubmit = clinicalNote !== null && !isUploading;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">New Encounter</h1>
        <p className="text-gray-600 mt-2">
          Upload clinical notes and billing codes for post-facto coding review
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      <div className="space-y-6">
        {/* Clinical Note Upload */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Clinical Note
              </h2>
              <p className="text-sm text-gray-600">Required</p>
            </div>
          </div>
          <FileUpload
            onFileSelect={handleClinicalNoteSelect}
            acceptedTypes={['.txt', '.pdf', '.docx']}
            maxSizeMB={5}
            label=""
            description="TXT, PDF, or DOCX up to 5MB"
          />
        </div>

        {/* Billing Codes Upload */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Billing Codes
              </h2>
              <p className="text-sm text-gray-600">
                Optional - CSV or JSON format
              </p>
            </div>
          </div>
          <FileUpload
            onFileSelect={setBillingCodes}
            acceptedTypes={['.csv', '.json']}
            maxSizeMB={1}
            label=""
            description="CSV or JSON up to 1MB"
          />
        </div>

        {/* Upload Progress */}
        {isUploading && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Upload Progress
            </h3>
            <div className="space-y-3">
              {uploadSteps.map((step) => (
                <div key={step.id} className="flex items-center gap-3">
                  {step.status === 'pending' && (
                    <div className="w-6 h-6 rounded-full border-2 border-gray-300" />
                  )}
                  {step.status === 'active' && (
                    <div className="w-6 h-6">
                      <Clock className="w-6 h-6 text-blue-600 animate-spin" />
                    </div>
                  )}
                  {step.status === 'complete' && (
                    <CheckCircle className="w-6 h-6 text-green-600" />
                  )}
                  {step.status === 'error' && (
                    <div className="w-6 h-6 rounded-full bg-red-600" />
                  )}
                  <span
                    className={`text-sm ${
                      step.status === 'complete'
                        ? 'text-green-600 font-medium'
                        : step.status === 'active'
                        ? 'text-blue-600 font-medium'
                        : step.status === 'error'
                        ? 'text-red-600 font-medium'
                        : 'text-gray-600'
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-end gap-4">
          <button
            onClick={() => router.back()}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            disabled={isUploading}
          >
            Cancel
          </button>
          <button
            onClick={handleClinicalNoteUpload}
            disabled={!canSubmit}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Upload className="w-5 h-5" />
            {isUploading ? 'Uploading...' : 'Upload & Process'}
          </button>
        </div>
      </div>
    </div>
  );
}

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import DualInputForm from '@/components/forms/DualInputForm';
import FileUpload from '@/components/upload/FileUpload';
import apiClient from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';
import { FileText, Clock, CheckCircle } from 'lucide-react';
import type { EncounterInputFormData } from '@/lib/schemas/encounter-input';

interface UploadStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'complete' | 'error';
}

export default function EncountersPage() {
  const router = useRouter();
  const [billingCodes, setBillingCodes] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadSteps, setUploadSteps] = useState<UploadStep[]>([
    { id: 'note', label: 'Process clinical note', status: 'pending' },
    { id: 'extract', label: 'Extract/Validate text', status: 'pending' },
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

  const handleEncounterSubmit = async (data: EncounterInputFormData) => {
    setIsUploading(true);
    setError(null);

    try {
      // Step 1: Upload clinical note (text or file)
      updateStepStatus('note', 'active');

      const formData = new FormData();

      if (data.inputMethod === 'text' && data.textContent) {
        // Text input
        formData.append('text_content', data.textContent);
      } else if (data.inputMethod === 'file' && data.file) {
        // File input
        const file = Array.isArray(data.file) ? data.file[0] : data.file;
        formData.append('file', file);
      }

      // Get token from localStorage
      const token = localStorage.getItem('auth_token');

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
    } catch (err) {
      updateStepStatus('note', 'error');
      const error = err as { response?: { data?: { detail?: string | Array<{ msg: string }> } } };
      const errorDetail = error.response?.data?.detail;
      const errorMessage = Array.isArray(errorDetail)
        ? errorDetail.map((e) => e.msg).join(', ')
        : typeof errorDetail === 'string'
        ? errorDetail
        : 'Failed to process clinical note';
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
    } catch (err) {
      updateStepStatus('codes', 'error');
      // Don't fail entire upload if billing codes fail
      console.error('Failed to upload billing codes:', err);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">New Encounter</h1>
        <p className="text-gray-600 mt-2">
          Paste clinical note text or upload a file for post-facto coding review
        </p>
      </div>

      <div className="space-y-6">
        {/* Clinical Note Input - Text or File */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <FileText className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Clinical Note
              </h2>
              <p className="text-sm text-gray-600">Required - Text or File</p>
            </div>
          </div>
          <DualInputForm
            onSubmit={handleEncounterSubmit}
            defaultMethod="text"
            isSubmitting={isUploading}
            error={error}
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
              Processing
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
      </div>
    </div>
  );
}

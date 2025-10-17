'use client';

import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  Tabs,
  Tab,
  Card,
  CardBody,
  Button,
  Progress,
} from '@heroui/react';
import { Upload, FileText } from 'lucide-react';
import {
  encounterInputSchema,
  type EncounterInputFormData,
  MAX_TEXT_LENGTH,
} from '@/lib/schemas/encounter-input';
import FileUpload from '@/components/upload/FileUpload';

interface DualInputFormProps {
  onSubmit: (data: EncounterInputFormData) => Promise<void> | void;
  defaultMethod?: 'text' | 'file';
  isSubmitting?: boolean;
  error?: string | null;
}

export default function DualInputForm({
  onSubmit,
  defaultMethod = 'text',
  isSubmitting = false,
  error = null,
}: DualInputFormProps) {
  const [inputMethod, setInputMethod] = useState<'text' | 'file'>(defaultMethod);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [showSwitchWarning, setShowSwitchWarning] = useState(false);

  const {
    control,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<EncounterInputFormData>({
    resolver: zodResolver(encounterInputSchema),
    defaultValues: {
      inputMethod: defaultMethod,
      textContent: '',
    },
  });

  const textContent = watch('textContent');
  const characterCount = textContent?.length || 0;
  const progressPercentage = (characterCount / MAX_TEXT_LENGTH) * 100;

  // Handle tab switching with warning if data exists
  const handleTabChange = (key: string | number) => {
    const newMethod = key as 'text' | 'file';

    // Check if switching away from populated data
    const hasText = textContent && textContent.trim().length > 0;
    const hasFile = selectedFile !== null;

    if ((inputMethod === 'text' && hasText && newMethod === 'file') ||
        (inputMethod === 'file' && hasFile && newMethod === 'text')) {
      setShowSwitchWarning(true);
      // Could implement a modal confirmation here
      // For now, allow the switch but clear the data
    }

    setInputMethod(newMethod);
    setValue('inputMethod', newMethod);

    // Clear opposite field when switching
    if (newMethod === 'text') {
      setSelectedFile(null);
      setValue('file', undefined);
    } else {
      setValue('textContent', '');
    }
  };

  // Handle file selection
  const handleFileSelect = (file: File | File[]) => {
    const selectedFileObj = Array.isArray(file) ? file[0] : file;
    setSelectedFile(selectedFileObj);
    setValue('file', [selectedFileObj]);
  };

  // Auto-focus text area when in text mode
  useEffect(() => {
    if (inputMethod === 'text') {
      const textarea = document.querySelector('textarea[name="textContent"]') as HTMLTextAreaElement;
      if (textarea) {
        textarea.focus();
      }
    }
  }, [inputMethod]);

  const handleFormSubmit = async (data: EncounterInputFormData) => {
    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      {/* Error Message */}
      {error && (
        <Card className="border-2 border-danger">
          <CardBody>
            <p className="text-sm text-danger">{error}</p>
          </CardBody>
        </Card>
      )}

      {/* Input Method Tabs */}
      <Tabs
        selectedKey={inputMethod}
        onSelectionChange={handleTabChange}
        variant="underlined"
        color="primary"
        classNames={{
          tabList: 'gap-6',
          cursor: 'w-full',
          tab: 'max-w-fit px-4 h-12',
        }}
      >
        <Tab
          key="text"
          title={
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              <span>Paste Text</span>
            </div>
          }
        >
          <Card className="mt-4">
            <CardBody className="p-6">
              {/* Textarea Section */}
              <div className="space-y-2">
                <label htmlFor="textContent" className="block text-sm font-medium text-gray-700">
                  Clinical Note Text
                </label>
                <Controller
                  name="textContent"
                  control={control}
                  render={({ field }) => (
                    <textarea
                      {...field}
                      id="textContent"
                      name="textContent"
                      placeholder="Paste your clinical note here..."
                      rows={15}
                      className={`
                        w-full px-3 py-2
                        border-2 rounded-lg
                        resize-y
                        font-sans text-base
                        placeholder:text-gray-400
                        focus:outline-none focus:ring-2 focus:ring-offset-0
                        transition-colors
                        ${errors.textContent
                          ? 'border-red-500 focus:border-red-500 focus:ring-red-200'
                          : 'border-gray-300 focus:border-blue-500 focus:ring-blue-200'
                        }
                      `}
                    />
                  )}
                />
                {errors.textContent && (
                  <p className="text-sm text-red-600">{errors.textContent.message}</p>
                )}
              </div>
            </CardBody>
          </Card>

          {/* Character Counter - Completely separate card */}
          <Card className="mt-4">
            <CardBody className="p-4">
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Character count</span>
                  <span
                    className={`text-sm font-medium ${
                      characterCount > MAX_TEXT_LENGTH
                        ? 'text-red-600'
                        : 'text-gray-900'
                    }`}
                  >
                    {characterCount.toLocaleString()} / {MAX_TEXT_LENGTH.toLocaleString()}
                  </span>
                </div>
                <Progress
                  value={Math.min(progressPercentage, 100)}
                  color={characterCount > MAX_TEXT_LENGTH ? 'danger' : 'primary'}
                  size="sm"
                />
                <p className="text-xs text-gray-500">
                  Maximum {MAX_TEXT_LENGTH.toLocaleString()} characters
                </p>
              </div>
            </CardBody>
          </Card>
        </Tab>

        <Tab
          key="file"
          title={
            <div className="flex items-center gap-2">
              <Upload className="w-4 h-4" />
              <span>Upload File</span>
            </div>
          }
        >
          <Card className="mt-4">
            <CardBody className="p-6">
              <FileUpload
                onFileSelect={handleFileSelect}
                acceptedTypes={['.txt', '.pdf', '.docx']}
                maxSizeMB={5}
                label="Clinical Note File"
                description="TXT, PDF, or DOCX up to 5MB"
                multiple={false}
              />
              {errors.file && (
                <p className="text-sm text-danger mt-2">{errors.file.message as string}</p>
              )}
            </CardBody>
          </Card>
        </Tab>
      </Tabs>

      {/* Submit Button */}
      <div className="flex justify-end gap-4">
        <Button
          type="submit"
          color="primary"
          size="lg"
          isLoading={isSubmitting}
          isDisabled={isSubmitting}
          startContent={!isSubmitting && <Upload className="w-5 h-5" />}
          className="font-medium"
        >
          {isSubmitting ? 'Processing...' : 'Submit Encounter'}
        </Button>
      </div>

      {/* Switch Warning (optional visual feedback) */}
      {showSwitchWarning && (
        <p className="text-xs text-warning">
          Note: Switching input methods will clear your current input
        </p>
      )}
    </form>
  );
}

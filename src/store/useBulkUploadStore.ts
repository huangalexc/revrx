import { create } from 'zustand';

export type FileStatus = 'pending' | 'uploading' | 'processing' | 'complete' | 'error' | 'duplicate';

export interface FileUploadState {
  file: File;
  encounterId?: string;
  status: FileStatus;
  progress: number;
  error?: string;
  isDuplicate?: boolean;
  duplicateInfo?: {
    file_id: string;
    encounter_id: string;
    original_filename: string;
    upload_timestamp: string;
    file_size: number;
  };
  duplicateHandling?: 'SKIP' | 'REPLACE' | 'PROCESS_AS_NEW';
}

interface BatchMetadata {
  batchId: string;
  totalFiles: number;
  completedCount: number;
  startedAt: Date;
  completedAt?: Date;
}

interface BulkUploadStore {
  // State
  files: FileUploadState[];
  batchMetadata: BatchMetadata | null;
  isUploading: boolean;

  // Actions
  addFiles: (files: File[]) => void;
  removeFile: (index: number) => void;
  clearFiles: () => void;
  updateFileStatus: (index: number, status: FileStatus, data?: Partial<FileUploadState>) => void;
  setFileProgress: (index: number, progress: number) => void;
  setFileEncounterId: (index: number, encounterId: string) => void;
  setFileDuplicate: (index: number, duplicateInfo: FileUploadState['duplicateInfo']) => void;
  setFileDuplicateHandling: (index: number, handling: 'SKIP' | 'REPLACE' | 'PROCESS_AS_NEW') => void;
  startBatch: (batchId: string) => void;
  completeBatch: () => void;
  setIsUploading: (isUploading: boolean) => void;

  // Getters
  getCompletedCount: () => number;
  getPendingCount: () => number;
  getErrorCount: () => number;
  getDuplicateCount: () => number;
}

export const useBulkUploadStore = create<BulkUploadStore>((set, get) => ({
  files: [],
  batchMetadata: null,
  isUploading: false,

  addFiles: (newFiles) =>
    set((state) => ({
      files: [
        ...state.files,
        ...newFiles.map((file) => ({
          file,
          status: 'pending' as FileStatus,
          progress: 0,
        })),
      ],
    })),

  removeFile: (index) =>
    set((state) => ({
      files: state.files.filter((_, i) => i !== index),
    })),

  clearFiles: () =>
    set({
      files: [],
      batchMetadata: null,
      isUploading: false,
    }),

  updateFileStatus: (index, status, data) =>
    set((state) => {
      const newFiles = [...state.files];
      newFiles[index] = {
        ...newFiles[index],
        status,
        ...data,
      };
      return { files: newFiles };
    }),

  setFileProgress: (index, progress) =>
    set((state) => {
      const newFiles = [...state.files];
      newFiles[index] = {
        ...newFiles[index],
        progress,
      };
      return { files: newFiles };
    }),

  setFileEncounterId: (index, encounterId) =>
    set((state) => {
      const newFiles = [...state.files];
      newFiles[index] = {
        ...newFiles[index],
        encounterId,
      };
      return { files: newFiles };
    }),

  setFileDuplicate: (index, duplicateInfo) =>
    set((state) => {
      const newFiles = [...state.files];
      newFiles[index] = {
        ...newFiles[index],
        status: 'duplicate',
        isDuplicate: true,
        duplicateInfo,
      };
      return { files: newFiles };
    }),

  setFileDuplicateHandling: (index, handling) =>
    set((state) => {
      const newFiles = [...state.files];
      newFiles[index] = {
        ...newFiles[index],
        duplicateHandling: handling,
        status: handling === 'SKIP' ? 'pending' : 'pending', // Reset to pending to be processed
      };
      return { files: newFiles };
    }),

  startBatch: (batchId) =>
    set((state) => ({
      batchMetadata: {
        batchId,
        totalFiles: state.files.length,
        completedCount: 0,
        startedAt: new Date(),
      },
      isUploading: true,
    })),

  completeBatch: () =>
    set((state) => ({
      batchMetadata: state.batchMetadata
        ? {
            ...state.batchMetadata,
            completedAt: new Date(),
          }
        : null,
      isUploading: false,
    })),

  setIsUploading: (isUploading) =>
    set({ isUploading }),

  getCompletedCount: () =>
    get().files.filter((f) => f.status === 'complete').length,

  getPendingCount: () =>
    get().files.filter((f) => f.status === 'pending').length,

  getErrorCount: () =>
    get().files.filter((f) => f.status === 'error').length,

  getDuplicateCount: () =>
    get().files.filter((f) => f.status === 'duplicate').length,
}));

/**
 * Integration tests for bulk upload feature
 * Tests the complete flow from file selection to upload completion
 */

import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from '@jest/globals';
import BulkUploadPage from '@/app/(dashboard)/encounters/bulk-upload/page';
import { useBulkUploadStore } from '@/store/useBulkUploadStore';
import apiClient from '@/lib/api/client';

// Mock API client
vi.mock('@/lib/api/client');

// Mock Next.js navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
}));

describe('Bulk Upload Integration Tests', () => {
  beforeEach(() => {
    // Reset store before each test
    useBulkUploadStore.getState().reset();
    vi.clearAllMocks();
  });

  describe('Multi-file Selection', () => {
    it('should allow selecting multiple files', async () => {
      render(<BulkUploadPage />);

      const file1 = new File(['clinical note 1'], 'note1.txt', { type: 'text/plain' });
      const file2 = new File(['clinical note 2'], 'note2.txt', { type: 'text/plain' });
      const file3 = new File(['clinical note 3'], 'note3.txt', { type: 'text/plain' });

      const fileInput = screen.getByLabelText(/select files/i);

      await userEvent.upload(fileInput, [file1, file2, file3]);

      await waitFor(() => {
        expect(screen.getByText('note1.txt')).toBeInTheDocument();
        expect(screen.getByText('note2.txt')).toBeInTheDocument();
        expect(screen.getByText('note3.txt')).toBeInTheDocument();
      });

      const store = useBulkUploadStore.getState();
      expect(store.files).toHaveLength(3);
    });

    it('should allow removing individual files from selection', async () => {
      render(<BulkUploadPage />);

      const file1 = new File(['note 1'], 'note1.txt', { type: 'text/plain' });
      const file2 = new File(['note 2'], 'note2.txt', { type: 'text/plain' });

      const fileInput = screen.getByLabelText(/select files/i);
      await userEvent.upload(fileInput, [file1, file2]);

      await waitFor(() => {
        expect(screen.getByText('note1.txt')).toBeInTheDocument();
      });

      // Remove first file
      const removeButtons = screen.getAllByRole('button', { name: /remove/i });
      await userEvent.click(removeButtons[0]);

      await waitFor(() => {
        expect(screen.queryByText('note1.txt')).not.toBeInTheDocument();
        expect(screen.getByText('note2.txt')).toBeInTheDocument();
      });
    });

    it('should validate file types', async () => {
      render(<BulkUploadPage />);

      const validFile = new File(['valid'], 'note.txt', { type: 'text/plain' });
      const invalidFile = new File(['invalid'], 'image.jpg', { type: 'image/jpeg' });

      const fileInput = screen.getByLabelText(/select files/i);
      await userEvent.upload(fileInput, [validFile, invalidFile]);

      await waitFor(() => {
        expect(screen.getByText('note.txt')).toBeInTheDocument();
        expect(screen.queryByText('image.jpg')).not.toBeInTheDocument();
        expect(screen.getByText(/invalid file type/i)).toBeInTheDocument();
      });
    });
  });

  describe('Duplicate Detection Flow', () => {
    it('should check for duplicates before upload', async () => {
      const mockCheckDuplicate = vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
        data: {
          is_duplicate: true,
          duplicate_info: {
            file_id: 'file-123',
            encounter_id: 'enc-123',
            original_filename: 'note1.txt',
            upload_timestamp: '2024-01-15T10:00:00Z',
            file_size: 1024,
          },
        },
      });

      render(<BulkUploadPage />);

      const file = new File(['clinical note'], 'note1.txt', { type: 'text/plain' });
      const fileInput = screen.getByLabelText(/select files/i);
      await userEvent.upload(fileInput, [file]);

      const uploadButton = screen.getByRole('button', { name: /start upload/i });
      await userEvent.click(uploadButton);

      await waitFor(() => {
        expect(mockCheckDuplicate).toHaveBeenCalledWith(
          expect.stringContaining('check-duplicate'),
          expect.any(FormData)
        );
      });

      // Duplicate modal should appear
      await waitFor(() => {
        expect(screen.getByText(/duplicate file detected/i)).toBeInTheDocument();
      });
    });

    it('should show duplicate handling options', async () => {
      vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
        data: {
          is_duplicate: true,
          duplicate_info: {
            file_id: 'file-123',
            encounter_id: 'enc-123',
            original_filename: 'original.txt',
            upload_timestamp: '2024-01-15T10:00:00Z',
            file_size: 1024,
          },
        },
      });

      render(<BulkUploadPage />);

      const file = new File(['note'], 'duplicate.txt', { type: 'text/plain' });
      await userEvent.upload(screen.getByLabelText(/select files/i), [file]);
      await userEvent.click(screen.getByRole('button', { name: /start upload/i }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /skip/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /replace/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /process as new/i })).toBeInTheDocument();
      });
    });

    it('should handle Skip duplicate action', async () => {
      vi.spyOn(apiClient, 'post')
        .mockResolvedValueOnce({
          data: {
            is_duplicate: true,
            duplicate_info: {
              file_id: 'file-123',
              encounter_id: 'enc-123',
              original_filename: 'note.txt',
              upload_timestamp: '2024-01-15T10:00:00Z',
              file_size: 1024,
            },
          },
        })
        .mockResolvedValueOnce({
          data: {
            encounter_id: 'enc-456',
            file_id: 'file-456',
            status: 'PENDING',
          },
        });

      render(<BulkUploadPage />);

      const file = new File(['note'], 'note.txt', { type: 'text/plain' });
      await userEvent.upload(screen.getByLabelText(/select files/i), [file]);
      await userEvent.click(screen.getByRole('button', { name: /start upload/i }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /skip/i })).toBeInTheDocument();
      });

      await userEvent.click(screen.getByRole('button', { name: /skip/i }));

      await waitFor(() => {
        const store = useBulkUploadStore.getState();
        expect(store.files[0].duplicateHandling).toBe('SKIP');
      });
    });

    it('should handle Process as New duplicate action', async () => {
      const mockUpload = vi.spyOn(apiClient, 'post')
        .mockResolvedValueOnce({
          data: { is_duplicate: true, duplicate_info: { file_id: 'file-123' } },
        })
        .mockResolvedValueOnce({
          data: { encounter_id: 'enc-456', file_id: 'file-456' },
        });

      render(<BulkUploadPage />);

      const file = new File(['note'], 'note.txt', { type: 'text/plain' });
      await userEvent.upload(screen.getByLabelText(/select files/i), [file]);
      await userEvent.click(screen.getByRole('button', { name: /start upload/i }));

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /process as new/i })).toBeInTheDocument();
      });

      await userEvent.click(screen.getByRole('button', { name: /process as new/i }));

      await waitFor(() => {
        expect(mockUpload).toHaveBeenCalledWith(
          expect.stringContaining('upload-note'),
          expect.objectContaining({
            duplicate_handling: 'PROCESS_AS_NEW',
          })
        );
      });
    });
  });

  describe('Upload Progress Tracking', () => {
    it('should show individual file progress', async () => {
      vi.spyOn(apiClient, 'post')
        .mockResolvedValueOnce({ data: { is_duplicate: false } })
        .mockImplementation(
          () =>
            new Promise((resolve) =>
              setTimeout(
                () =>
                  resolve({
                    data: { encounter_id: 'enc-123', file_id: 'file-123' },
                  }),
                100
              )
            )
        );

      render(<BulkUploadPage />);

      const file = new File(['note'], 'note.txt', { type: 'text/plain' });
      await userEvent.upload(screen.getByLabelText(/select files/i), [file]);
      await userEvent.click(screen.getByRole('button', { name: /start upload/i }));

      // Should show uploading status
      await waitFor(() => {
        expect(screen.getByText(/uploading/i)).toBeInTheDocument();
      });

      // Should eventually show complete
      await waitFor(
        () => {
          expect(screen.getByText(/complete/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should show batch progress statistics', async () => {
      vi.spyOn(apiClient, 'post')
        .mockResolvedValueOnce({ data: { is_duplicate: false } })
        .mockResolvedValueOnce({ data: { is_duplicate: false } })
        .mockResolvedValueOnce({ data: { is_duplicate: false } })
        .mockResolvedValue({ data: { encounter_id: 'enc-123', file_id: 'file-123' } });

      render(<BulkUploadPage />);

      const files = [
        new File(['note 1'], 'note1.txt', { type: 'text/plain' }),
        new File(['note 2'], 'note2.txt', { type: 'text/plain' }),
        new File(['note 3'], 'note3.txt', { type: 'text/plain' }),
      ];

      await userEvent.upload(screen.getByLabelText(/select files/i), files);
      await userEvent.click(screen.getByRole('button', { name: /start upload/i }));

      await waitFor(() => {
        // Should show total count
        expect(screen.getByText(/total: 3/i)).toBeInTheDocument();
      });

      await waitFor(
        () => {
          // Should show completed count
          expect(screen.getByText(/completed: 3/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should display progress bar for batch', async () => {
      vi.spyOn(apiClient, 'post')
        .mockResolvedValue({ data: { is_duplicate: false } })
        .mockResolvedValue({ data: { encounter_id: 'enc-123', file_id: 'file-123' } });

      render(<BulkUploadPage />);

      const files = [
        new File(['note 1'], 'note1.txt', { type: 'text/plain' }),
        new File(['note 2'], 'note2.txt', { type: 'text/plain' }),
      ];

      await userEvent.upload(screen.getByLabelText(/select files/i), files);
      await userEvent.click(screen.getByRole('button', { name: /start upload/i }));

      await waitFor(() => {
        const progressBar = screen.getByRole('progressbar');
        expect(progressBar).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('should display error for failed uploads', async () => {
      vi.spyOn(apiClient, 'post')
        .mockResolvedValueOnce({ data: { is_duplicate: false } })
        .mockRejectedValueOnce(new Error('Upload failed'));

      render(<BulkUploadPage />);

      const file = new File(['note'], 'note.txt', { type: 'text/plain' });
      await userEvent.upload(screen.getByLabelText(/select files/i), [file]);
      await userEvent.click(screen.getByRole('button', { name: /start upload/i }));

      await waitFor(() => {
        expect(screen.getByText(/error/i)).toBeInTheDocument();
      });

      const store = useBulkUploadStore.getState();
      expect(store.files[0].status).toBe('error');
    });

    it('should continue with other files when one fails', async () => {
      vi.spyOn(apiClient, 'post')
        .mockResolvedValueOnce({ data: { is_duplicate: false } })
        .mockRejectedValueOnce(new Error('Upload failed'))
        .mockResolvedValueOnce({ data: { is_duplicate: false } })
        .mockResolvedValueOnce({
          data: { encounter_id: 'enc-123', file_id: 'file-123' },
        });

      render(<BulkUploadPage />);

      const files = [
        new File(['note 1'], 'note1.txt', { type: 'text/plain' }),
        new File(['note 2'], 'note2.txt', { type: 'text/plain' }),
      ];

      await userEvent.upload(screen.getByLabelText(/select files/i), files);
      await userEvent.click(screen.getByRole('button', { name: /start upload/i }));

      await waitFor(() => {
        const store = useBulkUploadStore.getState();
        expect(store.files.some((f) => f.status === 'error')).toBe(true);
        expect(store.files.some((f) => f.status === 'complete')).toBe(true);
      });
    });
  });

  describe('Batch Completion', () => {
    it('should show completion summary after all files uploaded', async () => {
      vi.spyOn(apiClient, 'post')
        .mockResolvedValueOnce({ data: { is_duplicate: false } })
        .mockResolvedValueOnce({ data: { is_duplicate: false } })
        .mockResolvedValueOnce({
          data: { encounter_id: 'enc-1', file_id: 'file-1' },
        })
        .mockResolvedValueOnce({
          data: { encounter_id: 'enc-2', file_id: 'file-2' },
        });

      render(<BulkUploadPage />);

      const files = [
        new File(['note 1'], 'note1.txt', { type: 'text/plain' }),
        new File(['note 2'], 'note2.txt', { type: 'text/plain' }),
      ];

      await userEvent.upload(screen.getByLabelText(/select files/i), files);
      await userEvent.click(screen.getByRole('button', { name: /start upload/i }));

      await waitFor(
        () => {
          expect(screen.getByText(/upload complete/i)).toBeInTheDocument();
        },
        { timeout: 3000 }
      );
    });

    it('should provide links to individual reports', async () => {
      vi.spyOn(apiClient, 'post')
        .mockResolvedValueOnce({ data: { is_duplicate: false } })
        .mockResolvedValueOnce({
          data: { encounter_id: 'enc-123', file_id: 'file-123' },
        });

      render(<BulkUploadPage />);

      const file = new File(['note'], 'note.txt', { type: 'text/plain' });
      await userEvent.upload(screen.getByLabelText(/select files/i), [file]);
      await userEvent.click(screen.getByRole('button', { name: /start upload/i }));

      await waitFor(
        () => {
          const reportLink = screen.getByRole('link', { name: /view report/i });
          expect(reportLink).toHaveAttribute('href', '/reports/enc-123');
        },
        { timeout: 3000 }
      );
    });
  });
});

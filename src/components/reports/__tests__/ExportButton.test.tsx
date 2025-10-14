import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ExportButton from '../ExportButton';
import apiClient from '@/lib/api/client';

// Mock the API client
jest.mock('@/lib/api/client');
const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

// Mock URL.createObjectURL
global.URL.createObjectURL = jest.fn(() => 'mock-url');
global.URL.revokeObjectURL = jest.fn();

describe('ExportButton', () => {
  const mockEncounterId = 'test-encounter-123';

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders with default PDF format selected', () => {
    render(<ExportButton encounterId={mockEncounterId} />);

    expect(screen.getByLabelText(/Select export format/i)).toBeInTheDocument();
    expect(screen.getByRole('combobox')).toHaveValue('pdf');
    expect(screen.getByRole('button', { name: /Export report/i })).toBeInTheDocument();
  });

  it('displays all format options', () => {
    render(<ExportButton encounterId={mockEncounterId} />);

    const select = screen.getByRole('combobox');
    const options = Array.from(select.querySelectorAll('option'));

    expect(options).toHaveLength(4);
    expect(options.map(opt => opt.value)).toEqual(['pdf', 'csv', 'json', 'yaml']);
    expect(options.map(opt => opt.textContent)).toEqual([
      'PDF Report',
      'CSV Data',
      'JSON Data',
      'YAML Data',
    ]);
  });

  it('changes format when dropdown is changed', () => {
    render(<ExportButton encounterId={mockEncounterId} />);

    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'csv' } });

    expect(select).toHaveValue('csv');
    expect(screen.getByText(/Structured data for Excel/)).toBeInTheDocument();
  });

  it('shows correct description for each format', () => {
    render(<ExportButton encounterId={mockEncounterId} />);
    const select = screen.getByRole('combobox');

    // Test each format
    const formats = [
      { value: 'pdf', description: /Complete report with all analysis/ },
      { value: 'csv', description: /Structured data for Excel/ },
      { value: 'json', description: /Raw data for API integration/ },
      { value: 'yaml', description: /Human-readable structured data/ },
    ];

    formats.forEach(({ value, description }) => {
      fireEvent.change(select, { target: { value } });
      expect(screen.getByText(description)).toBeInTheDocument();
    });
  });

  it('downloads file successfully', async () => {
    const mockBlob = new Blob(['test data'], { type: 'application/pdf' });
    mockedApiClient.get.mockResolvedValueOnce({
      data: mockBlob,
    } as any);

    // Mock document methods
    const mockLink = {
      click: jest.fn(),
      remove: jest.fn(),
      setAttribute: jest.fn(),
      href: '',
    };
    jest.spyOn(document, 'createElement').mockReturnValueOnce(mockLink as any);
    jest.spyOn(document.body, 'appendChild').mockImplementation(() => mockLink as any);

    render(<ExportButton encounterId={mockEncounterId} />);

    const exportButton = screen.getByRole('button', { name: /Export report/i });
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(screen.getByText(/downloaded successfully/i)).toBeInTheDocument();
    });

    expect(mockedApiClient.get).toHaveBeenCalledWith(
      `/v1/reports/encounters/${mockEncounterId}?format=pdf`,
      { responseType: 'blob' }
    );
    expect(mockLink.click).toHaveBeenCalled();
    expect(mockLink.remove).toHaveBeenCalled();
  });

  it('shows loading state during export', async () => {
    mockedApiClient.get.mockImplementationOnce(
      () => new Promise(resolve => setTimeout(() => resolve({ data: new Blob() } as any), 100))
    );

    render(<ExportButton encounterId={mockEncounterId} />);

    const exportButton = screen.getByRole('button', { name: /Export report/i });
    fireEvent.click(exportButton);

    expect(screen.getByText(/Exporting/i)).toBeInTheDocument();
    expect(exportButton).toBeDisabled();

    await waitFor(() => {
      expect(screen.queryByText(/Exporting/i)).not.toBeInTheDocument();
    });
  });

  it('handles export error', async () => {
    const errorMessage = 'Export failed due to server error';
    mockedApiClient.get.mockRejectedValueOnce({
      response: {
        data: {
          detail: errorMessage,
        },
      },
    });

    render(<ExportButton encounterId={mockEncounterId} />);

    const exportButton = screen.getByRole('button', { name: /Export report/i });
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(screen.getByText(/Export Failed/i)).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  it('disables controls during export', async () => {
    mockedApiClient.get.mockImplementationOnce(
      () => new Promise(resolve => setTimeout(() => resolve({ data: new Blob() } as any), 100))
    );

    render(<ExportButton encounterId={mockEncounterId} />);

    const select = screen.getByRole('combobox');
    const exportButton = screen.getByRole('button', { name: /Export report/i });

    fireEvent.click(exportButton);

    expect(select).toBeDisabled();
    expect(exportButton).toBeDisabled();

    await waitFor(() => {
      expect(select).not.toBeDisabled();
      expect(exportButton).not.toBeDisabled();
    });
  });

  it('dismisses success notification', async () => {
    mockedApiClient.get.mockResolvedValueOnce({
      data: new Blob(),
    } as any);

    render(<ExportButton encounterId={mockEncounterId} />);

    const exportButton = screen.getByRole('button', { name: /Export report/i });
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(screen.getByText(/downloaded successfully/i)).toBeInTheDocument();
    });

    const dismissButton = screen.getByLabelText(/Dismiss notification/i);
    fireEvent.click(dismissButton);

    expect(screen.queryByText(/downloaded successfully/i)).not.toBeInTheDocument();
  });

  it('exports CSV format correctly', async () => {
    const mockBlob = new Blob(['csv data'], { type: 'text/csv' });
    mockedApiClient.get.mockResolvedValueOnce({
      data: mockBlob,
    } as any);

    const mockLink = {
      click: jest.fn(),
      remove: jest.fn(),
      setAttribute: jest.fn(),
      href: '',
    };
    jest.spyOn(document, 'createElement').mockReturnValueOnce(mockLink as any);
    jest.spyOn(document.body, 'appendChild').mockImplementation(() => mockLink as any);

    render(<ExportButton encounterId={mockEncounterId} />);

    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'csv' } });

    const exportButton = screen.getByRole('button', { name: /Export report/i });
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(mockedApiClient.get).toHaveBeenCalledWith(
        `/v1/reports/encounters/${mockEncounterId}?format=csv`,
        { responseType: 'blob' }
      );
    });
  });
});

import { render, screen, fireEvent } from '@testing-library/react';
import DenialRiskTable from '../DenialRiskTable';
import { DenialRisk } from '@/types/analysis';

describe('DenialRiskTable', () => {
  it('renders empty state when no denial risks', () => {
    render(<DenialRiskTable denialRisks={[]} />);

    expect(screen.getByText('Denial Risk Analysis')).toBeInTheDocument();
    expect(screen.getByText('Low Denial Risk')).toBeInTheDocument();
    expect(
      screen.getByText(/All codes appear to be well-documented/)
    ).toBeInTheDocument();
  });

  it('renders risk summary cards', () => {
    const risks: DenialRisk[] = [
      {
        code: '99214',
        risk_level: 'High',
        denial_reasons: ['Insufficient documentation'],
        documentation_addresses_risks: false,
        mitigation_notes: 'Add more details',
      },
      {
        code: '99213',
        risk_level: 'Medium',
        denial_reasons: ['Time not documented'],
        documentation_addresses_risks: true,
        mitigation_notes: 'Time is documented',
      },
      {
        code: '99212',
        risk_level: 'Low',
        denial_reasons: ['None identified'],
        documentation_addresses_risks: true,
        mitigation_notes: 'Well documented',
      },
    ];

    render(<DenialRiskTable denialRisks={risks} />);

    expect(screen.getByText('High Risk')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument(); // High risk count
    expect(screen.getByText('Medium Risk')).toBeInTheDocument();
    expect(screen.getByText('Low Risk')).toBeInTheDocument();
  });

  it('filters risks by level', () => {
    const risks: DenialRisk[] = [
      {
        code: '99214',
        risk_level: 'High',
        denial_reasons: ['Test'],
        documentation_addresses_risks: false,
        mitigation_notes: 'Test',
      },
      {
        code: '99213',
        risk_level: 'Low',
        denial_reasons: ['Test'],
        documentation_addresses_risks: true,
        mitigation_notes: 'Test',
      },
    ];

    render(<DenialRiskTable denialRisks={risks} />);

    // Initially shows all
    expect(screen.getByText('Showing 2 of 2 codes')).toBeInTheDocument();

    // Filter to high risk only
    const filterSelect = screen.getByRole('combobox');
    fireEvent.change(filterSelect, { target: { value: 'High' } });

    expect(screen.getByText('Showing 1 of 2 codes')).toBeInTheDocument();
  });

  it('expands row to show details', () => {
    const risks: DenialRisk[] = [
      {
        code: '99214',
        risk_level: 'High',
        denial_reasons: ['Reason 1', 'Reason 2'],
        documentation_addresses_risks: false,
        mitigation_notes: 'Mitigation strategy here',
      },
    ];

    render(<DenialRiskTable denialRisks={risks} />);

    // Initially, mitigation notes are not visible
    expect(screen.queryByText('Mitigation strategy here')).not.toBeInTheDocument();

    // Click the row to expand
    const codeCell = screen.getByText('99214');
    fireEvent.click(codeCell);

    // Now mitigation notes should be visible
    expect(screen.getByText('Mitigation strategy here')).toBeInTheDocument();
    expect(screen.getByText('Reason 1')).toBeInTheDocument();
    expect(screen.getByText('Reason 2')).toBeInTheDocument();
  });

  it('displays addressed status correctly', () => {
    const risks: DenialRisk[] = [
      {
        code: '99214',
        risk_level: 'High',
        denial_reasons: ['Test'],
        documentation_addresses_risks: true,
        mitigation_notes: 'Test',
      },
      {
        code: '99213',
        risk_level: 'High',
        denial_reasons: ['Test'],
        documentation_addresses_risks: false,
        mitigation_notes: 'Test',
      },
    ];

    render(<DenialRiskTable denialRisks={risks} />);

    expect(screen.getByText('Addressed')).toBeInTheDocument();
    expect(screen.getByText('Not Addressed')).toBeInTheDocument();
  });

  it('toggles "Show High Risk Only" button', () => {
    const risks: DenialRisk[] = [
      {
        code: '99214',
        risk_level: 'High',
        denial_reasons: ['Test'],
        documentation_addresses_risks: false,
        mitigation_notes: 'Test',
      },
      {
        code: '99213',
        risk_level: 'Low',
        denial_reasons: ['Test'],
        documentation_addresses_risks: true,
        mitigation_notes: 'Test',
      },
    ];

    render(<DenialRiskTable denialRisks={risks} />);

    const toggleButton = screen.getByRole('button', { name: /Show High Risk Only/ });

    // Initially shows all
    expect(screen.getByText('Showing 2 of 2 codes')).toBeInTheDocument();

    // Click to show only high risk
    fireEvent.click(toggleButton);

    expect(screen.getByText('Showing 1 of 2 codes')).toBeInTheDocument();
  });
});

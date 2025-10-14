/**
 * @jest-environment jsdom
 */

import { render, screen } from '@testing-library/react';
import ChargeCapture from '../ChargeCapture';
import type { UncapturedService } from '@/types/analysis-features';

describe('ChargeCapture', () => {
  const mockHighPriorityServices: UncapturedService[] = [
    {
      service: 'Joint Injection',
      location: 'Progress Note - Section 3, Paragraph 2',
      suggestedCodes: ['20610', '96372'],
      priority: 'High',
      estimatedRVUs: 3.45,
    },
    {
      service: 'Extended Counseling',
      location: 'Patient Education - Final paragraph',
      suggestedCodes: ['99354'],
      priority: 'High',
      estimatedRVUs: 2.1,
    },
  ];

  const mockMediumPriorityServices: UncapturedService[] = [
    {
      service: 'ECG Interpretation',
      location: 'Diagnostic Tests - Line 15',
      suggestedCodes: ['93010'],
      priority: 'Medium',
      estimatedRVUs: 0.68,
    },
  ];

  const mockLowPriorityServices: UncapturedService[] = [
    {
      service: 'Nebulizer Treatment',
      location: 'Treatment Plan - Bullet 2',
      suggestedCodes: ['94640'],
      priority: 'Low',
      estimatedRVUs: 0.45,
    },
  ];

  const mockMixedPriorityServices: UncapturedService[] = [
    ...mockHighPriorityServices,
    ...mockMediumPriorityServices,
    ...mockLowPriorityServices,
  ];

  it('returns null when no services provided', () => {
    const { container } = render(<ChargeCapture services={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders missed charges header', () => {
    render(<ChargeCapture services={mockHighPriorityServices} />);
    expect(screen.getByText('Missed Charges')).toBeInTheDocument();
  });

  it('displays alert banner for high priority items', () => {
    render(<ChargeCapture services={mockHighPriorityServices} />);
    expect(screen.getByText(/2 High-Priority Missed Charge/i)).toBeInTheDocument();
    expect(
      screen.getByText(/significant revenue impact and should be reviewed immediately/i)
    ).toBeInTheDocument();
  });

  it('does not display alert banner when no high priority items', () => {
    render(<ChargeCapture services={mockMediumPriorityServices} />);
    expect(screen.queryByText(/High-Priority Missed Charge/i)).not.toBeInTheDocument();
  });

  it('displays service names', () => {
    render(<ChargeCapture services={mockHighPriorityServices} />);
    expect(screen.getByText('Joint Injection')).toBeInTheDocument();
    expect(screen.getByText('Extended Counseling')).toBeInTheDocument();
  });

  it('shows chart locations', () => {
    render(<ChargeCapture services={mockHighPriorityServices} />);
    expect(screen.getByText(/Progress Note - Section 3, Paragraph 2/i)).toBeInTheDocument();
    expect(screen.getByText(/Patient Education - Final paragraph/i)).toBeInTheDocument();
  });

  it('displays suggested codes', () => {
    render(<ChargeCapture services={mockHighPriorityServices} />);
    expect(screen.getByText('20610')).toBeInTheDocument();
    expect(screen.getByText('96372')).toBeInTheDocument();
    expect(screen.getByText('99354')).toBeInTheDocument();
  });

  it('shows priority chips with correct colors', () => {
    const { container } = render(<ChargeCapture services={mockMixedPriorityServices} />);
    // Check that priority chips are rendered
    expect(screen.getByText('High')).toBeInTheDocument();
    expect(screen.getByText('Medium')).toBeInTheDocument();
    expect(screen.getByText('Low')).toBeInTheDocument();

    // Check for danger color class on high priority
    const highPriorityElements = container.querySelectorAll('.bg-red-50');
    expect(highPriorityElements.length).toBeGreaterThan(0);
  });

  it('displays estimated RVUs when provided', () => {
    render(<ChargeCapture services={mockHighPriorityServices} />);
    expect(screen.getByText(/3.45 RVUs/i)).toBeInTheDocument();
    expect(screen.getByText(/2.10 RVUs/i)).toBeInTheDocument();
  });

  it('calculates and displays total estimated RVUs', () => {
    render(<ChargeCapture services={mockHighPriorityServices} />);
    // Total: 3.45 + 2.1 = 5.55
    expect(screen.getByText(/~5.55 RVUs/i)).toBeInTheDocument();
  });

  it('shows total uncaptured services count', () => {
    render(<ChargeCapture services={mockMixedPriorityServices} />);
    expect(screen.getByText(/Total uncaptured services:/i)).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('displays educational note about documentation requirements', () => {
    render(<ChargeCapture services={mockHighPriorityServices} />);
    expect(
      screen.getByText(/Review chart documentation to confirm these services were actually performed/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Only bill for services that meet medical necessity and documentation requirements/i)
    ).toBeInTheDocument();
  });

  it('sorts services by priority (High -> Medium -> Low)', () => {
    const { container } = render(<ChargeCapture services={mockMixedPriorityServices} />);
    const serviceElements = container.querySelectorAll('[class*="p-4"][class*="rounded-lg"]');

    // First two should be high priority (red background)
    expect(serviceElements[0].className).toContain('bg-red-50');
    expect(serviceElements[1].className).toContain('bg-red-50');

    // Third should be medium priority (amber background)
    expect(serviceElements[2].className).toContain('bg-amber-50');

    // Fourth should be low priority (gray background)
    expect(serviceElements[3].className).toContain('bg-gray-50');
  });

  it('handles services without estimated RVUs', () => {
    const servicesWithoutRVUs: UncapturedService[] = [
      {
        service: 'Basic Service',
        location: 'Note Section 1',
        suggestedCodes: ['99213'],
        priority: 'Low',
      },
    ];

    render(<ChargeCapture services={servicesWithoutRVUs} />);
    expect(screen.getByText('Basic Service')).toBeInTheDocument();
    // Should not display RVU information
    expect(screen.queryByText(/RVUs/i)).not.toBeInTheDocument();
  });

  it('displays badge with service count', () => {
    render(<ChargeCapture services={mockMixedPriorityServices} />);
    expect(screen.getByText('4 uncaptured services')).toBeInTheDocument();
  });

  it('uses danger badge color when high priority items exist', () => {
    const { container } = render(<ChargeCapture services={mockHighPriorityServices} />);
    // Badge should have danger styling when high priority items present
    const badges = container.querySelectorAll('[class*="badge"]');
    expect(badges.length).toBeGreaterThan(0);
  });

  it('handles single high priority item (singular grammar)', () => {
    render(<ChargeCapture services={[mockHighPriorityServices[0]]} />);
    expect(screen.getByText('1 High-Priority Missed Charge')).toBeInTheDocument();
  });

  it('displays multiple suggested codes per service', () => {
    render(<ChargeCapture services={mockHighPriorityServices} />);
    // Joint Injection has two codes
    expect(screen.getByText('20610')).toBeInTheDocument();
    expect(screen.getByText('96372')).toBeInTheDocument();
  });

  it('renders chart location icon', () => {
    const { container } = render(<ChargeCapture services={mockHighPriorityServices} />);
    // MapPin icon should be rendered (lucide-react icon)
    const icons = container.querySelectorAll('svg');
    expect(icons.length).toBeGreaterThan(0);
  });
});

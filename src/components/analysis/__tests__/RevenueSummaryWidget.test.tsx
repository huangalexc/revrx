/**
 * @jest-environment jsdom
 */

import { render, screen } from '@testing-library/react';
import RevenueSummaryWidget from '../RevenueSummaryWidget';
import type { RevenueComparison } from '@/types/analysis-features';

describe('RevenueSummaryWidget', () => {
  const mockUnderCodingData: RevenueComparison = {
    billedCodes: ['99213', '80053'],
    billedRVUs: 2.5,
    suggestedCodes: ['99214', '80053', '36415'],
    suggestedRVUs: 3.2,
    missedRevenue: 0.7,
    percentDifference: 28.0,
  };

  const mockOptimalData: RevenueComparison = {
    billedCodes: ['99214', '80053'],
    billedRVUs: 3.2,
    suggestedCodes: ['99214', '80053'],
    suggestedRVUs: 3.2,
    missedRevenue: 0.0,
    percentDifference: 0.0,
  };

  const mockOverCodingData: RevenueComparison = {
    billedCodes: ['99215', '80053', '36415'],
    billedRVUs: 4.0,
    suggestedCodes: ['99214', '80053'],
    suggestedRVUs: 3.2,
    missedRevenue: -0.8,
    percentDifference: -20.0,
  };

  it('renders revenue analysis header', () => {
    render(<RevenueSummaryWidget data={mockUnderCodingData} />);
    expect(screen.getByText('Revenue Analysis')).toBeInTheDocument();
  });

  it('displays under-coding message when missed revenue is positive', () => {
    render(<RevenueSummaryWidget data={mockUnderCodingData} />);
    expect(screen.getByText('Under-coding detected')).toBeInTheDocument();
    expect(screen.getByText(/Potential Missed Revenue/i)).toBeInTheDocument();
  });

  it('displays optimal coding message when missed revenue is zero', () => {
    render(<RevenueSummaryWidget data={mockOptimalData} />);
    expect(screen.getByText('Coding is optimal')).toBeInTheDocument();
    expect(screen.getByText(/Optimal Coding/i)).toBeInTheDocument();
  });

  it('displays over-coding message when missed revenue is negative', () => {
    render(<RevenueSummaryWidget data={mockOverCodingData} />);
    expect(screen.getByText(/Compliance Review Recommended/i)).toBeInTheDocument();
  });

  it('displays billed and suggested RVUs correctly', () => {
    render(<RevenueSummaryWidget data={mockUnderCodingData} />);
    expect(screen.getByText('2.50')).toBeInTheDocument(); // billed RVUs
    expect(screen.getByText('3.20')).toBeInTheDocument(); // suggested RVUs
  });

  it('shows missed revenue amount and percentage', () => {
    render(<RevenueSummaryWidget data={mockUnderCodingData} />);
    expect(screen.getByText(/0.70 RVUs/i)).toBeInTheDocument();
    expect(screen.getByText(/28.0% increase/i)).toBeInTheDocument();
  });

  it('displays billed codes list', () => {
    render(<RevenueSummaryWidget data={mockUnderCodingData} />);
    expect(screen.getByText('99213')).toBeInTheDocument();
    expect(screen.getByText('80053')).toBeInTheDocument();
  });

  it('displays suggested codes list', () => {
    render(<RevenueSummaryWidget data={mockUnderCodingData} />);
    expect(screen.getByText('99214')).toBeInTheDocument();
    expect(screen.getByText('36415')).toBeInTheDocument();
  });

  it('highlights new suggested codes', () => {
    const { container } = render(<RevenueSummaryWidget data={mockUnderCodingData} />);
    // 36415 is new (not in billed codes)
    const newCodeElements = container.querySelectorAll('.border-blue-200');
    expect(newCodeElements.length).toBeGreaterThan(0);
  });

  it('shows educational note for under-coding', () => {
    render(<RevenueSummaryWidget data={mockUnderCodingData} />);
    expect(screen.getByText(/RVU \(Relative Value Unit\)/i)).toBeInTheDocument();
  });

  it('does not show educational note for optimal coding', () => {
    render(<RevenueSummaryWidget data={mockOptimalData} />);
    expect(screen.queryByText(/RVU \(Relative Value Unit\)/i)).not.toBeInTheDocument();
  });

  it('handles empty code arrays', () => {
    const emptyData: RevenueComparison = {
      billedCodes: [],
      billedRVUs: 0,
      suggestedCodes: [],
      suggestedRVUs: 0,
      missedRevenue: 0,
      percentDifference: 0,
    };
    render(<RevenueSummaryWidget data={emptyData} />);
    expect(screen.getByText('No codes billed')).toBeInTheDocument();
    expect(screen.getByText('No suggestions')).toBeInTheDocument();
  });
});

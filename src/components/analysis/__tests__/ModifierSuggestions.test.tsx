/**
 * @jest-environment jsdom
 */

import { render, screen } from '@testing-library/react';
import ModifierSuggestions from '../ModifierSuggestions';
import type { ModifierSuggestion } from '@/types/analysis-features';

describe('ModifierSuggestions', () => {
  const mockNewSuggestions: ModifierSuggestion[] = [
    {
      code: '99214',
      modifier: '-25',
      justification: 'Separately identifiable E/M service on same day as procedure',
      isNewSuggestion: true,
    },
    {
      code: '27447',
      modifier: '-59',
      justification: 'Distinct procedural service at different anatomic site',
      isNewSuggestion: true,
    },
  ];

  const mockExistingSuggestions: ModifierSuggestion[] = [
    {
      code: '99213',
      modifier: '-25',
      justification: 'Modifier already applied correctly',
      isNewSuggestion: false,
    },
  ];

  const mockMixedSuggestions: ModifierSuggestion[] = [
    ...mockNewSuggestions,
    ...mockExistingSuggestions,
  ];

  it('returns null when no suggestions provided', () => {
    const { container } = render(<ModifierSuggestions suggestions={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders modifier suggestions header', () => {
    render(<ModifierSuggestions suggestions={mockNewSuggestions} />);
    expect(screen.getByText('Modifier Suggestions')).toBeInTheDocument();
  });

  it('displays count of new suggestions', () => {
    render(<ModifierSuggestions suggestions={mockNewSuggestions} />);
    expect(screen.getByText('2 New')).toBeInTheDocument();
  });

  it('shows new modifier suggestions section', () => {
    render(<ModifierSuggestions suggestions={mockNewSuggestions} />);
    expect(screen.getByText('New Modifier Suggestions')).toBeInTheDocument();
  });

  it('displays code with modifier format', () => {
    render(<ModifierSuggestions suggestions={mockNewSuggestions} />);
    expect(screen.getByText('99214-25')).toBeInTheDocument();
    expect(screen.getByText('27447-59')).toBeInTheDocument();
  });

  it('shows justification for each modifier', () => {
    render(<ModifierSuggestions suggestions={mockNewSuggestions} />);
    expect(
      screen.getByText(/Separately identifiable E\/M service on same day as procedure/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Distinct procedural service at different anatomic site/i)
    ).toBeInTheDocument();
  });

  it('displays existing modifiers section', () => {
    render(<ModifierSuggestions suggestions={mockMixedSuggestions} />);
    expect(screen.getByText('Existing Modifiers (Correctly Applied)')).toBeInTheDocument();
  });

  it('shows educational section', () => {
    render(<ModifierSuggestions suggestions={mockNewSuggestions} />);
    expect(screen.getByText('Understanding CPT Modifiers')).toBeInTheDocument();
    expect(screen.getByText(/Learn more about CPT modifiers/i)).toBeInTheDocument();
  });

  it('displays common modifier quick reference', () => {
    render(<ModifierSuggestions suggestions={mockNewSuggestions} />);
    expect(screen.getByText('Common Modifier Quick Reference')).toBeInTheDocument();
  });

  it('correctly separates new vs existing suggestions', () => {
    render(<ModifierSuggestions suggestions={mockMixedSuggestions} />);
    // Should have 2 new and 1 existing
    const newSection = screen.getByText('New Modifier Suggestions');
    const existingSection = screen.getByText('Existing Modifiers (Correctly Applied)');
    expect(newSection).toBeInTheDocument();
    expect(existingSection).toBeInTheDocument();
  });

  it('handles only new suggestions', () => {
    render(<ModifierSuggestions suggestions={mockNewSuggestions} />);
    expect(screen.getByText('New Modifier Suggestions')).toBeInTheDocument();
    expect(screen.queryByText('Existing Modifiers')).not.toBeInTheDocument();
  });

  it('handles only existing suggestions', () => {
    render(<ModifierSuggestions suggestions={mockExistingSuggestions} />);
    expect(screen.getByText('Existing Modifiers (Correctly Applied)')).toBeInTheDocument();
    expect(screen.queryByText('2 New')).not.toBeInTheDocument();
  });
});

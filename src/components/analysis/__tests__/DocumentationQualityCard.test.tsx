import { render, screen } from '@testing-library/react';
import DocumentationQualityCard from '../DocumentationQualityCard';
import { MissingDocumentation } from '@/types/analysis';

describe('DocumentationQualityCard', () => {
  it('renders empty state when no documentation gaps', () => {
    render(<DocumentationQualityCard missingDocumentation={[]} />);

    expect(screen.getByText('Documentation Quality')).toBeInTheDocument();
    expect(screen.getByText('Excellent Documentation')).toBeInTheDocument();
    expect(screen.getByText(/No documentation gaps identified/)).toBeInTheDocument();
  });

  it('renders quality score when provided', () => {
    render(
      <DocumentationQualityCard
        missingDocumentation={[]}
        documentationQualityScore={0.85}
      />
    );

    expect(screen.getByText('85%')).toBeInTheDocument();
  });

  it('renders documentation gaps grouped by priority', () => {
    const gaps: MissingDocumentation[] = [
      {
        section: 'History of Present Illness',
        issue: 'Duration not specified',
        suggestion: 'Add timeline',
        priority: 'High',
      },
      {
        section: 'Physical Exam',
        issue: 'Incomplete cardiovascular exam',
        suggestion: 'Document heart sounds',
        priority: 'Medium',
      },
      {
        section: 'Assessment',
        issue: 'Could be more specific',
        suggestion: 'Add differential diagnosis',
        priority: 'Low',
      },
    ];

    render(<DocumentationQualityCard missingDocumentation={gaps} />);

    expect(screen.getByText(/3 documentation gaps identified/)).toBeInTheDocument();
    expect(screen.getByText('High Priority (1)')).toBeInTheDocument();
    expect(screen.getByText('Medium Priority (1)')).toBeInTheDocument();
    expect(screen.getByText('Low Priority (1)')).toBeInTheDocument();

    expect(screen.getByText('History of Present Illness')).toBeInTheDocument();
    expect(screen.getByText(/Duration not specified/)).toBeInTheDocument();
    expect(screen.getByText(/Add timeline/)).toBeInTheDocument();
  });

  it('displays priority badges with correct colors', () => {
    const gaps: MissingDocumentation[] = [
      {
        section: 'Test Section',
        issue: 'Test issue',
        suggestion: 'Test suggestion',
        priority: 'High',
      },
    ];

    const { container } = render(
      <DocumentationQualityCard missingDocumentation={gaps} />
    );

    const highPriorityBadge = screen.getByText('High');
    expect(highPriorityBadge).toHaveClass('text-red-700');
  });
});

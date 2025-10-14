# Analysis Components

Enhanced UI components for displaying medical coding analysis features.

## Components

### DocumentationQualityCard

Displays documentation quality analysis with missing elements and actionable suggestions.

**Props:**
- `missingDocumentation: MissingDocumentation[]` - List of documentation gaps
- `documentationQualityScore?: number` - Overall quality score (0.0-1.0)

**Features:**
- Empty state for excellent documentation
- Priority-based grouping (High/Medium/Low)
- Color-coded visual hierarchy
- Actionable suggestions for each gap
- Responsive layout

**Usage:**
```tsx
import { DocumentationQualityCard } from '@/components/analysis';

<DocumentationQualityCard
  missingDocumentation={reportData.missing_documentation || []}
  documentationQualityScore={reportData.audit_metadata?.documentation_quality_score}
/>
```

**Accessibility:**
- Semantic HTML with proper heading hierarchy
- Color + icon + text for status indicators (not color-only)
- High contrast text
- Keyboard navigable

---

### DenialRiskTable

Interactive table displaying denial risk analysis for billing codes.

**Props:**
- `denialRisks: DenialRisk[]` - List of codes with denial risk assessment

**Features:**
- Risk level filtering (All/High/Medium/Low)
- "Show High Risk Only" toggle
- Sortable by code or risk level
- Expandable rows with detailed denial reasons and mitigation strategies
- Risk summary cards (counts by level)
- Responsive design (table on desktop, cards on mobile)
- Color-coded risk levels (Red/Yellow/Green)
- Documentation status indicators (Addressed/Not Addressed)

**Usage:**
```tsx
import { DenialRiskTable } from '@/components/analysis';

<DenialRiskTable denialRisks={reportData.denial_risks || []} />
```

**Accessibility:**
- Semantic table structure with proper headers
- ARIA labels for interactive elements
- Keyboard navigation (click to expand, tab to navigate)
- Color + icon + text for risk levels (not color-only)
- High contrast text in all states
- Responsive mobile view with card layout

---

## Type Definitions

Types are defined in `@/types/analysis.ts`:

```typescript
interface MissingDocumentation {
  section: string;
  issue: string;
  suggestion: string;
  priority: 'High' | 'Medium' | 'Low';
}

interface DenialRisk {
  code: string;
  risk_level: 'Low' | 'Medium' | 'High';
  denial_reasons: string[];
  documentation_addresses_risks: boolean;
  mitigation_notes: string;
}
```

---

## Error Handling

Both components are wrapped in ErrorBoundary in the report page:

```tsx
<ErrorBoundary>
  <DocumentationQualityCard {...props} />
</ErrorBoundary>

<ErrorBoundary>
  <DenialRiskTable {...props} />
</ErrorBoundary>
```

This prevents component errors from breaking the entire page.

---

## Testing

Test files located in `__tests__/`:
- `DocumentationQualityCard.test.tsx`
- `DenialRiskTable.test.tsx`

Run tests:
```bash
npm test src/components/analysis
```

---

## Design Principles

### Visual Hierarchy
- Clear section headers with icons
- Priority-based color coding
- Appropriate spacing and grouping
- Empty states for positive outcomes

### Color System
- **Red** (High priority/risk): Urgent attention needed
- **Yellow** (Medium): Should address
- **Green** (Low/Good): On track
- **Blue** (Info): Additional context

### Responsive Design
- Desktop: Full table layouts with all columns
- Tablet: Slightly condensed layouts
- Mobile: Card-based layouts with essential info first

### Accessibility
- WCAG 2.1 AA compliant
- Color is never the only indicator
- All interactive elements keyboard accessible
- Semantic HTML throughout
- High contrast text (4.5:1 minimum)

---

## Performance

### Optimization Strategies
- Memoized filtering and sorting in DenialRiskTable
- Conditional rendering to avoid unnecessary DOM
- Lazy expansion of details (only render when expanded)
- Efficient state management with useState

### Bundle Size
- DocumentationQualityCard: ~4KB
- DenialRiskTable: ~9KB (includes filtering/sorting logic)
- Total: ~13KB (minified)

---

## Future Enhancements

### Planned Features
- [ ] Export individual sections to PDF
- [ ] Copy suggestions to clipboard
- [ ] Bulk actions for denial risks
- [ ] Historical comparison (track improvements over time)
- [ ] Customizable priority thresholds
- [ ] Integration with external coding guidelines

### Performance Improvements
- [ ] Virtual scrolling for large datasets
- [ ] Skeleton loading states
- [ ] Optimistic UI updates

---

## Related Components

- **ErrorBoundary**: Wraps components to prevent crashes
- **ProcessingStatus**: Shows loading states during analysis
- **ReportDetailPage**: Parent page that integrates these components

---

## Dependencies

- `lucide-react`: Icon library
- `@/types/analysis`: Type definitions
- React hooks: `useState`, `useMemo`

---

## Support

For issues or questions:
1. Check component tests for usage examples
2. Review type definitions in `@/types/analysis.ts`
3. See integration in `/src/app/(dashboard)/reports/[id]/page.tsx`

---

**Version:** 1.0
**Last Updated:** 2025-10-03
**Track:** D - UI Components (Quality & Risk)

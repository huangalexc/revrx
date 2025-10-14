'use client';

import { AlertCircle, CheckCircle, FileText, TrendingUp } from 'lucide-react';
import { MissingDocumentation } from '@/types/analysis';

interface DocumentationQualityCardProps {
  missingDocumentation: MissingDocumentation[];
  documentationQualityScore?: number;
}

const priorityConfig = {
  High: {
    color: 'text-red-700',
    bg: 'bg-red-50',
    border: 'border-red-200',
    badge: 'bg-red-100 text-red-700',
    icon: AlertCircle,
  },
  Medium: {
    color: 'text-yellow-700',
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    badge: 'bg-yellow-100 text-yellow-700',
    icon: AlertCircle,
  },
  Low: {
    color: 'text-blue-700',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    badge: 'bg-blue-100 text-blue-700',
    icon: TrendingUp,
  },
};

export default function DocumentationQualityCard({
  missingDocumentation,
  documentationQualityScore,
}: DocumentationQualityCardProps) {
  // Empty state
  if (!missingDocumentation || missingDocumentation.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <CheckCircle className="w-5 h-5 text-green-600" />
          <h2 className="text-xl font-semibold text-gray-900">
            Documentation Quality
          </h2>
        </div>
        <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
          <CheckCircle className="w-8 h-8 text-green-600 flex-shrink-0" />
          <div>
            <p className="font-medium text-green-900">
              Excellent Documentation
            </p>
            <p className="text-sm text-green-700">
              No documentation gaps identified. The clinical note contains all necessary elements to support the billed codes.
            </p>
          </div>
        </div>
        {documentationQualityScore !== undefined && (
          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">
                Quality Score
              </span>
              <span className="text-lg font-bold text-green-600">
                {Math.round(documentationQualityScore * 100)}%
              </span>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Group by priority for better organization
  const highPriority = missingDocumentation.filter(
    (doc) => doc.priority === 'High'
  );
  const mediumPriority = missingDocumentation.filter(
    (doc) => doc.priority === 'Medium'
  );
  const lowPriority = missingDocumentation.filter(
    (doc) => doc.priority === 'Low'
  );

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-600" />
          <h2 className="text-xl font-semibold text-gray-900">
            Documentation Quality
          </h2>
        </div>
        {documentationQualityScore !== undefined && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">Quality Score:</span>
            <span
              className={`text-lg font-bold ${
                documentationQualityScore >= 0.8
                  ? 'text-green-600'
                  : documentationQualityScore >= 0.6
                  ? 'text-yellow-600'
                  : 'text-red-600'
              }`}
            >
              {Math.round(documentationQualityScore * 100)}%
            </span>
          </div>
        )}
      </div>

      {/* Summary */}
      <p className="text-sm text-gray-600 mb-6">
        {missingDocumentation.length === 1
          ? '1 documentation gap identified'
          : `${missingDocumentation.length} documentation gaps identified`}{' '}
        that could improve coding accuracy and reduce denial risk.
      </p>

      {/* Priority Sections */}
      <div className="space-y-4">
        {/* High Priority */}
        {highPriority.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-red-900 flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              High Priority ({highPriority.length})
            </h3>
            {highPriority.map((doc, index) => (
              <DocumentationGapItem key={`high-${index}`} doc={doc} />
            ))}
          </div>
        )}

        {/* Medium Priority */}
        {mediumPriority.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-yellow-900 flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              Medium Priority ({mediumPriority.length})
            </h3>
            {mediumPriority.map((doc, index) => (
              <DocumentationGapItem key={`medium-${index}`} doc={doc} />
            ))}
          </div>
        )}

        {/* Low Priority */}
        {lowPriority.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-blue-900 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Low Priority ({lowPriority.length})
            </h3>
            {lowPriority.map((doc, index) => (
              <DocumentationGapItem key={`low-${index}`} doc={doc} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function DocumentationGapItem({ doc }: { doc: MissingDocumentation }) {
  const config = priorityConfig[doc.priority];
  const Icon = config.icon;

  return (
    <div
      className={`border ${config.border} ${config.bg} rounded-lg p-4 hover:shadow-sm transition-shadow`}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          <Icon className={`w-5 h-5 ${config.color}`} />
        </div>
        <div className="flex-1 min-w-0">
          {/* Section and Priority */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <h4 className="text-sm font-semibold text-gray-900">
              {doc.section}
            </h4>
            <span
              className={`px-2 py-0.5 text-xs font-medium rounded ${config.badge}`}
            >
              {doc.priority}
            </span>
          </div>

          {/* Issue */}
          <p className="text-sm text-gray-700 mb-2">
            <span className="font-medium">Issue:</span> {doc.issue}
          </p>

          {/* Suggestion */}
          <div className="bg-white border border-gray-200 rounded p-3">
            <p className="text-xs font-medium text-gray-600 mb-1">
              💡 Suggested Improvement:
            </p>
            <p className="text-sm text-gray-800">{doc.suggestion}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

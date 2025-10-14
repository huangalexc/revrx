'use client';

import { Card, CardHeader, CardBody, Chip, Tooltip } from '@heroui/react';
import { Info, ExternalLink, Sparkles } from 'lucide-react';
import type { ModifierSuggestion } from '@/types/analysis-features';

interface ModifierSuggestionsProps {
  suggestions: ModifierSuggestion[];
}

// Common modifier descriptions for education
const MODIFIER_DESCRIPTIONS: Record<string, { name: string; description: string; example: string }> = {
  '-25': {
    name: 'Significant, Separately Identifiable E/M',
    description:
      'Use when an Evaluation and Management service is performed on the same day as a procedure or other service.',
    example: 'Office visit on same day as minor procedure (e.g., 99214-25 with lesion removal)',
  },
  '-59': {
    name: 'Distinct Procedural Service',
    description:
      'Indicates a procedure or service was distinct or independent from other services performed on the same day.',
    example: 'Multiple procedures at different anatomic sites (e.g., EKG and spirometry)',
  },
  '-76': {
    name: 'Repeat Procedure by Same Physician',
    description: 'Use when a procedure is repeated by the same physician on the same day.',
    example: 'Second X-ray on same day by same provider',
  },
  '-77': {
    name: 'Repeat Procedure by Another Physician',
    description: 'Use when a procedure is repeated by a different physician on the same day.',
    example: 'Second interpretation of imaging by different radiologist',
  },
  '-24': {
    name: 'Unrelated E/M During Post-Op Period',
    description:
      'Indicates an E/M service during the post-operative period that is unrelated to the original procedure.',
    example: 'Office visit for unrelated condition during surgical post-op period',
  },
  '-57': {
    name: 'Decision for Surgery',
    description:
      'Use when an E/M service resulted in the initial decision to perform surgery within 1 day (major) or 24 hours (minor).',
    example: 'E/M visit where decision for surgery was made',
  },
  '-51': {
    name: 'Multiple Procedures',
    description: 'Indicates that multiple procedures were performed at the same session.',
    example: 'Two or more procedures performed during same operative session',
  },
  '-52': {
    name: 'Reduced Services',
    description:
      'Use when a service or procedure is partially reduced or eliminated at the physician's discretion.',
    example: 'Procedure started but discontinued due to patient condition',
  },
  '-53': {
    name: 'Discontinued Procedure',
    description:
      'Use when a procedure is discontinued due to extenuating circumstances or patient safety.',
    example: 'Procedure stopped due to patient reaction',
  },
  '-91': {
    name: 'Repeat Lab Test',
    description:
      'Use when a clinical diagnostic laboratory test is repeated on the same day for the same patient.',
    example: 'Multiple glucose tests throughout the day',
  },
};

export default function ModifierSuggestions({ suggestions }: ModifierSuggestionsProps) {
  if (suggestions.length === 0) {
    return null;
  }

  // Separate new suggestions from existing modifiers
  const newSuggestions = suggestions.filter((s) => s.isNewSuggestion);
  const existingModifiers = suggestions.filter((s) => !s.isNewSuggestion);

  return (
    <Card className="w-full dark:bg-gray-800 dark:border-gray-700">
      <CardHeader className="flex flex-col items-start p-6 pb-4">
        <div className="flex items-center justify-between w-full mb-2">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white">Modifier Suggestions</h3>
          {newSuggestions.length > 0 && (
            <Chip color="warning" variant="flat" size="sm" className="font-medium">
              {newSuggestions.length} New
            </Chip>
          )}
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          CPT modifiers to maximize appropriate reimbursement
        </p>
      </CardHeader>

      <CardBody className="p-6 pt-0 space-y-6">
        {/* New Modifier Suggestions */}
        {newSuggestions.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                New Modifier Suggestions
              </h4>
            </div>

            {newSuggestions.map((suggestion, index) => {
              const modifierInfo = MODIFIER_DESCRIPTIONS[suggestion.modifier];

              return (
                <div
                  key={index}
                  className="p-4 bg-amber-50 dark:bg-amber-900/20 border-2 border-amber-200 dark:border-amber-800 rounded-lg"
                >
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <div className="flex items-center gap-2">
                      <code className="px-3 py-1.5 bg-white dark:bg-gray-800 border border-amber-300 dark:border-amber-700 rounded font-mono text-sm font-semibold text-gray-900 dark:text-white">
                        {suggestion.code}
                        {suggestion.modifier}
                      </code>
                      {modifierInfo && (
                        <Tooltip
                          content={
                            <div className="max-w-xs p-2">
                              <p className="font-semibold text-sm mb-1">{modifierInfo.name}</p>
                              <p className="text-xs mb-2">{modifierInfo.description}</p>
                              <p className="text-xs text-gray-400">
                                <span className="font-semibold">Example:</span> {modifierInfo.example}
                              </p>
                            </div>
                          }
                          placement="top"
                        >
                          <Info className="w-4 h-4 text-amber-600 dark:text-amber-400 cursor-help" />
                        </Tooltip>
                      )}
                    </div>
                  </div>

                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    <span className="font-medium">Justification:</span> {suggestion.justification}
                  </p>

                  {modifierInfo && (
                    <div className="mt-3 p-2 bg-white dark:bg-gray-800/50 rounded text-xs">
                      <p className="text-gray-600 dark:text-gray-400">
                        <span className="font-semibold">Modifier {suggestion.modifier}:</span>{' '}
                        {modifierInfo.name}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Existing Modifiers (Already Billed Correctly) */}
        {existingModifiers.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
              Existing Modifiers (Correctly Applied)
            </h4>

            {existingModifiers.map((suggestion, index) => {
              const modifierInfo = MODIFIER_DESCRIPTIONS[suggestion.modifier];

              return (
                <div
                  key={index}
                  className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg"
                >
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <div className="flex items-center gap-2">
                      <code className="px-3 py-1.5 bg-white dark:bg-gray-800 border border-green-300 dark:border-green-700 rounded font-mono text-sm font-semibold text-gray-900 dark:text-white">
                        {suggestion.code}
                        {suggestion.modifier}
                      </code>
                      {modifierInfo && (
                        <Tooltip
                          content={
                            <div className="max-w-xs p-2">
                              <p className="font-semibold text-sm mb-1">{modifierInfo.name}</p>
                              <p className="text-xs mb-2">{modifierInfo.description}</p>
                              <p className="text-xs text-gray-400">
                                <span className="font-semibold">Example:</span> {modifierInfo.example}
                              </p>
                            </div>
                          }
                          placement="top"
                        >
                          <Info className="w-4 h-4 text-green-600 dark:text-green-400 cursor-help" />
                        </Tooltip>
                      )}
                    </div>
                  </div>

                  <p className="text-sm text-gray-700 dark:text-gray-300">{suggestion.justification}</p>
                </div>
              );
            })}
          </div>
        )}

        {/* Educational Section */}
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1 space-y-2">
              <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-300">
                Understanding CPT Modifiers
              </h4>
              <p className="text-xs text-blue-800 dark:text-blue-300">
                CPT modifiers are two-digit codes that provide additional information about services performed.
                They help ensure proper reimbursement for services that may otherwise be denied or bundled.
              </p>
              <div className="pt-2">
                <a
                  href="https://www.ama-assn.org/practice-management/cpt/cpt-modifiers"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
                >
                  Learn more about CPT modifiers
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* Common Modifier Reference */}
        <details className="group">
          <summary className="cursor-pointer list-none">
            <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors">
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                Common Modifier Quick Reference
              </span>
              <svg
                className="w-4 h-4 text-gray-500 dark:text-gray-400 transition-transform group-open:rotate-180"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </summary>

          <div className="mt-3 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="space-y-3">
              {Object.entries(MODIFIER_DESCRIPTIONS).map(([modifier, info]) => (
                <div key={modifier} className="pb-3 border-b border-gray-200 dark:border-gray-600 last:border-0">
                  <div className="flex items-start gap-3">
                    <code className="px-2 py-1 bg-gray-200 dark:bg-gray-800 rounded font-mono text-xs font-semibold text-gray-900 dark:text-white flex-shrink-0">
                      {modifier}
                    </code>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">{info.name}</p>
                      <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">{info.description}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-500 italic">
                        Example: {info.example}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </details>
      </CardBody>
    </Card>
  );
}

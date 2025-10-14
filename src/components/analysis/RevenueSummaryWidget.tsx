'use client';

import { Card, CardHeader, CardBody, Progress, Chip } from '@heroui/react';
import { TrendingUp, TrendingDown, DollarSign, AlertTriangle } from 'lucide-react';
import type { RevenueComparison } from '@/types/analysis-features';

interface RevenueSummaryWidgetProps {
  data: RevenueComparison;
}

export default function RevenueSummaryWidget({ data }: RevenueSummaryWidgetProps) {
  const {
    billedCodes,
    billedRVUs,
    suggestedCodes,
    suggestedRVUs,
    missedRevenue,
    percentDifference,
  } = data;

  const isUnderCoding = missedRevenue > 0;
  const isOverCoding = missedRevenue < 0;
  const isOptimal = missedRevenue === 0;

  // Color coding based on revenue impact
  const getRevenueColor = () => {
    if (isOptimal) return 'success';
    if (isUnderCoding) return 'warning';
    return 'danger';
  };

  const getRevenueIcon = () => {
    if (isOptimal) return null;
    if (isUnderCoding) return <TrendingUp className="w-5 h-5" />;
    return <TrendingDown className="w-5 h-5" />;
  };

  const getRevenueMessage = () => {
    if (isOptimal) return 'Coding is optimal';
    if (isUnderCoding) return 'Under-coding detected';
    return 'Potential over-coding detected';
  };

  // Calculate percentage for progress bar (capped at 100%)
  const progressPercentage = Math.min(
    (suggestedRVUs / Math.max(billedRVUs, suggestedRVUs)) * 100,
    100
  );

  return (
    <Card className="w-full dark:bg-gray-800 dark:border-gray-700">
      <CardHeader className="flex flex-col items-start p-6 pb-4">
        <div className="flex items-center justify-between w-full mb-2">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
            Revenue Analysis
          </h3>
          <Chip
            color={getRevenueColor()}
            variant="flat"
            startContent={getRevenueIcon()}
            className="font-medium"
          >
            {getRevenueMessage()}
          </Chip>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Comparison of billed vs suggested codes and RVU values
        </p>
      </CardHeader>

      <CardBody className="p-6 pt-0 space-y-6">
        {/* RVU Comparison Bar Chart */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Billed RVUs
            </span>
            <span className="text-lg font-bold text-gray-900 dark:text-white">
              {billedRVUs.toFixed(2)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Suggested RVUs
            </span>
            <span className="text-lg font-bold text-gray-900 dark:text-white">
              {suggestedRVUs.toFixed(2)}
            </span>
          </div>

          {/* Visual RVU Comparison */}
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-600 dark:text-gray-400 w-20">Billed</span>
              <div className="flex-1">
                <Progress
                  value={billedRVUs === 0 ? 0 : (billedRVUs / Math.max(billedRVUs, suggestedRVUs)) * 100}
                  color="primary"
                  size="md"
                  className="max-w-full"
                />
              </div>
              <span className="text-xs font-medium text-gray-700 dark:text-gray-300 w-16 text-right">
                {billedRVUs.toFixed(2)}
              </span>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-600 dark:text-gray-400 w-20">Suggested</span>
              <div className="flex-1">
                <Progress
                  value={suggestedRVUs === 0 ? 0 : (suggestedRVUs / Math.max(billedRVUs, suggestedRVUs)) * 100}
                  color={isUnderCoding ? 'success' : isOverCoding ? 'danger' : 'primary'}
                  size="md"
                  className="max-w-full"
                />
              </div>
              <span className="text-xs font-medium text-gray-700 dark:text-gray-300 w-16 text-right">
                {suggestedRVUs.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        {/* Missed Revenue Highlight */}
        <div
          className={`p-4 rounded-lg border-2 ${
            isOptimal
              ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
              : isUnderCoding
              ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800'
              : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
          }`}
        >
          <div className="flex items-start gap-3">
            <div
              className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                isOptimal
                  ? 'bg-green-100 dark:bg-green-900/40'
                  : isUnderCoding
                  ? 'bg-amber-100 dark:bg-amber-900/40'
                  : 'bg-red-100 dark:bg-red-900/40'
              }`}
            >
              {isOptimal ? (
                <DollarSign className="w-5 h-5 text-green-600 dark:text-green-400" />
              ) : (
                <AlertTriangle
                  className={`w-5 h-5 ${
                    isUnderCoding
                      ? 'text-amber-600 dark:text-amber-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                />
              )}
            </div>

            <div className="flex-1">
              <h4
                className={`text-sm font-semibold mb-1 ${
                  isOptimal
                    ? 'text-green-900 dark:text-green-300'
                    : isUnderCoding
                    ? 'text-amber-900 dark:text-amber-300'
                    : 'text-red-900 dark:text-red-300'
                }`}
              >
                {isOptimal
                  ? 'Optimal Coding'
                  : isUnderCoding
                  ? 'Potential Missed Revenue'
                  : 'Compliance Review Recommended'}
              </h4>
              <p
                className={`text-sm ${
                  isOptimal
                    ? 'text-green-800 dark:text-green-300'
                    : isUnderCoding
                    ? 'text-amber-800 dark:text-amber-300'
                    : 'text-red-800 dark:text-red-300'
                }`}
              >
                {isOptimal ? (
                  'Your coding matches the suggested codes. No additional revenue identified.'
                ) : isUnderCoding ? (
                  <>
                    Suggested codes could capture an additional{' '}
                    <span className="font-bold">{Math.abs(missedRevenue).toFixed(2)} RVUs</span> (
                    <span className="font-bold">{Math.abs(percentDifference).toFixed(1)}%</span> increase).
                  </>
                ) : (
                  <>
                    Billed codes exceed suggested codes by{' '}
                    <span className="font-bold">{Math.abs(missedRevenue).toFixed(2)} RVUs</span>. Review for
                    over-coding compliance.
                  </>
                )}
              </p>
            </div>
          </div>
        </div>

        {/* Code Lists */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Billed Codes */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
              Billed Codes ({billedCodes.length})
            </h4>
            <div className="space-y-1">
              {billedCodes.length > 0 ? (
                billedCodes.map((code, index) => (
                  <div
                    key={index}
                    className="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 rounded text-sm font-mono text-gray-700 dark:text-gray-300"
                  >
                    {code}
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400 italic">No codes billed</p>
              )}
            </div>
          </div>

          {/* Suggested Codes */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
              Suggested Codes ({suggestedCodes.length})
            </h4>
            <div className="space-y-1">
              {suggestedCodes.length > 0 ? (
                suggestedCodes.map((code, index) => (
                  <div
                    key={index}
                    className={`px-3 py-1.5 rounded text-sm font-mono ${
                      !billedCodes.includes(code)
                        ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
                    }`}
                  >
                    {code}
                    {!billedCodes.includes(code) && (
                      <span className="ml-2 text-xs text-blue-600 dark:text-blue-400 font-normal">
                        • New
                      </span>
                    )}
                  </div>
                ))
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400 italic">No suggestions</p>
              )}
            </div>
          </div>
        </div>

        {/* Educational Note */}
        {isUnderCoding && (
          <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-xs text-blue-800 dark:text-blue-300">
              <span className="font-semibold">Note:</span> RVU (Relative Value Unit) estimates are based on
              standard Medicare rates. Actual reimbursement varies by payer, location, and contract rates.
              Review suggested codes for clinical accuracy before billing.
            </p>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

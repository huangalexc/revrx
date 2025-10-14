'use client';

import { Card, CardHeader, CardBody, Chip, Badge } from '@heroui/react';
import { AlertCircle, MapPin, DollarSign, FileText } from 'lucide-react';
import type { UncapturedService } from '@/types/analysis-features';

interface ChargeCaptureProps {
  services: UncapturedService[];
}

export default function ChargeCapture({ services }: ChargeCaptureProps) {
  if (services.length === 0) {
    return null;
  }

  // Count high priority items
  const highPriorityCount = services.filter((s) => s.priority === 'High').length;

  // Sort by priority (High -> Medium -> Low)
  const priorityOrder = { High: 0, Medium: 1, Low: 2 };
  const sortedServices = [...services].sort(
    (a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]
  );

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'High':
        return {
          chip: 'danger' as const,
          bg: 'bg-red-50 dark:bg-red-900/20',
          border: 'border-red-200 dark:border-red-800',
          icon: 'text-red-600 dark:text-red-400',
          text: 'text-red-900 dark:text-red-300',
        };
      case 'Medium':
        return {
          chip: 'warning' as const,
          bg: 'bg-amber-50 dark:bg-amber-900/20',
          border: 'border-amber-200 dark:border-amber-800',
          icon: 'text-amber-600 dark:text-amber-400',
          text: 'text-amber-900 dark:text-amber-300',
        };
      case 'Low':
        return {
          chip: 'default' as const,
          bg: 'bg-gray-50 dark:bg-gray-700',
          border: 'border-gray-200 dark:border-gray-600',
          icon: 'text-gray-600 dark:text-gray-400',
          text: 'text-gray-900 dark:text-gray-300',
        };
      default:
        return {
          chip: 'default' as const,
          bg: 'bg-gray-50 dark:bg-gray-700',
          border: 'border-gray-200 dark:border-gray-600',
          icon: 'text-gray-600 dark:text-gray-400',
          text: 'text-gray-900 dark:text-gray-300',
        };
    }
  };

  // Calculate total estimated RVUs
  const totalEstimatedRVUs = services.reduce((sum, service) => {
    return sum + (service.estimatedRVUs || 0);
  }, 0);

  return (
    <div className="space-y-4">
      {/* Alert Banner for High Priority Items */}
      {highPriorityCount > 0 && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-red-900 dark:text-red-300 mb-1">
                {highPriorityCount} High-Priority Missed Charge{highPriorityCount !== 1 && 's'}
              </h4>
              <p className="text-xs text-red-800 dark:text-red-300">
                These services have significant revenue impact and should be reviewed immediately.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Main Card */}
      <Card className="w-full dark:bg-gray-800 dark:border-gray-700">
        <CardHeader className="flex flex-col items-start p-6 pb-4">
          <div className="flex items-center justify-between w-full mb-2">
            <div className="flex items-center gap-2">
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                Missed Charges
              </h3>
              <Badge
                content={services.length}
                color={highPriorityCount > 0 ? 'danger' : 'primary'}
                size="lg"
                className="ml-1"
              >
                <span className="sr-only">{services.length} uncaptured services</span>
              </Badge>
            </div>
            {totalEstimatedRVUs > 0 && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg">
                <DollarSign className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <span className="text-sm font-semibold text-blue-900 dark:text-blue-300">
                  ~{totalEstimatedRVUs.toFixed(2)} RVUs
                </span>
              </div>
            )}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Services documented but not linked to billing codes
          </p>
        </CardHeader>

        <CardBody className="p-6 pt-0 space-y-4">
          {sortedServices.map((service, index) => {
            const colors = getPriorityColor(service.priority);

            return (
              <div
                key={index}
                className={`p-4 ${colors.bg} border ${colors.border} rounded-lg`}
              >
                {/* Header */}
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className={`text-sm font-semibold ${colors.text}`}>
                        {service.service}
                      </h4>
                      <Chip
                        color={colors.chip}
                        size="sm"
                        variant="flat"
                        className="font-medium"
                      >
                        {service.priority}
                      </Chip>
                    </div>

                    {/* Chart Location */}
                    <div className="flex items-start gap-2 mb-3">
                      <MapPin className={`w-4 h-4 ${colors.icon} flex-shrink-0 mt-0.5`} />
                      <p className="text-xs text-gray-700 dark:text-gray-300">
                        <span className="font-medium">Chart Location:</span> {service.location}
                      </p>
                    </div>

                    {/* Suggested Codes */}
                    <div className="space-y-2">
                      <p className="text-xs font-medium text-gray-700 dark:text-gray-300">
                        Suggested Codes:
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {service.suggestedCodes.map((code, codeIndex) => (
                          <code
                            key={codeIndex}
                            className="px-2.5 py-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded font-mono text-xs font-semibold text-gray-900 dark:text-white"
                          >
                            {code}
                          </code>
                        ))}
                      </div>
                    </div>

                    {/* Estimated RVUs */}
                    {service.estimatedRVUs !== undefined && service.estimatedRVUs > 0 && (
                      <div className="mt-3 flex items-center gap-2">
                        <DollarSign className={`w-4 h-4 ${colors.icon}`} />
                        <p className="text-xs text-gray-700 dark:text-gray-300">
                          <span className="font-medium">Estimated Value:</span>{' '}
                          {service.estimatedRVUs.toFixed(2)} RVUs
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Priority Icon */}
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      service.priority === 'High'
                        ? 'bg-red-100 dark:bg-red-900/40'
                        : service.priority === 'Medium'
                        ? 'bg-amber-100 dark:bg-amber-900/40'
                        : 'bg-gray-200 dark:bg-gray-600'
                    }`}
                  >
                    <FileText
                      className={`w-5 h-5 ${
                        service.priority === 'High'
                          ? 'text-red-600 dark:text-red-400'
                          : service.priority === 'Medium'
                          ? 'text-amber-600 dark:text-amber-400'
                          : 'text-gray-600 dark:text-gray-400'
                      }`}
                    />
                  </div>
                </div>
              </div>
            );
          })}

          {/* Summary Footer */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Total uncaptured services: <span className="font-semibold">{services.length}</span>
              </p>
              {totalEstimatedRVUs > 0 && (
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Total potential revenue:{' '}
                  <span className="font-semibold text-blue-600 dark:text-blue-400">
                    ~{totalEstimatedRVUs.toFixed(2)} RVUs
                  </span>
                </p>
              )}
            </div>
          </div>

          {/* Educational Note */}
          <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-xs text-blue-800 dark:text-blue-300">
              <span className="font-semibold">Important:</span> Review chart documentation to confirm
              these services were actually performed. Only bill for services that meet medical necessity
              and documentation requirements.
            </p>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}

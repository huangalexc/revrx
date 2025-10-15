'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import apiClient from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';
import ProcessingStatus from '@/components/encounters/ProcessingStatus';
import {
  Download,
  ArrowLeft,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  FileText,
  DollarSign,
} from 'lucide-react';
import ErrorBoundary from '@/components/ErrorBoundary';
import { DocumentationQualityCard, DenialRiskTable } from '@/components/analysis';
import ExportButton from '@/components/reports/ExportButton';

interface SuggestedCode {
  code: string;  // Changed from suggested_code to code
  code_type: string;
  description?: string;
  billed_code?: string;
  comparison_type?: 'new' | 'upgrade' | 'match';
  revenue_impact?: number;
  confidence: number;
  justification: string;
  supporting_text: string[];
}

interface BilledCode {
  code: string;
  code_type: string;
  description?: string;
}

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

interface ReportData {
  encounter_id: string;
  generated_at: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETE' | 'FAILED';
  metadata: {
    encounter_created: string;
    processing_time_ms?: number;
    processing_completed?: string;
    user_email: string;
    phi_included: boolean;
    phi_detected: boolean;
  };
  clinical_note: {
    text: string;
    length: number;
    uploaded_files: Array<{
      filename: string;
      file_type: string;
      file_size: number;
      uploaded_at: string;
    }>;
  };
  code_analysis: {
    billed_codes: BilledCode[];
    suggested_codes: SuggestedCode[];
    ai_model: string;
    confidence_score: number;
  };
  revenue_analysis: {
    incremental_revenue: number;
    currency: string;
    calculation_method: string;
  };
  summary: {
    total_billed_codes: number;
    total_suggested_codes: number;
    new_code_opportunities: number;
    upgrade_opportunities: number;
  };
  // New enhanced features
  missing_documentation?: MissingDocumentation[];
  denial_risks?: DenialRisk[];
  audit_metadata?: {
    documentation_quality_score?: number;
  };
}

export default function ReportDetailPage() {
  const params = useParams();
  const router = useRouter();
  const encounterId = params.reportId as string;

  const [reportData, setReportData] = useState<ReportData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchReport();
    // Poll for updates if processing or report not yet available
    const interval = setInterval(() => {
      if (!reportData || reportData?.status === 'PROCESSING' || reportData?.status === 'PENDING') {
        fetchReport();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [encounterId, reportData]);

  const fetchReport = async () => {
    setError(null);

    try {
      const response = await apiClient.get(API_ENDPOINTS.REPORTS.DETAIL(encounterId));
      setReportData(response.data);
      setIsLoading(false);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to load report';
      const statusCode = err.response?.status;

      // Don't show error for "not yet generated" or 404 (report still processing) - keep polling instead
      if (!errorMessage.includes('not yet generated') && statusCode !== 404) {
        setError(errorMessage);
        setIsLoading(false);
      }
      // Keep isLoading true for 404s so the loading state continues to show
      console.error('Failed to fetch report:', err);
    }
  };


  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading && !reportData) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg border border-gray-200 p-12">
          <div className="flex flex-col items-center justify-center text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mb-6"></div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Generating Your Report
            </h2>
            <p className="text-gray-600 mb-4">
              Please wait while we analyze your clinical note and generate coding suggestions.
            </p>
            <p className="text-sm text-gray-500">
              This usually takes 30-60 seconds...
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-900 mb-2">Error Loading Report</h3>
          <p className="text-red-700">{error}</p>
          <Link
            href="/encounters"
            className="mt-4 inline-flex items-center gap-2 text-sm text-red-600 hover:text-red-900"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Encounters
          </Link>
        </div>
      </div>
    );
  }

  if (!reportData) {
    return null;
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/encounters"
          className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Encounters
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Encounter Report
            </h1>
            <p className="text-gray-600 mt-2">
              {reportData.clinical_note?.uploaded_files?.[0]?.filename && `${reportData.clinical_note.uploaded_files[0].filename} • `}
              {reportData.metadata?.encounter_created && formatDate(reportData.metadata.encounter_created)}
            </p>
          </div>
          {reportData.status === 'COMPLETE' && (
            <ExportButton encounterId={encounterId} />
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Processing Status */}
          {(reportData.status === 'PENDING' || reportData.status === 'PROCESSING') && (
            <ProcessingStatus
              encounterId={encounterId}
              currentStatus={reportData.status.toLowerCase() as 'pending' | 'processing'}
              processingTime={reportData.metadata?.processing_time_ms ? reportData.metadata.processing_time_ms / 1000 : undefined}
            />
          )}

          {/* Value Summary Card */}
          {reportData.status === 'COMPLETE' && (
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg border border-blue-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Value Summary</h2>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-gray-600 mb-1">Originally Billed</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {reportData.code_analysis.billed_codes?.length || 0}
                  </p>
                  <p className="text-xs text-gray-500">codes</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Additional Opportunities</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {reportData.summary.new_code_opportunities + reportData.summary.upgrade_opportunities}
                  </p>
                  <p className="text-xs text-gray-500">
                    {reportData.summary.new_code_opportunities} new, {reportData.summary.upgrade_opportunities} upgrades
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 mb-1">Incremental Revenue</p>
                  <p className="text-2xl font-bold text-green-600">
                    {formatCurrency(reportData.revenue_analysis.incremental_revenue)}
                  </p>
                  <p className="text-xs text-gray-500">potential gain</p>
                </div>
              </div>
            </div>
          )}

          {/* Originally Billed Codes */}
          {reportData.status === 'COMPLETE' && reportData.code_analysis.billed_codes && reportData.code_analysis.billed_codes.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center gap-2 mb-6">
                <CheckCircle className="w-5 h-5 text-gray-500" />
                <h2 className="text-xl font-semibold text-gray-900">
                  Originally Billed Codes
                </h2>
              </div>
              <p className="text-sm text-gray-600 mb-4">
                These codes were already billed for this encounter:
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {reportData.code_analysis.billed_codes.map((code, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-3 p-4 bg-gray-50 rounded-lg border border-gray-200"
                  >
                    <div className="w-10 h-10 bg-gray-200 rounded-lg flex items-center justify-center flex-shrink-0">
                      <FileText className="w-5 h-5 text-gray-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="text-lg font-semibold text-gray-900">{code.code}</span>
                        <span className="px-2 py-0.5 text-xs font-medium bg-gray-200 text-gray-700 rounded">
                          {code.code_type}
                        </span>
                      </div>
                      {code.description && (
                        <p className="text-sm text-gray-600">{code.description}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Suggested Additional Codes */}
          {reportData.status === 'COMPLETE' && reportData.code_analysis.suggested_codes.length > 0 && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="w-5 h-5 text-green-600" />
                <h2 className="text-xl font-semibold text-gray-900">
                  Suggested Additional Codes
                </h2>
              </div>
              <p className="text-sm text-gray-600 mb-6">
                In addition to the {reportData.code_analysis.billed_codes?.length || 0} codes already billed,
                we identified {reportData.code_analysis.suggested_codes.length} additional coding opportunities:
              </p>
              <div className="space-y-4">
                {reportData.code_analysis.suggested_codes.map((code, index) => (
                  <div
                    key={index}
                    className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:bg-blue-50 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-start gap-3 flex-1">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                          code.comparison_type === 'new' ? 'bg-green-100' :
                          code.comparison_type === 'upgrade' ? 'bg-blue-100' : 'bg-gray-100'
                        }`}>
                          <FileText className={`w-5 h-5 ${
                            code.comparison_type === 'new' ? 'text-green-600' :
                            code.comparison_type === 'upgrade' ? 'text-blue-600' : 'text-gray-600'
                          }`} />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className="text-lg font-semibold text-gray-900">
                              {code.code}
                            </span>
                            <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-700 rounded">
                              {code.code_type}
                            </span>
                            <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                              code.comparison_type === 'new'
                                ? 'bg-green-100 text-green-700'
                                : code.comparison_type === 'upgrade'
                                ? 'bg-blue-100 text-blue-700'
                                : 'bg-gray-100 text-gray-700'
                            }`}>
                              {code.comparison_type?.toUpperCase() || 'UNKNOWN'}
                            </span>
                            {code.confidence && (
                              <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                                code.confidence >= 0.9
                                  ? 'bg-green-100 text-green-700'
                                  : code.confidence >= 0.75
                                  ? 'bg-yellow-100 text-yellow-700'
                                  : 'bg-orange-100 text-orange-700'
                              }`}>
                                {Math.round(code.confidence * 100)}% confidence
                              </span>
                            )}
                          </div>
                          {code.billed_code && (
                            <p className="text-sm text-gray-600 mb-2">
                              Compares to billed: <span className="font-medium">{code.billed_code}</span>
                            </p>
                          )}
                          <p className="text-sm text-gray-700 mb-3">
                            {code.justification}
                          </p>
                          {code.supporting_text && code.supporting_text.length > 0 && (
                            <div className="bg-gray-50 border border-gray-200 rounded p-3">
                              <p className="text-xs font-medium text-gray-600 mb-2">Supporting Evidence:</p>
                              <ul className="space-y-1">
                                {code.supporting_text.map((text, i) => (
                                  <li key={i} className="text-sm text-gray-600 italic">
                                    "{text}"
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      </div>
                      {code.revenue_impact > 0 && (
                        <div className="text-right flex-shrink-0 ml-4">
                          <div className="text-sm font-semibold text-green-600">
                            +{formatCurrency(code.revenue_impact)}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Documentation Quality Analysis */}
          {reportData.status === 'COMPLETE' && (
            <ErrorBoundary>
              <DocumentationQualityCard
                missingDocumentation={reportData.missing_documentation || []}
                documentationQualityScore={reportData.audit_metadata?.documentation_quality_score}
              />
            </ErrorBoundary>
          )}

          {/* Denial Risk Analysis */}
          {reportData.status === 'COMPLETE' && (
            <ErrorBoundary>
              <DenialRiskTable denialRisks={reportData.denial_risks || []} />
            </ErrorBoundary>
          )}

          {/* Clinical Note */}
          {reportData.status === 'COMPLETE' && reportData.clinical_note.text && (
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Clinical Note
              </h2>
              {reportData.metadata.phi_detected && (
                <div className="mb-3 px-4 py-2 rounded-lg text-sm bg-green-50 border border-green-200 text-green-800">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    <span>✓ PHI has been removed from this view. Sensitive information is redacted.</span>
                  </div>
                </div>
              )}
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <pre className="whitespace-pre-wrap font-mono text-sm text-gray-800">
                  {reportData.clinical_note.text}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Encounter Info */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Encounter Details
            </h3>
            <div className="space-y-3 text-sm">
              <div>
                <span className="text-gray-600">Encounter ID</span>
                <p className="font-mono text-gray-900">
                  {encounterId.slice(0, 16)}...
                </p>
              </div>
              <div>
                <span className="text-gray-600">Status</span>
                <p className="font-semibold text-gray-900 capitalize">
                  {reportData.status}
                </p>
              </div>
              {reportData.metadata?.processing_time_ms && (
                <div>
                  <span className="text-gray-600">Processing Time</span>
                  <p className="font-semibold text-gray-900">
                    {(reportData.metadata.processing_time_ms / 1000).toFixed(2)}s
                  </p>
                </div>
              )}
              {reportData.code_analysis?.ai_model && (
                <div>
                  <span className="text-gray-600">AI Model</span>
                  <p className="font-semibold text-gray-900">
                    {reportData.code_analysis.ai_model}
                  </p>
                </div>
              )}
              {reportData.code_analysis?.confidence_score !== undefined && (
                <div>
                  <span className="text-gray-600">Confidence Score</span>
                  <p className="font-semibold text-gray-900">
                    {Math.round(reportData.code_analysis.confidence_score * 100)}%
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Quick Actions
            </h3>
            <div className="space-y-2">
              <Link
                href="/encounters/new"
                className="block w-full px-4 py-2 bg-blue-600 text-white text-center rounded-lg hover:bg-blue-700 transition-colors"
              >
                Upload New Encounter
              </Link>
              <Link
                href="/encounters"
                className="block w-full px-4 py-2 border border-gray-300 text-gray-700 text-center rounded-lg hover:bg-gray-50 transition-colors"
              >
                View All Encounters
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

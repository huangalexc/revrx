'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import apiClient from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';
import {
  TrendingUp,
  DollarSign,
  FileText,
  Clock,
  ArrowUpRight,
  Calendar,
  BarChart3,
} from 'lucide-react';

interface SummaryData {
  date_range: {
    start: string;
    end: string;
    days: number;
  };
  overview: {
    total_encounters: number;
    total_incremental_revenue: number;
    average_revenue_per_encounter: number;
    average_processing_time_ms: number;
  };
  opportunities: {
    total_new_codes: number;
    total_upgrade_opportunities: number;
    total_opportunities: number;
  };
  chart_data: {
    labels: string[];
    datasets: {
      encounter_counts: number[];
      revenue: number[];
      new_codes: number[];
      upgrades: number[];
    };
  };
}

interface RecentEncounter {
  id: string;
  userId: string;
  status: string;
  processingTime?: number;
  createdAt: string;
  updatedAt: string;
  patientAge?: number;
  patientSex?: string;
  visitDate?: string;
  errorMessage?: string;
}

interface EncounterListResponse {
  encounters: RecentEncounter[];
  total: number;
  page: number;
  page_size: number;
}

interface CodeCategory {
  category: string;
  revenue: number;
  count: number;
  unique_codes: number;
}

export default function SummaryPage() {
  const [summaryData, setSummaryData] = useState<SummaryData | null>(null);
  const [recentEncounters, setRecentEncounters] = useState<RecentEncounter[]>([]);
  const [codeCategories, setCodeCategories] = useState<CodeCategory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeFilter, setTimeFilter] = useState('30'); // days

  const fetchSummary = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.get(API_ENDPOINTS.REPORTS.SUMMARY, {
        params: { days: timeFilter },
      });

      setSummaryData(response.data);
    } catch (err: any) {
      console.error('Failed to fetch summary:', err);
      console.error('Error details:', {
        code: err.code,
        message: err.message,
        response: err.response,
        request: err.request,
      });

      if (err.code === 'ERR_NETWORK' || err.message === 'Network Error') {
        setError('Cannot connect to the backend server. Please check browser console for details.');
      } else if (err.response?.status === 401) {
        setError('Authentication required. Please log in again.');
      } else {
        setError(err.response?.data?.detail || err.message || 'Failed to load summary data');
      }
    } finally {
      setIsLoading(false);
    }
  }, [timeFilter]);

  const fetchRecentEncounters = useCallback(async () => {
    try {
      const response = await apiClient.get<EncounterListResponse>(
        API_ENDPOINTS.ENCOUNTERS.LIST,
        {
          params: { page: 1, page_size: 5 },
        }
      );

      setRecentEncounters(response.data.encounters || []);
    } catch (err: any) {
      console.error('Failed to fetch recent encounters:', err);
    }
  }, []);

  const fetchCodeCategories = useCallback(async () => {
    try {
      const response = await apiClient.get<CodeCategory[]>(
        API_ENDPOINTS.REPORTS.CODE_CATEGORIES,
        {
          params: { days: timeFilter, limit: 5 },
        }
      );

      setCodeCategories(response.data || []);
    } catch (err: any) {
      console.error('Failed to fetch code categories:', err);
    }
  }, [timeFilter]);

  useEffect(() => {
    let cancelled = false;

    const loadData = async () => {
      if (!cancelled) {
        await fetchSummary();
        await fetchRecentEncounters();
        await fetchCodeCategories();
      }
    };

    loadData();

    return () => {
      cancelled = true;
    };
  }, [fetchSummary, fetchRecentEncounters, fetchCodeCategories]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            Revenue opportunities and performance metrics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={timeFilter}
            onChange={(e) => setTimeFilter(e.target.value)}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
            <option value="365">Last year</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Total Revenue */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
              <DollarSign className="w-6 h-6 text-green-600 dark:text-green-400" />
            </div>
            <TrendingUp className="w-5 h-5 text-green-600 dark:text-green-400" />
          </div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
            {formatCurrency(summaryData?.overview.total_incremental_revenue || 0)}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">Total Incremental Revenue</p>
        </div>

        {/* Average Revenue */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <BarChart3 className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
            {formatCurrency(summaryData?.overview.average_revenue_per_encounter || 0)}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">Avg per Encounter</p>
        </div>

        {/* Total Encounters */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
              <FileText className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
            {summaryData?.overview.total_encounters || 0}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">Total Encounters</p>
        </div>

        {/* Avg Processing Time */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
              <Clock className="w-6 h-6 text-orange-600 dark:text-orange-400" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
            {((summaryData?.overview.average_processing_time_ms || 0) / 1000).toFixed(1)}s
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">Avg Processing Time</p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Revenue Trend Chart Placeholder */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Revenue Trend
          </h3>
          <div className="h-64 flex items-center justify-center bg-gray-50 dark:bg-gray-900/50 rounded-lg">
            <p className="text-gray-500 dark:text-gray-400 text-sm">Chart will be implemented with Chart.js</p>
          </div>
        </div>

        {/* Top Code Categories */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Top Code Categories
          </h3>
          {codeCategories.length > 0 ? (
            <div className="space-y-4">
              {codeCategories.map((category, index) => {
                const maxRevenue = codeCategories[0]?.revenue || 1;
                const percentage = (category.revenue / maxRevenue) * 100;
                const colors = [
                  'bg-blue-600',
                  'bg-green-600',
                  'bg-purple-600',
                  'bg-orange-600',
                  'bg-pink-600',
                ];
                const barColor = colors[index % colors.length];

                return (
                  <div key={category.category}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        {category.category}
                        <span className="text-xs text-gray-500 dark:text-gray-400 ml-1">
                          ({category.count} codes)
                        </span>
                      </span>
                      <span className="text-sm font-semibold text-gray-900 dark:text-white">
                        {formatCurrency(category.revenue)}
                      </span>
                    </div>
                    <div className="h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${barColor}`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-12">
              <BarChart3 className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <p className="text-gray-600 dark:text-gray-400 text-sm">No code data available</p>
            </div>
          )}
        </div>
      </div>

      {/* Recent Encounters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Encounters</h3>
          <Link
            href="/encounters"
            className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 flex items-center gap-1"
          >
            View All
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>

        {recentEncounters && recentEncounters.length > 0 ? (
          <div className="space-y-4">
            {recentEncounters.map((encounter) => {
              const statusConfig = {
                PENDING: { label: 'Pending', color: 'text-yellow-600 bg-yellow-50' },
                PROCESSING: { label: 'Processing', color: 'text-blue-600 bg-blue-50' },
                COMPLETE: { label: 'Complete', color: 'text-green-600 bg-green-50' },
                FAILED: { label: 'Failed', color: 'text-red-600 bg-red-50' },
              };
              const status = statusConfig[encounter.status as keyof typeof statusConfig] || statusConfig.PENDING;

              return (
                <Link
                  key={encounter.id}
                  href={`/reports/${encounter.id}`}
                  className="flex items-center justify-between p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                      <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        Encounter #{encounter.id.slice(0, 8)}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {formatDate(encounter.createdAt)}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`text-xs font-medium px-2 py-1 rounded-full ${status.color}`}>
                      {status.label}
                    </div>
                    {encounter.processingTime && (
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {(encounter.processingTime / 1000).toFixed(1)}s
                      </div>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">No encounters yet</p>
            <Link
              href="/encounters/new"
              className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-blue-600 dark:bg-blue-700 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors"
            >
              Create First Encounter
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

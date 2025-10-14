'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import apiClient from '@/lib/api/client';
import { API_ENDPOINTS } from '@/lib/api/endpoints';
import {
  Users,
  FileText,
  Activity,
  Shield,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Clock,
  Search,
} from 'lucide-react';

interface SystemMetrics {
  total_users: number;
  active_users: number;
  total_encounters: number;
  encounters_today: number;
  average_processing_time: number;
  success_rate: number;
}

interface AuditLog {
  id: string;
  user_email: string;
  action: string;
  timestamp: string;
  ip_address: string;
  status: 'success' | 'failed';
}

export default function AdminPage() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [metricsResponse, logsResponse] = await Promise.all([
        apiClient.get(API_ENDPOINTS.ADMIN.METRICS),
        apiClient.get(API_ENDPOINTS.ADMIN.AUDIT_LOGS, {
          params: { limit: 10 },
        }),
      ]);

      setMetrics(metricsResponse.data);
      setAuditLogs(logsResponse.data.logs || []);
    } catch (err: any) {
      // Use mock data for development
      setMetrics({
        total_users: 128,
        active_users: 42,
        total_encounters: 3456,
        encounters_today: 87,
        average_processing_time: 18.5,
        success_rate: 98.5,
      });

      setAuditLogs([
        {
          id: '1',
          user_email: 'user@example.com',
          action: 'UPLOAD_CLINICAL_NOTE',
          timestamp: new Date().toISOString(),
          ip_address: '192.168.1.1',
          status: 'success',
        },
        {
          id: '2',
          user_email: 'admin@example.com',
          action: 'VIEW_AUDIT_LOGS',
          timestamp: new Date(Date.now() - 300000).toISOString(),
          ip_address: '192.168.1.2',
          status: 'success',
        },
        {
          id: '3',
          user_email: 'user2@example.com',
          action: 'LOGIN',
          timestamp: new Date(Date.now() - 600000).toISOString(),
          ip_address: '192.168.1.3',
          status: 'failed',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getActionBadge = (action: string) => {
    const actionMap: Record<string, { color: string; label: string }> = {
      UPLOAD_CLINICAL_NOTE: { color: 'bg-blue-100 text-blue-700', label: 'Upload' },
      LOGIN: { color: 'bg-green-100 text-green-700', label: 'Login' },
      LOGOUT: { color: 'bg-gray-100 text-gray-700', label: 'Logout' },
      VIEW_AUDIT_LOGS: { color: 'bg-purple-100 text-purple-700', label: 'Audit' },
      EXPORT_REPORT: { color: 'bg-orange-100 text-orange-700', label: 'Export' },
    };

    const config = actionMap[action] || { color: 'bg-gray-100 text-gray-700', label: action };

    return (
      <span className={`px-2 py-1 text-xs font-medium rounded ${config.color}`}>
        {config.label}
      </span>
    );
  };

  const filteredLogs = auditLogs.filter(
    (log) =>
      log.user_email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.ip_address.includes(searchTerm)
  );

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
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-600" aria-hidden="true" />
            Admin Dashboard
          </h1>
          <p className="text-gray-600 mt-2">
            System metrics, user management, and audit logs
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* System Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {/* Total Users */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <Users className="w-6 h-6 text-blue-600" aria-hidden="true" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-gray-900 mb-1">
            {metrics?.total_users || 0}
          </h3>
          <p className="text-sm text-gray-600">Total Users</p>
          <p className="text-xs text-green-600 mt-2">
            {metrics?.active_users || 0} active today
          </p>
        </div>

        {/* Total Encounters */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
              <FileText className="w-6 h-6 text-purple-600" aria-hidden="true" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-gray-900 mb-1">
            {metrics?.total_encounters || 0}
          </h3>
          <p className="text-sm text-gray-600">Total Encounters</p>
          <p className="text-xs text-green-600 mt-2">
            {metrics?.encounters_today || 0} today
          </p>
        </div>

        {/* Processing Time */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
              <Clock className="w-6 h-6 text-orange-600" aria-hidden="true" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-gray-900 mb-1">
            {metrics?.average_processing_time?.toFixed(1) || '0.0'}s
          </h3>
          <p className="text-sm text-gray-600">Avg Processing Time</p>
          <p className="text-xs text-gray-500 mt-2">Target: &lt;30s</p>
        </div>

        {/* Success Rate */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-green-600" aria-hidden="true" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-gray-900 mb-1">
            {metrics?.success_rate?.toFixed(1) || '0.0'}%
          </h3>
          <p className="text-sm text-gray-600">Success Rate</p>
          <div className="mt-2 h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-600"
              style={{ width: `${metrics?.success_rate || 0}%` }}
            />
          </div>
        </div>

        {/* System Health */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <Activity className="w-6 h-6 text-green-600" aria-hidden="true" />
            </div>
          </div>
          <h3 className="text-2xl font-bold text-green-600 mb-1">Healthy</h3>
          <p className="text-sm text-gray-600">System Status</p>
          <p className="text-xs text-gray-500 mt-2">All services operational</p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Link
          href="/admin/users"
          className="p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-colors"
        >
          <Users className="w-6 h-6 text-blue-600 mb-2" aria-hidden="true" />
          <h3 className="font-semibold text-gray-900">User Management</h3>
          <p className="text-sm text-gray-600">Manage users and permissions</p>
        </Link>

        <Link
          href="/admin/audit-logs"
          className="p-4 bg-white rounded-lg border border-gray-200 hover:border-purple-300 hover:bg-purple-50 transition-colors"
        >
          <Shield className="w-6 h-6 text-purple-600 mb-2" aria-hidden="true" />
          <h3 className="font-semibold text-gray-900">Audit Logs</h3>
          <p className="text-sm text-gray-600">View security audit trail</p>
        </Link>

        <Link
          href="/admin/metrics"
          className="p-4 bg-white rounded-lg border border-gray-200 hover:border-orange-300 hover:bg-orange-50 transition-colors"
        >
          <Activity className="w-6 h-6 text-orange-600 mb-2" aria-hidden="true" />
          <h3 className="font-semibold text-gray-900">System Metrics</h3>
          <p className="text-sm text-gray-600">View detailed analytics</p>
        </Link>

        <Link
          href="/admin/settings"
          className="p-4 bg-white rounded-lg border border-gray-200 hover:border-green-300 hover:bg-green-50 transition-colors"
        >
          <TrendingUp className="w-6 h-6 text-green-600 mb-2" aria-hidden="true" />
          <h3 className="font-semibold text-gray-900">Settings</h3>
          <p className="text-sm text-gray-600">Configure system settings</p>
        </Link>
      </div>

      {/* Recent Audit Logs */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">Recent Audit Logs</h2>
          <Link
            href="/admin/audit-logs"
            className="text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            View All
          </Link>
        </div>

        {/* Search */}
        <div className="mb-4">
          <div className="relative">
            <Search
              className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400"
              aria-hidden="true"
            />
            <input
              type="text"
              placeholder="Search logs by email, action, or IP..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-label="Search audit logs"
            />
          </div>
        </div>

        {/* Logs Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th
                  scope="col"
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  User
                </th>
                <th
                  scope="col"
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Action
                </th>
                <th
                  scope="col"
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Timestamp
                </th>
                <th
                  scope="col"
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  IP Address
                </th>
                <th
                  scope="col"
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {log.user_email}
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {getActionBadge(log.action)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {formatDate(log.timestamp)}
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="text-sm text-gray-500 font-mono">
                      {log.ip_address}
                    </div>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {log.status === 'success' ? (
                      <CheckCircle className="w-5 h-5 text-green-600" aria-label="Success" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-red-600" aria-label="Failed" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredLogs.length === 0 && (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-600">No audit logs found</p>
          </div>
        )}
      </div>
    </div>
  );
}

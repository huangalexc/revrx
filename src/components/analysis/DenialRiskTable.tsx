'use client';

import { useState, useMemo } from 'react';
import {
  AlertTriangle,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Filter,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from 'lucide-react';
import { DenialRisk } from '@/types/analysis';

interface DenialRiskTableProps {
  denialRisks: DenialRisk[];
}

type RiskLevel = 'Low' | 'Medium' | 'High' | 'All';
type SortField = 'code' | 'risk_level';
type SortOrder = 'asc' | 'desc';

const riskLevelConfig = {
  High: {
    color: 'text-red-700',
    bg: 'bg-red-50',
    border: 'border-red-200',
    badge: 'bg-red-100 text-red-700 border-red-200',
    icon: XCircle,
    iconColor: 'text-red-600',
  },
  Medium: {
    color: 'text-yellow-700',
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    badge: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    icon: AlertTriangle,
    iconColor: 'text-yellow-600',
  },
  Low: {
    color: 'text-green-700',
    bg: 'bg-green-50',
    border: 'border-green-200',
    badge: 'bg-green-100 text-green-700 border-green-200',
    icon: ShieldCheck,
    iconColor: 'text-green-600',
  },
};

export default function DenialRiskTable({ denialRisks }: DenialRiskTableProps) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [filterRiskLevel, setFilterRiskLevel] = useState<RiskLevel>('All');
  const [showOnlyHighRisk, setShowOnlyHighRisk] = useState(false);
  const [sortField, setSortField] = useState<SortField>('risk_level');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  // Toggle row expansion
  const toggleRow = (code: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(code)) {
      newExpanded.delete(code);
    } else {
      newExpanded.add(code);
    }
    setExpandedRows(newExpanded);
  };

  // Filter and sort data
  const filteredAndSortedRisks = useMemo(() => {
    let filtered = [...denialRisks];

    // Apply filters
    if (showOnlyHighRisk) {
      filtered = filtered.filter((risk) => risk.risk_level === 'High');
    } else if (filterRiskLevel !== 'All') {
      filtered = filtered.filter((risk) => risk.risk_level === filterRiskLevel);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      if (sortField === 'code') {
        const comparison = a.code.localeCompare(b.code);
        return sortOrder === 'asc' ? comparison : -comparison;
      } else {
        // Sort by risk level: High > Medium > Low
        const riskOrder = { High: 3, Medium: 2, Low: 1 };
        const comparison =
          riskOrder[a.risk_level] - riskOrder[b.risk_level];
        return sortOrder === 'asc' ? comparison : -comparison;
      }
    });

    return filtered;
  }, [denialRisks, filterRiskLevel, showOnlyHighRisk, sortField, sortOrder]);

  // Handle sort
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  // Empty state
  if (!denialRisks || denialRisks.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <ShieldCheck className="w-5 h-5 text-green-600" />
          <h2 className="text-xl font-semibold text-gray-900">Denial Risk Analysis</h2>
        </div>
        <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
          <ShieldCheck className="w-8 h-8 text-green-600 flex-shrink-0" />
          <div>
            <p className="font-medium text-green-900">Low Denial Risk</p>
            <p className="text-sm text-green-700">
              All codes appear to be well-documented and supported by the clinical note.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Calculate risk summary
  const riskSummary = {
    high: denialRisks.filter((r) => r.risk_level === 'High').length,
    medium: denialRisks.filter((r) => r.risk_level === 'Medium').length,
    low: denialRisks.filter((r) => r.risk_level === 'Low').length,
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <ShieldAlert className="w-5 h-5 text-blue-600" />
        <h2 className="text-xl font-semibold text-gray-900">Denial Risk Analysis</h2>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-red-900">High Risk</span>
            <span className="text-2xl font-bold text-red-700">{riskSummary.high}</span>
          </div>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-yellow-900">Medium Risk</span>
            <span className="text-2xl font-bold text-yellow-700">{riskSummary.medium}</span>
          </div>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-green-900">Low Risk</span>
            <span className="text-2xl font-bold text-green-700">{riskSummary.low}</span>
          </div>
        </div>
      </div>

      {/* Filters and Controls */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        {/* Risk Level Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500" />
          <select
            value={filterRiskLevel}
            onChange={(e) => {
              setFilterRiskLevel(e.target.value as RiskLevel);
              setShowOnlyHighRisk(false);
            }}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="All">All Risk Levels</option>
            <option value="High">High Risk Only</option>
            <option value="Medium">Medium Risk Only</option>
            <option value="Low">Low Risk Only</option>
          </select>
        </div>

        {/* High Risk Toggle */}
        {riskSummary.high > 0 && (
          <button
            onClick={() => {
              setShowOnlyHighRisk(!showOnlyHighRisk);
              if (!showOnlyHighRisk) setFilterRiskLevel('All');
            }}
            className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
              showOnlyHighRisk
                ? 'bg-red-100 text-red-700 border border-red-300'
                : 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200'
            }`}
          >
            {showOnlyHighRisk ? '✓ ' : ''}Show High Risk Only
          </button>
        )}

        <div className="flex-1" />

        {/* Results count */}
        <div className="text-sm text-gray-600 flex items-center">
          Showing {filteredAndSortedRisks.length} of {denialRisks.length} codes
        </div>
      </div>

      {/* Table - Desktop */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-3 px-4">
                <button
                  onClick={() => handleSort('code')}
                  className="flex items-center gap-1 font-semibold text-gray-900 hover:text-blue-600"
                >
                  Code
                  {sortField === 'code' && (
                    sortOrder === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
                  )}
                </button>
              </th>
              <th className="text-left py-3 px-4">
                <button
                  onClick={() => handleSort('risk_level')}
                  className="flex items-center gap-1 font-semibold text-gray-900 hover:text-blue-600"
                >
                  Risk Level
                  {sortField === 'risk_level' && (
                    sortOrder === 'asc' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />
                  )}
                </button>
              </th>
              <th className="text-left py-3 px-4 font-semibold text-gray-900">
                Status
              </th>
              <th className="text-left py-3 px-4 font-semibold text-gray-900">
                Denial Reasons
              </th>
              <th className="w-12"></th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedRisks.map((risk) => (
              <DenialRiskRow
                key={risk.code}
                risk={risk}
                isExpanded={expandedRows.has(risk.code)}
                onToggle={() => toggleRow(risk.code)}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* Cards - Mobile */}
      <div className="md:hidden space-y-3">
        {filteredAndSortedRisks.map((risk) => (
          <DenialRiskCard
            key={risk.code}
            risk={risk}
            isExpanded={expandedRows.has(risk.code)}
            onToggle={() => toggleRow(risk.code)}
          />
        ))}
      </div>

      {/* No results */}
      {filteredAndSortedRisks.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <Filter className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No codes match the selected filters</p>
        </div>
      )}
    </div>
  );
}

function DenialRiskRow({
  risk,
  isExpanded,
  onToggle,
}: {
  risk: DenialRisk;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const config = riskLevelConfig[risk.risk_level];
  const Icon = config.icon;

  return (
    <>
      <tr
        className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors"
        onClick={onToggle}
      >
        <td className="py-3 px-4">
          <span className="font-mono font-semibold text-gray-900">{risk.code}</span>
        </td>
        <td className="py-3 px-4">
          <div className="flex items-center gap-2">
            <Icon className={`w-4 h-4 ${config.iconColor}`} />
            <span className={`px-2 py-0.5 text-xs font-medium rounded border ${config.badge}`}>
              {risk.risk_level}
            </span>
          </div>
        </td>
        <td className="py-3 px-4">
          {risk.documentation_addresses_risks ? (
            <div className="flex items-center gap-1 text-green-700">
              <CheckCircle className="w-4 h-4" />
              <span className="text-sm">Addressed</span>
            </div>
          ) : (
            <div className="flex items-center gap-1 text-red-700">
              <XCircle className="w-4 h-4" />
              <span className="text-sm">Not Addressed</span>
            </div>
          )}
        </td>
        <td className="py-3 px-4">
          <span className="text-sm text-gray-600">
            {risk.denial_reasons.length} reason{risk.denial_reasons.length !== 1 ? 's' : ''}
          </span>
        </td>
        <td className="py-3 px-4 text-right">
          {isExpanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </td>
      </tr>
      {isExpanded && (
        <tr>
          <td colSpan={5} className={`${config.bg} border-b border-gray-100`}>
            <div className="p-4 space-y-3">
              {/* Denial Reasons */}
              <div>
                <h4 className="text-sm font-semibold text-gray-900 mb-2">
                  Common Denial Reasons:
                </h4>
                <ul className="list-disc list-inside space-y-1">
                  {risk.denial_reasons.map((reason, idx) => (
                    <li key={idx} className="text-sm text-gray-700">
                      {reason}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Mitigation Notes */}
              <div className="bg-white border border-gray-200 rounded p-3">
                <h4 className="text-sm font-semibold text-gray-900 mb-1">
                  Mitigation Strategy:
                </h4>
                <p className="text-sm text-gray-700">{risk.mitigation_notes}</p>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function DenialRiskCard({
  risk,
  isExpanded,
  onToggle,
}: {
  risk: DenialRisk;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const config = riskLevelConfig[risk.risk_level];
  const Icon = config.icon;

  return (
    <div
      className={`border ${config.border} rounded-lg overflow-hidden cursor-pointer transition-shadow hover:shadow-md`}
      onClick={onToggle}
    >
      {/* Card Header */}
      <div className={`${config.bg} p-4`}>
        <div className="flex items-start justify-between mb-2">
          <span className="font-mono font-semibold text-gray-900">{risk.code}</span>
          {isExpanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400 flex-shrink-0" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400 flex-shrink-0" />
          )}
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon className={`w-4 h-4 ${config.iconColor}`} />
            <span className={`px-2 py-0.5 text-xs font-medium rounded border ${config.badge}`}>
              {risk.risk_level}
            </span>
          </div>
          {risk.documentation_addresses_risks ? (
            <div className="flex items-center gap-1 text-green-700">
              <CheckCircle className="w-4 h-4" />
              <span className="text-xs">Addressed</span>
            </div>
          ) : (
            <div className="flex items-center gap-1 text-red-700">
              <XCircle className="w-4 h-4" />
              <span className="text-xs">Not Addressed</span>
            </div>
          )}
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="bg-white p-4 space-y-3 border-t border-gray-200">
          {/* Denial Reasons */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-2">
              Common Denial Reasons:
            </h4>
            <ul className="list-disc list-inside space-y-1">
              {risk.denial_reasons.map((reason, idx) => (
                <li key={idx} className="text-sm text-gray-700">
                  {reason}
                </li>
              ))}
            </ul>
          </div>

          {/* Mitigation Notes */}
          <div className={`${config.bg} border ${config.border} rounded p-3`}>
            <h4 className="text-sm font-semibold text-gray-900 mb-1">
              Mitigation Strategy:
            </h4>
            <p className="text-sm text-gray-700">{risk.mitigation_notes}</p>
          </div>
        </div>
      )}
    </div>
  );
}

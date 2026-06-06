'use client';

import { useState } from 'react';
import {
  ChevronDown,
  ChevronUp,
  CheckCircle,
  AlertTriangle,
  XCircle,
  FileSpreadsheet,
} from 'lucide-react';
import type { ValidatePreviewDoctype } from '@/lib/api/implementation_api';
import { friendlyRuleMessage } from '@/lib/copy/gate-copy';

interface Props {
  data: ValidatePreviewDoctype;
  defaultOpen?: boolean;
}

const METHOD_LABELS: Record<string, string> = {
  exact_match: 'KB exact',
  fuzzy_match: 'KB fuzzy',
  llm_inferred: 'LLM',
  user_confirmed: 'User confirmed',
  historical_match: 'Historical',
};

const STATUS_CONFIG: Record<string, { label: string; icon: typeof CheckCircle; color: string; bg: string }> = {
  passed: { label: 'Passed', icon: CheckCircle, color: 'text-emerald-400', bg: 'border-emerald-500/20' },
  pass:   { label: 'Passed', icon: CheckCircle, color: 'text-emerald-400', bg: 'border-emerald-500/20' },
  partial:{ label: 'Passed with warnings', icon: AlertTriangle, color: 'text-amber-400', bg: 'border-amber-500/20' },
  passed_with_warnings: { label: 'Passed with warnings', icon: AlertTriangle, color: 'text-amber-400', bg: 'border-amber-500/20' },
  failed: { label: 'Failed', icon: XCircle,     color: 'text-red-400',     bg: 'border-red-500/20' },
  fail:   { label: 'Failed', icon: XCircle,     color: 'text-red-400',     bg: 'border-red-500/20' },
  pending:{ label: 'Pending',icon: AlertTriangle,color: 'text-yellow-400', bg: 'border-yellow-500/20' },
};

export function DataPreviewTable({ data, defaultOpen = false }: Props) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [visibleRows, setVisibleRows] = useState(10);

  const status = STATUS_CONFIG[data.validation_status] ?? STATUS_CONFIG.pending;
  const StatusIcon = status.icon;

  const hasMore = data.records.length > visibleRows;

  const renderCellValue = (value: unknown) => {
    if (value == null || value === '') {
      return <span className="text-gray-700 italic">—</span>;
    }

    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
      return String(value);
    }

    if (Array.isArray(value)) {
      if (!value.length) {
        return <span className="text-gray-500 italic">[]</span>;
      }
      const preview = value.slice(0, 2).map((item) => {
        if (item == null) return '—';
        if (typeof item === 'string' || typeof item === 'number' || typeof item === 'boolean') return String(item);
        if (typeof item === 'object') {
          const rec = item as Record<string, unknown>;
          const label = rec.item_code ?? rec.name ?? rec.doctype ?? rec.fieldname;
          const qty = rec.qty ?? rec.quantity;
          const uom = rec.uom ?? rec.stock_uom;
          const pieces = [label, qty != null ? `x ${qty}` : null, uom].filter(Boolean);
          if (pieces.length > 0) return pieces.join(' ');
          try {
            return JSON.stringify(item);
          } catch {
            return '[object Object]';
          }
        }
        return String(item);
      }).join(', ');
      return `${value.length} item${value.length !== 1 ? 's' : ''}${preview ? `: ${preview}${value.length > 2 ? '…' : ''}` : ''}`;
    }

    if (typeof value === 'object') {
      try {
        const json = JSON.stringify(value);
        return json.length > 120 ? `${json.slice(0, 117)}…` : json;
      } catch {
        return String(value);
      }
    }

    return String(value);
  };

  return (
    <div className={`rounded-2xl border border-white/[0.07] bg-white/[0.02] overflow-hidden transition-all duration-300 ${status.bg}`}>
      {/* Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-4 px-5 py-4 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center flex-shrink-0">
          <FileSpreadsheet className="w-4 h-4 text-amber-400" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2.5">
            <h3 className="text-sm font-bold text-white">{data.doctype}</h3>
            <span className="text-[10px] font-mono bg-white/[0.06] text-gray-400 px-2 py-0.5 rounded-full">
              {data.total_rows} row{data.total_rows !== 1 ? 's' : ''}
            </span>
            <span className="text-[10px] font-mono bg-white/[0.06] text-gray-400 px-2 py-0.5 rounded-full">
              {data.columns.length} field{data.columns.length !== 1 ? 's' : ''}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-0.5">
            {data.source_file && (
              <p className="text-[11px] text-gray-600 truncate">
                Source: {data.source_file}
              </p>
            )}
            {data.classification?.primary_method && (
              <span
                className="text-[10px] font-mono bg-violet-500/10 text-violet-300 border border-violet-500/20 px-2 py-0.5 rounded-full"
                title={
                  Object.entries(data.classification.method_counts || {})
                    .map(([k, v]) => `${METHOD_LABELS[k] || k}: ${v}`)
                    .join(', ') || undefined
                }
              >
                Map: {METHOD_LABELS[data.classification.primary_method] || data.classification.primary_method}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <StatusIcon className={`w-4 h-4 ${status.color}`} />
          <span className={`text-[10px] font-bold uppercase tracking-wider ${status.color}`}>
            {status.label}
          </span>
        </div>

        {isOpen
          ? <ChevronUp className="w-4 h-4 text-gray-600 flex-shrink-0" />
          : <ChevronDown className="w-4 h-4 text-gray-600 flex-shrink-0" />
        }
      </button>

      {/* Expanded content */}
      {isOpen && (
        <div className="border-t border-white/[0.06]">
          {/* Errors / Warnings */}
          {(data.errors.length > 0 || data.warnings.length > 0) && (
            <div className={`px-5 py-3 space-y-1.5 border-b border-white/[0.06] ${
              data.errors.length > 0 ? 'bg-red-500/[0.03]' : 'bg-amber-500/[0.03]'
            }`}>
              {data.errors.map((e, i) => (
                <div key={`err-${i}`} className="flex items-start gap-2 text-xs">
                  <XCircle className="w-3.5 h-3.5 text-red-400 mt-0.5 flex-shrink-0" />
                  <span className="text-red-300" title={e.rule_id ? `Rule: ${e.rule_id}` : undefined}>
                    <span className="font-semibold text-red-400">{e.field}:</span>{' '}
                    {friendlyRuleMessage(e.rule_id, e.message)}
                  </span>
                </div>
              ))}
              {data.warnings.map((w, i) => (
                <div key={`warn-${i}`} className="flex items-start gap-2 text-xs">
                  <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 mt-0.5 flex-shrink-0" />
                  <span className="text-yellow-300">
                    <span className="font-semibold text-yellow-400">{w.field}:</span> {w.message}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Data Table */}
          {data.records.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-white/[0.08]">
                    <th className="px-4 py-2.5 text-left text-[10px] font-bold uppercase tracking-widest text-gray-600 bg-white/[0.02] w-10">
                      #
                    </th>
                    {data.columns.map((col) => (
                      <th
                        key={col}
                        className="px-4 py-2.5 text-left text-[10px] font-bold uppercase tracking-widest text-gray-600 bg-white/[0.02] whitespace-nowrap"
                      >
                        {col.replace(/_/g, ' ')}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.records.slice(0, visibleRows).map((row, rowIdx) => (
                    <tr
                      key={rowIdx}
                      className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors"
                    >
                      <td className="px-4 py-2 text-gray-700 font-mono">{rowIdx + 1}</td>
                      {data.columns.map((col) => (
                        <td key={col} className="px-4 py-2 text-gray-300 whitespace-nowrap max-w-[200px] truncate">
                          {renderCellValue(row[col])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Show more / less */}
              {(hasMore || visibleRows > 10) && (
                <div className="px-5 py-2.5 border-t border-white/[0.06] flex items-center justify-between">
                  <span className="text-[11px] text-gray-600">
                    Showing {Math.min(visibleRows, data.records.length)} of {data.records.length} records
                  </span>
                  <div className="flex gap-2">
                    {hasMore && (
                      <button
                        onClick={() => setVisibleRows((v) => v + 20)}
                        className="text-[11px] font-bold text-amber-500 hover:text-amber-400 transition-colors"
                      >
                        Show more ↓
                      </button>
                    )}
                    {visibleRows > 10 && (
                      <button
                        onClick={() => setVisibleRows(10)}
                        className="text-[11px] font-bold text-gray-500 hover:text-gray-400 transition-colors"
                      >
                        Collapse
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="px-5 py-6 text-center text-xs text-gray-600">
              No records available — payload could not be loaded from storage.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

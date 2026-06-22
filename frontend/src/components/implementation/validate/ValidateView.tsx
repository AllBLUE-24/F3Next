'use client';

// src/components/implementation/validate/ValidateView.tsx
// Full data review + confirm before import

import { useState, useTransition, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowRight,
  Shield,
  CheckCircle,
  Database,
  Layers,
  Package,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { DataPreviewTable } from './DataPreviewTable';
import type { ValidatePreviewData } from '@/lib/api/implementation_api';
import { getBaseApiUrl } from '@/lib/config';
import { stageToStep } from '@/lib/implementation-routes';
import { friendlyRuleMessage } from '@/lib/copy/gate-copy';

interface Props {
  jobId: string;
  preview: ValidatePreviewData;
  submitValidation: (formData: FormData) => Promise<void>;
  importHref: string;
  companySlug: string;
}

const PHASE_LABELS: Record<string, { label: string; icon: typeof Package }> = {
  phase_a_config:        { label: 'Phase A — Configuration', icon: Layers },
  phase_b_master:        { label: 'Phase B — Master Data',   icon: Database },
  phase_c_transactional: { label: 'Phase C — Transactions',  icon: Package },
};

export function ValidateView({ jobId, preview, submitValidation, importHref, companySlug }: Props) {
  const [alreadyConfirmed, setAlreadyConfirmed] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  // Sync with workflow stage — confirm state, errors, import progress
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${getBaseApiUrl()}/api/implementation/stage/${jobId}`, {
          cache: 'no-store',
        });
        if (!res.ok || cancelled) return;
        const data = await res.json();
        const stage = data.stage as string | null;
        const step = stageToStep(stage);
        if (step === 'import') {
          setAlreadyConfirmed(true);
        }
        if (stage === 'error' || stage === 'import_blocked') {
          setSubmitError(
            stage === 'import_blocked'
              ? 'Import is blocked — upload missing MVP files or fix validation errors, then try again.'
              : 'The workflow hit an error after validation. Check worker logs or start a fresh session.',
          );
        }
      } catch {
        // keep default
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  const profile = preview.profile;
  const totalRecords = preview.doctypes.reduce((s, d) => s + d.total_rows, 0);
  const totalDoctypes = preview.doctypes.length;
  const errorCount = preview.doctypes.reduce((s, d) => s + (d.errors?.length || 0), 0);
  const warningCount = preview.doctypes.reduce((s, d) => s + (d.warnings?.length || 0), 0);
  const failedDoctypes = preview.doctypes.filter((d) =>
    ['fail', 'failed'].includes(d.validation_status),
  ).length;
  const hasErrors = preview.validation_overall === 'fail' || failedDoctypes > 0;
  const hasWarnings = preview.validation_overall === 'partial' || warningCount > 0;
  const blockingUnmapped = preview.blocking_unmapped_seeds ?? [];
  const importBlocked =
    !preview.import_ready ||
    (preview.open_critical_gaps ?? 0) > 0 ||
    blockingUnmapped.length > 0;
  const canConfirm = !hasErrors && !importBlocked;

  const dataQualityLabel = (() => {
    const raw = profile.data_quality_score;
    if (raw == null) return '—';
    const pct = Math.round(Number(raw) * 100);
    if (profile.data_quality_capped) return `${pct}% (capped — validation warnings)`;
    return `${pct}%`;
  })();

  const handleConfirmImport = () => {
    setSubmitError(null);
    startTransition(async () => {
      if (!alreadyConfirmed) {
        const formData = new FormData();
        formData.append('jobId', jobId);
        formData.append('companySlug', companySlug);
        formData.append('responses', JSON.stringify({}));
        formData.append('profileEdits', JSON.stringify({}));
        formData.append('note', '');
        try {
          await submitValidation(formData);
        } catch (e) {
          setSubmitError(e instanceof Error ? e.message : 'Validation submit failed');
          return;
        }
      }
      router.push(importHref);
    });
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-500 mb-2">
          Step 03 of 04
        </p>
        <h1 className="text-3xl font-black text-white mb-3">
          Review your data.
        </h1>
        <p className="text-gray-500 text-base leading-relaxed">
          Here's everything we extracted from your files. Review each section below —
          this is exactly what will be imported into your ERPNext instance.
        </p>
      </div>

      {/* Stats bar */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2 bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-2.5">
          <Database className="w-4 h-4 text-amber-400" />
          <span className="text-xs font-bold text-white">{totalDoctypes}</span>
          <span className="text-xs text-gray-500">doctypes</span>
        </div>
        <div className="flex items-center gap-2 bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-2.5">
          <Layers className="w-4 h-4 text-amber-400" />
          <span className="text-xs font-bold text-white">{totalRecords}</span>
          <span className="text-xs text-gray-500">total records</span>
        </div>
        <div className="flex items-center gap-2 bg-white/[0.04] border border-white/[0.08] rounded-xl px-4 py-2.5">
          {hasErrors ? (
            <AlertTriangle className="w-4 h-4 text-red-400" />
          ) : hasWarnings ? (
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          ) : (
            <CheckCircle className="w-4 h-4 text-emerald-400" />
          )}
          <span className={`text-xs font-bold ${
            hasErrors ? 'text-red-400' : hasWarnings ? 'text-amber-400' : 'text-emerald-400'
          }`}>
            {hasErrors
              ? `Failed (${failedDoctypes} doctype${failedDoctypes !== 1 ? 's' : ''}, ${errorCount} error${errorCount !== 1 ? 's' : ''})`
              : hasWarnings
                ? `Passed with warnings (${warningCount})`
                : 'All Passed'}
          </span>
        </div>
      </div>

      {/* ── Company Profile Card ──────────────────────────────────────────────── */}
      <div className="bg-white/[0.02] border border-white/[0.07] rounded-2xl p-6 space-y-5">
        <h2 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
          <Shield className="w-4 h-4 text-amber-400" />
          Company Profile
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[
            { label: 'Company', value: String(profile.company_name || '—') },
            { label: 'Industry', value: String(profile.industry || '—') },
            { label: 'F3iche', value: String(profile.f3iche || '—') },
            { label: 'Business Size', value: String(profile.company_size || '—') },
            { label: 'Sub-Industry', value: String(profile.industry_sub || '—') },
            { label: 'Data Quality', value: dataQualityLabel },
          ].map((item) => (
            <div key={item.label}>
              <p className="text-[10px] uppercase tracking-widest text-gray-700 mb-1">{item.label}</p>
              <p className="text-sm text-white font-medium">{item.value}</p>
            </div>
          ))}
        </div>

        {Array.isArray(profile.modules) && profile.modules.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-widest text-gray-700 mb-2">Detected Modules</p>
            <div className="flex flex-wrap gap-2">
              {(profile.modules as string[]).map((m) => (
                <span key={m} className="text-xs bg-amber-500/10 border border-amber-500/20 text-amber-400 px-2.5 py-1 rounded-full font-medium">
                  {m}
                </span>
              ))}
            </div>
          </div>
        )}

        {Array.isArray(profile.required_doctypes) && (profile.required_doctypes as string[]).length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-widest text-gray-700 mb-2">Target Doctypes</p>
            <div className="flex flex-wrap gap-1.5">
              {(profile.required_doctypes as string[]).map((d) => (
                <span key={d} className="text-[11px] bg-white/[0.05] border border-white/[0.08] text-gray-400 px-2 py-0.5 rounded-md font-mono">
                  {d}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Data Tables ──────────────────────────────────────────────────────── */}
      <div className="space-y-4">
        <h2 className="text-sm font-bold text-white uppercase tracking-widest">
          Data Preview — {totalDoctypes} Doctypes
        </h2>
        {preview.doctypes.map((dt, idx) => (
          <DataPreviewTable key={`${dt.doctype}-${dt.source_file ?? idx}`} data={dt} defaultOpen={idx === 0} />
        ))}

        {(preview.unmapped_files?.length ?? 0) > 0 && (
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-2xl p-5 space-y-3">
            <h3 className="text-xs font-bold text-amber-400 uppercase tracking-widest flex items-center gap-2">
              <AlertTriangle className="w-3.5 h-3.5" />
              Uploaded but not mapped — {(preview.tracked_files?.length ?? 0) || preview.unmapped_files!.length + totalDoctypes} files tracked
            </h3>
            <ul className="space-y-2">
              {preview.unmapped_files!.map((f) => (
                <li key={f.filename} className="text-xs text-amber-200/80 font-mono">
                  {f.filename}
                  <span className="text-amber-400/60 font-sans ml-2">— mapping skipped or failed preflight</span>
                </li>
              ))}
            </ul>
            {(preview.mapping_gaps?.length ?? 0) > 0 && (
              <ul className="space-y-1 pt-2 border-t border-amber-500/10">
                {preview.mapping_gaps!.map((gap, i) => (
                  <li key={`${gap.source_file}-${gap.doctype}-${i}`} className="text-[11px] text-amber-300/70">
                    {gap.message}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {/* ── Import Plan Summary ──────────────────────────────────────────────── */}
      {Object.keys(preview.import_summary).length > 0 && (
        <div className="bg-white/[0.02] border border-white/[0.07] rounded-2xl p-6 space-y-4">
          <h2 className="text-sm font-bold text-white uppercase tracking-widest">
            Import Plan — 3 Phases
          </h2>
          <div className="space-y-3">
            {Object.entries(preview.import_summary).map(([phaseKey, doctypes]) => {
              const cfg = PHASE_LABELS[phaseKey] || { label: phaseKey, icon: Package };
              const Icon = cfg.icon;
              return (
                <div key={phaseKey} className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Icon className="w-3.5 h-3.5 text-amber-400" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-white">{cfg.label}</p>
                    <p className="text-[11px] text-gray-500 mt-0.5">
                      {(doctypes as string[]).join(' → ')}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Action ─────────────────────────────────────────────────────────── */}
      <div className="space-y-3">
        {alreadyConfirmed && (
          <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-5 py-4">
            <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0" />
            <div>
              <p className="text-sm font-bold text-emerald-400">Data confirmed</p>
              <p className="text-xs text-emerald-300/70 mt-0.5">
                Validation was submitted. Continue to the import step.
              </p>
            </div>
          </div>
        )}

        {!alreadyConfirmed && hasErrors && (
          <p className="text-xs text-red-400 font-medium flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" />
            Validation failed for {failedDoctypes} doctype{failedDoctypes !== 1 ? 's' : ''}.
            Fix errors below before starting import.
          </p>
        )}
        {!alreadyConfirmed && hasWarnings && !hasErrors && !importBlocked && (
          <p className="text-xs text-amber-500 font-medium flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" />
            Some doctypes passed with warnings. Review amber sections before import.
          </p>
        )}

        {!alreadyConfirmed && importBlocked && !hasErrors && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 space-y-1">
            <p className="text-xs text-red-400 font-medium flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" />
              Import is not ready yet.
            </p>
            {blockingUnmapped.length > 0 && (
              <p className="text-xs text-red-300/80">
                Upload data for: {blockingUnmapped.join(', ')}.
              </p>
            )}
            {(preview.unmapped_seeds?.length ?? 0) > 0 && blockingUnmapped.length === 0 && (
              <p className="text-xs text-zinc-400">
                Optional seeds not uploaded: {preview.unmapped_seeds!.join(', ')} (import can proceed).
              </p>
            )}
          </div>
        )}

        {submitError && (
          <p className="text-xs text-red-400 font-medium flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" />
            {submitError}
          </p>
        )}

        <button
          onClick={handleConfirmImport}
          disabled={isPending || (!alreadyConfirmed && !canConfirm)}
          className="w-full py-4 rounded-xl bg-amber-500 text-black font-black text-base hover:bg-amber-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2 group shadow-xl shadow-amber-500/10"
        >
          {isPending ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              {alreadyConfirmed ? 'Continuing…' : 'Confirming…'}
            </>
          ) : (
            <>
              {alreadyConfirmed ? 'Continue to Import' : 'Confirm & Start Import'}
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}

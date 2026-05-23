'use client';

// src/components/implementation/validate/ValidateView.tsx
// Full data review + double-confirm before import

import { useState, useTransition } from 'react';
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

interface Props {
  jobId: string;
  preview: ValidatePreviewData;
  submitValidation: (formData: FormData) => Promise<void>;
  submitImport: (formData: FormData) => Promise<void>;
  sandboxHref: string;
  companySlug: string;
}

const PHASE_LABELS: Record<string, { label: string; icon: typeof Package }> = {
  phase_a_config:        { label: 'Phase A — Configuration', icon: Layers },
  phase_b_master:        { label: 'Phase B — Master Data',   icon: Database },
  phase_c_transactional: { label: 'Phase C — Transactions',  icon: Package },
};

export function ValidateView({ jobId, preview, submitValidation, submitImport, sandboxHref, companySlug }: Props) {
  const [step, setStep] = useState<'review' | 'confirmed' | 'importing'>('review');
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  const profile = preview.profile;
  const totalRecords = preview.doctypes.reduce((s, d) => s + d.total_rows, 0);
  const totalDoctypes = preview.doctypes.length;
  const hasErrors = preview.validation_overall === 'fail';

  const handleValidate = () => {
    startTransition(async () => {
      const formData = new FormData();
      formData.append('jobId', jobId);
      formData.append('companySlug', companySlug);
      formData.append('responses', JSON.stringify({}));
      formData.append('profileEdits', JSON.stringify({}));
      formData.append('note', '');
      await submitValidation(formData);
      setStep('confirmed');
    });
  };

  const handleImport = () => {
    startTransition(async () => {
      const formData = new FormData();
      formData.append('jobId', jobId);
      await submitImport(formData);
      router.push(sandboxHref);
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
          ) : (
            <CheckCircle className="w-4 h-4 text-emerald-400" />
          )}
          <span className={`text-xs font-bold ${hasErrors ? 'text-red-400' : 'text-emerald-400'}`}>
            {hasErrors ? 'Has Errors' : 'All Passed'}
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
            { label: 'Data Quality', value: profile.data_quality_score != null ? `${Math.round(Number(profile.data_quality_score) * 100)}%` : '—' },
          ].map((item) => (
            <div key={item.label}>
              <p className="text-[10px] uppercase tracking-widest text-gray-700 mb-1">{item.label}</p>
              <p className="text-sm text-white font-medium">{item.value}</p>
            </div>
          ))}
        </div>

        {/* Modules */}
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

        {/* Doctypes */}
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

      {/* ── Action Buttons ─────────────────────────────────────────────────── */}
      {step === 'review' && (
        <div className="space-y-3">
          {hasErrors && (
            <p className="text-xs text-yellow-500 font-medium flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" />
              Some doctypes have validation errors. You can still proceed — errors will be logged.
            </p>
          )}
          <button
            onClick={handleValidate}
            disabled={isPending}
            className="w-full py-4 rounded-xl bg-white/[0.08] border border-white/[0.12] text-white font-bold text-base hover:bg-white/[0.12] transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2 group"
          >
            {isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Validating…
              </>
            ) : (
              <>
                <Shield className="w-4 h-4 text-amber-400" />
                Validate & Confirm Data
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </>
            )}
          </button>
        </div>
      )}

      {step === 'confirmed' && (
        <div className="space-y-4">
          <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-5 py-4">
            <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0" />
            <div>
              <p className="text-sm font-bold text-emerald-400">Data Validated</p>
              <p className="text-xs text-emerald-300/70 mt-0.5">
                Your data has been confirmed. Click below to start the live import into ERPNext.
              </p>
            </div>
          </div>

          <button
            onClick={handleImport}
            disabled={isPending}
            className="w-full py-4 rounded-xl bg-amber-500 text-black font-black text-base hover:bg-amber-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2 group shadow-xl shadow-amber-500/10"
          >
            {isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Starting Import…
              </>
            ) : (
              <>
                Confirm & Start Import
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
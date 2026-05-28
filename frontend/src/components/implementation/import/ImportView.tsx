'use client';

import { useState, useTransition, useEffect, useCallback } from 'react';
import {
  ExternalLink,
  Server,
  ShieldCheck,
  CheckCircle,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import { getBaseApiUrl } from '@/lib/config';
import type { LiveInstance } from '@/types/implementation';

interface PlanGap {
  doctype: string;
  action: string;
  criticality?: string;
}

interface ImportResultRow {
  phase: string;
  step_number: number;
  doctype: string;
  action: string;
  status: string;
  records_attempted: number;
  records_succeeded: number;
  records_failed: number;
  error_message: string | null;
}

interface Props {
  jobId: string;
  companySlug: string;
  instance: LiveInstance;
  approveAction: (formData: FormData) => Promise<void>;
}

function extractCriticalGaps(plan: Record<string, unknown> | null): PlanGap[] {
  if (!plan) return [];
  const phases = (plan.phases as Record<string, { steps?: PlanGap[] }>) || {};
  const gaps: PlanGap[] = [];
  for (const phase of Object.values(phases)) {
    for (const step of phase.steps || []) {
      if (
        step.action === 'data_gap' ||
        (step.criticality === 'critical' && step.action !== 'seed_from_baseline' && step.action !== 'skip')
      ) {
        gaps.push(step);
      }
    }
  }
  return gaps;
}

export function ImportView({ jobId, companySlug, instance, approveAction }: Props) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [isPending, startTransition] = useTransition();
  const [stage, setStage] = useState<string | null>(null);
  const [planStatus, setPlanStatus] = useState<string | null>(null);
  const [gaps, setGaps] = useState<PlanGap[]>([]);
  const [importResults, setImportResults] = useState<ImportResultRow[]>([]);
  const [approveError, setApproveError] = useState<string | null>(null);

  const poll = useCallback(async () => {
    try {
      const base = getBaseApiUrl();
      const [stageRes, planRes] = await Promise.all([
        fetch(`${base}/api/implementation/stage/${jobId}`, { cache: 'no-store' }),
        fetch(`${base}/api/implementation/import-plan/${jobId}`, { cache: 'no-store' }),
      ]);

      let currentStage: string | null = null;
      if (stageRes.ok) {
        const data = await stageRes.json();
        currentStage = data.stage || null;
        setStage(currentStage);
      }

      if (planRes.ok) {
        const data = await planRes.json();
        const plan = data.import_plan as Record<string, unknown> | null;
        setPlanStatus((plan?.status as string) || null);
        setGaps(extractCriticalGaps(plan));
      }

      if (
        currentStage === 'complete' ||
        currentStage === 'complete_with_errors' ||
        currentStage === 'importing'
      ) {
        const resultsRes = await fetch(
          `${base}/api/implementation/import-results/${jobId}`,
          { cache: 'no-store' },
        );
        if (resultsRes.ok) {
          const data = await resultsRes.json();
          setImportResults((data.import_results as ImportResultRow[]) || []);
        }
      }
    } catch {
      // retry on next interval
    }
  }, [jobId]);

  useEffect(() => {
    poll();
    const id = setInterval(poll, 4000);
    return () => clearInterval(id);
  }, [poll]);

  const isBlocked = stage === 'import_blocked' || planStatus === 'blocked';
  const isImporting = stage === 'importing';
  const isCompleteWithErrors = stage === 'complete_with_errors';
  const isComplete = stage === 'complete' || isCompleteWithErrors;
  const awaitingApproval =
    stage === 'awaiting_sandbox_approval' && planStatus !== 'blocked' && !isBlocked;
  const preparingPlan =
    stage !== null &&
    !awaitingApproval &&
    !isImporting &&
    !isComplete &&
    !isBlocked &&
    planStatus !== 'blocked';

  const handleApprove = () => {
    setApproveError(null);
    startTransition(async () => {
      try {
        const formData = new FormData();
        formData.append('companySlug', companySlug);
        formData.append('jobId', jobId);
        await approveAction(formData);
        setShowConfirm(false);
        await poll();
      } catch (err) {
        setApproveError(err instanceof Error ? err.message : 'Import approval failed');
        setShowConfirm(false);
        await poll();
      }
    });
  };

  const headerTitle = isCompleteWithErrors
    ? 'Import finished with errors.'
    : isComplete
      ? "You're live."
      : isBlocked
        ? 'Import blocked.'
        : isImporting
          ? 'Import in progress.'
          : 'Your ERP is ready.';

  const headerSubtitle = isCompleteWithErrors
    ? 'Some records failed to import. Review the results below before using the live instance.'
    : isComplete
      ? 'Your data has been imported into your live ERPNext instance.'
      : isBlocked
        ? 'Critical setup gaps must be resolved before live import can run.'
        : isImporting
          ? 'We are writing your validated data into ERPNext. This may take a few minutes.'
          : 'Review your live instance below. When ready, approve to run the live import.';

  return (
    <div className="space-y-8">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-500 mb-2">
          Step 04 of 04
        </p>
        <h1 className="text-3xl font-black text-white mb-3">{headerTitle}</h1>
        <p className="text-gray-500 text-base leading-relaxed">{headerSubtitle}</p>
      </div>

      <div
        className={`rounded-2xl border overflow-hidden transition-all duration-500 ${
          isCompleteWithErrors
            ? 'border-amber-500/30 bg-amber-500/5'
            : isComplete
              ? 'border-green-500/30 bg-green-500/5'
              : isBlocked
                ? 'border-red-500/20 bg-red-500/5'
                : 'border-amber-500/20 bg-amber-500/5'
        }`}
      >
        <div className="p-6 space-y-5">
          <div className="flex items-center gap-3">
            {isCompleteWithErrors ? (
              <AlertTriangle className="w-5 h-5 text-amber-400" />
            ) : isComplete ? (
              <CheckCircle className="w-5 h-5 text-green-400" />
            ) : isBlocked ? (
              <AlertTriangle className="w-5 h-5 text-red-400" />
            ) : isImporting ? (
              <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />
            ) : (
              <Server className="w-5 h-5 text-amber-400" />
            )}
            <span
              className={`text-sm font-bold ${
                isCompleteWithErrors
                  ? 'text-amber-400'
                  : isComplete
                    ? 'text-green-400'
                    : isBlocked
                      ? 'text-red-400'
                      : 'text-amber-400'
              }`}
            >
              {isCompleteWithErrors
                ? 'Import Complete (Errors)'
                : isComplete
                  ? 'Live Instance'
                  : isBlocked
                    ? 'Import Blocked'
                    : isImporting
                      ? 'Import Running'
                      : 'Live Instance'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {[
              { label: 'Instance URL', value: instance.url, mono: true },
              { label: 'Username', value: instance.username, mono: true },
              {
                label: 'Password',
                value: instance.password,
                mono: true,
                blur: !isComplete,
              },
            ].map(({ label, value, mono, blur }) => (
              <div key={label}>
                <p className="text-[10px] uppercase tracking-widest text-gray-700 mb-1">{label}</p>
                <p
                  className={`text-sm font-medium text-white ${mono ? 'font-mono' : ''} ${
                    blur ? 'blur-sm select-none' : ''
                  }`}
                >
                  {value}
                </p>
              </div>
            ))}
          </div>

          <a
            href={instance.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-white/[0.06] border border-white/[0.1] text-white text-sm font-bold px-4 py-2.5 rounded-lg hover:bg-white/[0.1] transition-colors"
          >
            Open ERPNext
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>

      {preparingPlan && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-white/[0.03] border border-white/[0.08]">
          <Loader2 className="w-5 h-5 text-amber-400 animate-spin flex-shrink-0" />
          <div>
            <p className="text-sm font-bold text-white">Preparing import plan…</p>
            <p className="text-xs text-gray-600 mt-0.5">
              Finalizing your data mapping. The approve button will appear shortly.
            </p>
          </div>
        </div>
      )}

      {isBlocked && (
        <div className="space-y-4">
          <div className="flex items-start gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20">
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-bold text-red-400">Live import was not run</p>
              <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                The import plan is blocked. ERPNext config masters (UOM, groups, territory) are
                normally seeded automatically — if you still see gaps below, re-run the pipeline
                after deploying the latest worker, or upload files for the listed doctypes.
              </p>
            </div>
          </div>

          {gaps.length > 0 && (
            <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 space-y-2">
              <p className="text-xs font-bold uppercase tracking-widest text-red-400">
                Critical gaps ({gaps.length})
              </p>
              <ul className="space-y-1.5">
                {gaps.map((g) => (
                  <li
                    key={g.doctype}
                    className="flex items-center justify-between text-sm px-3 py-2 rounded-lg bg-black/20 border border-white/[0.05]"
                  >
                    <span className="font-mono text-white">{g.doctype}</span>
                    <span className="text-[10px] uppercase text-red-400">{g.action}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {approveError && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20">
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-300">{approveError}</p>
        </div>
      )}

      {awaitingApproval && (
        <>
          <div className="space-y-2">
            <p className="text-xs font-bold uppercase tracking-widest text-gray-600">
              Before you approve
            </p>
            {[
              'Verify your item list and stock quantities',
              'Check suppliers and customer master data',
              'Confirm chart of accounts looks correct',
            ].map((item) => (
              <div
                key={item}
                className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]"
              >
                <div className="w-4 h-4 rounded border border-white/[0.1] flex-shrink-0" />
                <span className="text-sm text-gray-500">{item}</span>
              </div>
            ))}
          </div>

          {!showConfirm ? (
            <button
              onClick={() => setShowConfirm(true)}
              className="w-full py-4 rounded-xl bg-amber-500 text-black font-black text-base hover:bg-amber-400 transition-colors flex items-center justify-center gap-2 shadow-xl shadow-amber-500/10"
            >
              <ShieldCheck className="w-5 h-5" />
              Approve & Run Live Import
            </button>
          ) : (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-6 space-y-4">
              <p className="text-white font-bold">Run live import?</p>
              <p className="text-sm text-gray-500 leading-relaxed">
                This writes your validated data into{' '}
                <strong className="text-white">{instance.url.replace('https://', '')}</strong>.
                Make sure you have reviewed the data on the Validate step.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={handleApprove}
                  disabled={isPending}
                  className="flex-1 py-3 rounded-lg bg-amber-500 text-black font-bold hover:bg-amber-400 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Starting…
                    </>
                  ) : (
                    'Yes, import now'
                  )}
                </button>
                <button
                  onClick={() => setShowConfirm(false)}
                  className="flex-1 py-3 rounded-lg bg-white/[0.04] border border-white/[0.08] text-gray-400 font-bold hover:text-white hover:bg-white/[0.07] transition-colors"
                >
                  Not yet
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {(isComplete || isImporting) && importResults.length > 0 && (
        <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 space-y-3">
          <p className="text-xs font-bold uppercase tracking-widest text-gray-500">
            Import results ({importResults.length} steps)
          </p>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {importResults.map((row) => {
              const hasFailures = row.records_failed > 0 || row.status === 'error';
              return (
                <div
                  key={`${row.phase}-${row.step_number}-${row.doctype}`}
                  className={`flex flex-col gap-1 text-sm px-3 py-2 rounded-lg border ${
                    hasFailures
                      ? 'bg-amber-500/5 border-amber-500/20'
                      : 'bg-black/20 border-white/[0.05]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-white">{row.doctype}</span>
                    <span
                      className={`text-[10px] uppercase ${
                        hasFailures ? 'text-amber-400' : 'text-green-400'
                      }`}
                    >
                      {row.records_succeeded}/{row.records_attempted} ok
                    </span>
                  </div>
                  {row.error_message && (
                    <p className="text-xs text-gray-500 leading-relaxed">{row.error_message}</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {isComplete && !isCompleteWithErrors && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-green-500/10 border border-green-500/20">
          <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
          <div>
            <p className="text-sm font-bold text-green-400">Import complete.</p>
            <p className="text-xs text-gray-600 mt-0.5">
              Your team can log in to the live ERPNext instance.
            </p>
          </div>
        </div>
      )}

      {isCompleteWithErrors && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
          <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
          <div>
            <p className="text-sm font-bold text-amber-400">Import completed with errors.</p>
            <p className="text-xs text-gray-600 mt-0.5">
              Review failed doctypes above. Masters that succeeded are available in ERPNext.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

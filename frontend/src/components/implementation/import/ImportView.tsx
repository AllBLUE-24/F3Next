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

interface Props {
  jobId: string;
  companySlug: string;
  instance: LiveInstance;
  approveAction: (formData: FormData) => Promise<void>;
}

export function ImportView({ jobId, companySlug, instance, approveAction }: Props) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [isPending, startTransition] = useTransition();
  const [approved, setApproved] = useState(instance.isApproved);
  const [stage, setStage] = useState<string | null>(null);

  const pollStage = useCallback(async () => {
    try {
      const res = await fetch(`${getBaseApiUrl()}/api/implementation/stage/${jobId}`, {
        cache: 'no-store',
      });
      if (!res.ok) return;
      const data = await res.json();
      setStage(data.stage || null);
      if (data.stage === 'complete' || data.stage === 'importing') {
        setApproved(true);
      }
    } catch {
      // retry on next interval
    }
  }, [jobId]);

  useEffect(() => {
    pollStage();
    const id = setInterval(pollStage, 4000);
    return () => clearInterval(id);
  }, [pollStage]);

  const isImporting = stage === 'importing';
  const isComplete = stage === 'complete' || approved;
  const awaitingApproval = stage === 'awaiting_sandbox_approval' && !approved;
  const preparingPlan =
    stage !== null &&
    !awaitingApproval &&
    !isImporting &&
    !isComplete &&
    stage !== 'import_blocked';

  const handleApprove = () => {
    startTransition(async () => {
      const formData = new FormData();
      formData.append('companySlug', companySlug);
      formData.append('jobId', jobId);
      await approveAction(formData);
      setApproved(true);
      setShowConfirm(false);
      pollStage();
    });
  };

  return (
    <div className="space-y-8">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-500 mb-2">
          Step 04 of 04
        </p>
        <h1 className="text-3xl font-black text-white mb-3">
          {isComplete ? "You're live." : isImporting ? 'Import in progress.' : 'Your ERP is ready.'}
        </h1>
        <p className="text-gray-500 text-base leading-relaxed">
          {isComplete
            ? 'Your data has been imported into your live ERPNext instance.'
            : isImporting
              ? 'We are writing your validated data into ERPNext. This may take a few minutes.'
              : 'Review your live instance below. When ready, approve to run the live import.'}
        </p>
      </div>

      <div
        className={`rounded-2xl border overflow-hidden transition-all duration-500 ${
          isComplete ? 'border-green-500/30 bg-green-500/5' : 'border-amber-500/20 bg-amber-500/5'
        }`}
      >
        <div className="p-6 space-y-5">
          <div className="flex items-center gap-3">
            {isComplete ? (
              <CheckCircle className="w-5 h-5 text-green-400" />
            ) : isImporting ? (
              <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />
            ) : (
              <Server className="w-5 h-5 text-amber-400" />
            )}
            <span
              className={`text-sm font-bold ${
                isComplete ? 'text-green-400' : 'text-amber-400'
              }`}
            >
              {isComplete ? 'Live Instance' : isImporting ? 'Import Running' : 'Live Instance'}
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

      {stage === 'import_blocked' && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20">
          <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <div>
            <p className="text-sm font-bold text-red-400">Import blocked</p>
            <p className="text-xs text-gray-600 mt-0.5">
              Critical data gaps must be resolved before live import can proceed.
            </p>
          </div>
        </div>
      )}

      {isComplete && (
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
    </div>
  );
}

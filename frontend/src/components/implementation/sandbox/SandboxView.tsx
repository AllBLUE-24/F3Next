'use client';

// src/components/implementation/sandbox/SandboxView.tsx

import { useState, useEffect, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { ExternalLink, FlaskConical, ShieldCheck, Clock, CheckCircle, AlertTriangle } from 'lucide-react';
import type { SandboxInstance } from '@/types/implementation';

interface Props {
  sandbox: SandboxInstance;
  companySlug: string;
  approveAction: (formData: FormData) => Promise<void>;
}

function useCountdown(expiresAt: string) {
  const [remaining, setRemaining] = useState(0);

  useEffect(() => {
    const update = () => {
      const diff = new Date(expiresAt).getTime() - Date.now();
      setRemaining(Math.max(0, diff));
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [expiresAt]);

  const hours   = Math.floor(remaining / 3_600_000);
  const minutes = Math.floor((remaining % 3_600_000) / 60_000);
  const seconds = Math.floor((remaining % 60_000) / 1000);
  const pct     = (remaining / 86_400_000) * 100; // % of 24hrs remaining

  return { hours, minutes, seconds, pct, expired: remaining === 0 };
}

export function SandboxView({ sandbox, companySlug, approveAction }: Props) {
  const [showConfirm, setShowConfirm]     = useState(false);
  const [isPending, startTransition]      = useTransition();
  const [approved, setApproved]           = useState(sandbox.isApproved);
  const countdown                         = useCountdown(sandbox.expiresAt);
  const router                            = useRouter();

  const handleApprove = () => {
    startTransition(async () => {
      const formData = new FormData();
      formData.append('companySlug', companySlug);
      await approveAction(formData);
      setApproved(true);
      setShowConfirm(false);
    });
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-500 mb-2">Step 04 of 04</p>
        <h1 className="text-3xl font-black text-white mb-3">
        {approved ? "You're live." : "Your sandbox is ready."}
        </h1>
        <p className="text-gray-500 text-base leading-relaxed">
          {approved
            ? "Your data has been imported to the production ERPNext instance. You're all set."
            : "Explore your ERPNext instance with real data for 24 hours. When you're happy, approve and we'll move it to production."}
        </p>
      </div>

      {/* Sandbox card */}
      <div className={`rounded-2xl border overflow-hidden transition-all duration-500 ${
        approved ? 'border-green-500/30 bg-green-500/5' : 'border-amber-500/20 bg-amber-500/5'
      }`}>
        <div className="p-6 space-y-5">
          {/* Status */}
          <div className="flex items-center gap-3">
            {approved
              ? <CheckCircle className="w-5 h-5 text-green-400" />
              : <FlaskConical className="w-5 h-5 text-amber-400" />
            }
            <span className={`text-sm font-bold ${approved ? 'text-green-400' : 'text-amber-400'}`}>
              {approved ? 'Production Instance' : 'Sandbox Instance'}
            </span>
          </div>

          {/* Credentials */}
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: 'Instance URL', value: sandbox.url, mono: true },
              { label: 'Username',     value: sandbox.username, mono: true },
              { label: 'Password',     value: sandbox.password, mono: true, blur: !approved },
            ].map(({ label, value, mono, blur }) => (
              <div key={label}>
                <p className="text-[10px] uppercase tracking-widest text-gray-700 mb-1">{label}</p>
                <p className={`text-sm font-medium text-white ${mono ? 'font-mono' : ''} ${blur ? 'blur-sm select-none' : ''}`}>
                  {value}
                </p>
              </div>
            ))}
          </div>

          <a
            href={sandbox.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-white/[0.06] border border-white/[0.1] text-white text-sm font-bold px-4 py-2.5 rounded-lg hover:bg-white/[0.1] transition-colors"
          >
            Open ERPNext
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>

        {/* Countdown bar */}
        {!approved && !countdown.expired && (
          <div className="border-t border-white/[0.06] px-6 py-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Clock className="w-3.5 h-3.5 text-gray-600" />
                <span className="text-xs text-gray-600">Sandbox window</span>
              </div>
              <span className="font-mono text-sm text-white tabular-nums">
                {String(countdown.hours).padStart(2, '0')}:
                {String(countdown.minutes).padStart(2, '0')}:
                {String(countdown.seconds).padStart(2, '0')}
              </span>
            </div>
            <div className="h-1 bg-white/[0.06] rounded-full overflow-hidden">
              <div
                className="h-full bg-amber-500 rounded-full transition-all duration-1000"
                style={{ width: `${countdown.pct}%` }}
              />
            </div>
          </div>
        )}

        {countdown.expired && !approved && (
          <div className="border-t border-red-500/20 px-6 py-4 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <p className="text-xs text-red-400">Sandbox window has expired. Contact support to extend.</p>
          </div>
        )}
      </div>

      {/* Checklist */}
      {!approved && (
        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-widest text-gray-600">Before you approve</p>
          {[
            'Verify your item list and stock quantities',
            'Check suppliers and customer master data',
            'Open one purchase order and one sales order',
            'Confirm chart of accounts looks correct',
          ].map((item) => (
            <div key={item} className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/[0.05]">
              <div className="w-4 h-4 rounded border border-white/[0.1] flex-shrink-0" />
              <span className="text-sm text-gray-500">{item}</span>
            </div>
          ))}
        </div>
      )}

      {/* Approve button / confirmation */}
      {!approved && (
        <>
          {!showConfirm ? (
            <button
              onClick={() => setShowConfirm(true)}
              disabled={countdown.expired}
              className="w-full py-4 rounded-xl bg-amber-500 text-black font-black text-base hover:bg-amber-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2 group shadow-xl shadow-amber-500/10"
            >
              <ShieldCheck className="w-5 h-5" />
              Approve & Import to Production
            </button>
          ) : (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-6 space-y-4">
              <p className="text-white font-bold">Are you sure?</p>
              <p className="text-sm text-gray-500 leading-relaxed">
                This will import your validated data into the <strong className="text-white">live production</strong> ERPNext instance. 
                This action cannot be undone. Make sure you've tested everything in the sandbox.
              </p>
              <div className="flex gap-3">
                <button
                  onClick={handleApprove}
                  disabled={isPending}
                  className="flex-1 py-3 rounded-lg bg-amber-500 text-black font-bold hover:bg-amber-400 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isPending
                    ? <><div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" /> Importing…</>
                    : 'Yes, go live'
                  }
                </button>
                <button
                  onClick={() => setShowConfirm(false)}
                  className="flex-1 py-3 rounded-lg bg-white/[0.04] border border-white/[0.08] text-gray-400 font-bold hover:text-white hover:bg-white/[0.07] transition-colors"
                >
                  Keep testing
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Approved state */}
      {approved && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-green-500/10 border border-green-500/20">
          <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
          <div>
            <p className="text-sm font-bold text-green-400">Production import complete.</p>
            <p className="text-xs text-gray-600 mt-0.5">Your team can now log in to the live ERPNext instance.</p>
          </div>
        </div>
      )}
    </div>
  );
}
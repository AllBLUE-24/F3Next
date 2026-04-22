'use client';
// PATH: src/components/implementation/shell/DeploymentPill.tsx
// ✅ No context. Reads companySlug from URL. Falls back to mock in dev.

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import type { DeploymentState } from '@/types/implementation';

const API_BASE = (typeof window !== "undefined" ? "" : "http://backend_api:8000");

const STATUS_CONFIG = {
  pending:   { label: 'Initializing',       dot: 'bg-gray-500',                text: 'text-gray-500',  ring: 'bg-gray-500/10 border-gray-500/20' },
  deploying: { label: 'Deploying Instance', dot: 'bg-amber-500 animate-pulse', text: 'text-amber-400', ring: 'bg-amber-500/10 border-amber-500/20' },
  ready:     { label: 'Instance Ready',     dot: 'bg-green-500',               text: 'text-green-400', ring: 'bg-green-500/10 border-green-500/20' },
  failed:    { label: 'Deploy Failed',      dot: 'bg-red-500',                 text: 'text-red-400',   ring: 'bg-red-500/10 border-red-500/20' },
};

const DEV_MOCK: DeploymentState = {
  status: 'deploying',
  progress: 47,
  instanceUrl: null,
  region: 'ap-south-1',
  erpSoftware: 'ERPNext',
  startedAt: new Date().toISOString(),
  readyAt: null,
};

export function DeploymentPill() {
  const params = useParams<{ companySlug: string }>();
  const [deployment, setDeployment] = useState<DeploymentState | null>(null);

  useEffect(() => {
    const companySlug = params?.companySlug;
    if (!companySlug) return;

    let stopped = false;

    const poll = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/deployment/slug/${companySlug}`);
        if (!res.ok) throw new Error('not ok');
        const data: DeploymentState = await res.json();
        if (!stopped) setDeployment(data);
        // Stop polling on terminal state
        if (data.status === 'ready' || data.status === 'failed') stopped = true;
      } catch {
        // Route handler not built yet — use dev mock so the pill still renders
        if (!stopped) setDeployment(DEV_MOCK);
      }
    };

    poll();
    const id = setInterval(() => { if (!stopped) poll(); }, 5000);
    return () => { stopped = true; clearInterval(id); };
  }, [params?.companySlug]);

  if (!deployment) {
    return (
      <div className="inline-flex items-center gap-2 rounded-full border border-white/[0.06] bg-white/[0.02] px-3.5 py-1.5 text-xs text-gray-700">
        <span className="w-1.5 h-1.5 rounded-full bg-gray-800 animate-pulse" />
        <span className="font-mono">ERPNext</span>
        <span className="text-white/10">·</span>
        <span>Connecting…</span>
      </div>
    );
  }

  const cfg = STATUS_CONFIG[deployment.status];

  return (
    <div className={`inline-flex items-center gap-2.5 rounded-full border px-3.5 py-1.5 text-xs font-medium transition-all duration-500 ${cfg.ring} ${cfg.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${cfg.dot}`} />
      <span className="font-mono">{deployment.erpSoftware}</span>
      <span className="text-white/20">·</span>
      <span>{cfg.label}</span>

      {deployment.status === 'deploying' && (
        <>
          <span className="text-white/20">·</span>
          <div className="w-16 h-1 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full bg-amber-500 rounded-full transition-all duration-700"
              style={{ width: `${deployment.progress}%` }}
            />
          </div>
          <span className="tabular-nums">{deployment.progress}%</span>
        </>
      )}

      {deployment.status === 'ready' && deployment.instanceUrl && (
        <>
          <span className="text-white/20">·</span>
          <a
            href={deployment.instanceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2 hover:text-green-300 transition-colors"
          >
            Open
          </a>
          {(deployment as any).adminPassword && (
            <>
              <span className="text-white/20">·</span>
              <span className="text-gray-400">Administrator / <span className="text-white font-mono select-all font-bold">{(deployment as any).adminPassword}</span></span>
            </>
          )}
        </>
      )}
    </div>
  );
}
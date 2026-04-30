'use client';
// PATH: src/components/implementation/shell/DeploymentPill.tsx

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getBaseApiUrl } from '@/lib/config';
import { ExternalLink, Copy, Server } from 'lucide-react';

const STATUS_CONFIG = {
  pending:   { label: 'Initializing',       dot: 'bg-zinc-500',                text: 'text-zinc-500' },
  deploying: { label: 'Deploying',          dot: 'bg-amber-500 animate-pulse', text: 'text-amber-400' },
  ready:     { label: 'Live Instance',      dot: 'bg-green-500',               text: 'text-green-400' },
  failed:    { label: 'Deploy Failed',      dot: 'bg-red-500',                 text: 'text-red-400' },
};

const DEV_MOCK: any = {
  status: 'ready',
  progress: 100,
  instanceUrl: 'https://live-erp.f3next.in',
  region: 'ap-south-1',
  erpSoftware: 'ERPNext',
  startedAt: new Date().toISOString(),
  readyAt: new Date().toISOString(),
  adminPassword: 'f3-secure-pass-9921',
};

export function DeploymentPill({ collapsed = false }: { collapsed?: boolean }) {
  const params = useParams<{ companySlug: string }>();
  const [deployment, setDeployment] = useState<any>(null);

  useEffect(() => {
    const companySlug = params?.companySlug;
    if (!companySlug) return;

    let stopped = false;

    const poll = async () => {
      try {
        const res = await fetch(`${getBaseApiUrl()}/api/deployment/slug/${companySlug}`);
        if (!res.ok) throw new Error('not ok');
        const data = await res.json();
        if (!stopped) setDeployment(data);
        if (data.status === 'ready' || data.status === 'failed') stopped = true;
      } catch {
        if (!stopped) setDeployment(DEV_MOCK);
      }
    };

    poll();
    const id = setInterval(() => { if (!stopped) poll(); }, 5000);
    return () => { stopped = true; clearInterval(id); };
  }, [params?.companySlug]);

  if (!deployment) {
    if (collapsed) {
      return (
        <div className="w-10 h-10 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-shell)] flex items-center justify-center shrink-0">
          <span className="w-2 h-2 rounded-full bg-zinc-700 animate-pulse" />
        </div>
      );
    }
    return (
      <div className="flex items-center gap-2.5 p-3 rounded-lg bg-[var(--bg-shell)] border border-[var(--border-subtle)] w-full">
        <span className="w-2 h-2 rounded-full bg-zinc-800 animate-pulse" />
        <span className="text-[11px] font-mono text-zinc-500">Connecting...</span>
      </div>
    );
  }

  const cfg = STATUS_CONFIG[deployment.status as keyof typeof STATUS_CONFIG];

  if (collapsed) {
    return (
      <div className={`w-10 h-10 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-shell)] flex items-center justify-center shrink-0 transition-all`} title={`${cfg.label} - ${deployment.erpSoftware}`}>
        <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
      </div>
    );
  }

  return (
    <div className={`flex flex-col gap-2 rounded-lg bg-[var(--bg-shell)] border border-[var(--border-subtle)] p-3 text-[11px] transition-all duration-500 w-full`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Server className={`w-3.5 h-3.5 ${cfg.text}`} />
          <span className={`font-bold ${cfg.text} tracking-wide uppercase text-[10px]`}>{cfg.label}</span>
        </div>
      </div>

      {/* Progress Bar (Deploying) */}
      {deployment.status === 'deploying' && (
        <div className="w-full space-y-1.5 mt-1">
          <div className="flex justify-between text-[10px] text-zinc-400 font-medium">
            <span>Provisioning</span>
            <span className="tabular-nums font-mono">{deployment.progress}%</span>
          </div>
          <div className="w-full h-1 bg-[var(--bg-void)] rounded-full overflow-hidden">
            <div
              className="h-full bg-amber-500 rounded-full transition-all duration-700"
              style={{ width: `${deployment.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Minimalist Live Credentials (Ready) */}
      {deployment.status === 'ready' && deployment.instanceUrl && (
        <div className="flex flex-col gap-1.5 mt-1 pt-1.5 border-t border-[var(--border-subtle)]">
          <div className="flex justify-between items-center group">
            <span className="text-zinc-500 text-[10px]">URL</span>
            <a href={deployment.instanceUrl} target="_blank" rel="noopener noreferrer" className="text-zinc-300 font-mono text-[10px] hover:text-white transition-colors flex items-center gap-1">
              {deployment.instanceUrl.replace('https://', '')} <ExternalLink className="w-2.5 h-2.5" />
            </a>
          </div>
          <div className="flex justify-between items-center group">
             <span className="text-zinc-500 text-[10px]">UID</span>
             <span className="text-zinc-300 font-mono text-[10px]">Administrator</span>
          </div>
          {deployment.adminPassword && (
            <div className="flex justify-between items-center group">
               <span className="text-zinc-500 text-[10px]">PWD</span>
               <div className="flex items-center gap-2">
                 <span className="text-zinc-300 font-mono text-[10px] filter blur-[2px] hover:blur-none transition-all select-all">
                   {deployment.adminPassword}
                 </span>
                 <button onClick={() => navigator.clipboard.writeText(deployment.adminPassword)} className="text-zinc-600 hover:text-white transition-colors">
                   <Copy className="w-2.5 h-2.5" />
                 </button>
               </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
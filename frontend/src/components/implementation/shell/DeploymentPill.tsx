'use client';
// PATH: src/components/implementation/shell/DeploymentPill.tsx

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { getBaseApiUrl } from '@/lib/config';
import { useImplementation } from '@/contexts/ImplementationContext';
import type { DeploymentStatus } from '@/types/implementation';
import { ExternalLink, Copy, Server } from 'lucide-react';

const STATUS_CONFIG: Record<
  DeploymentStatus,
  { label: string; dot: string; text: string }
> = {
  pending: { label: 'Not Live', dot: 'bg-zinc-500', text: 'text-zinc-500' },
  deploying: { label: 'Deploying', dot: 'bg-amber-500 animate-pulse', text: 'text-amber-400' },
  ready: { label: 'Live Instance', dot: 'bg-green-500', text: 'text-green-400' },
  failed: { label: 'Deploy Failed', dot: 'bg-red-500', text: 'text-red-400' },
};

export function DeploymentPill({ collapsed = false }: { collapsed?: boolean }) {
  const params = useParams<{ companySlug: string }>();
  const { session, deployment, refreshDeployment } = useImplementation();
  const [isDeploying, setIsDeploying] = useState(false);
  const [deployError, setDeployError] = useState<string | null>(null);

  const handleDeploy = async () => {
    setIsDeploying(true);
    setDeployError(null);
    try {
      const res = await fetch(`${getBaseApiUrl()}/api/deploy/infra`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: session.instanceId,
          company_slug: params?.companySlug || session.companySlug,
          tier: 'standard',
        }),
      });
      if (!res.ok) {
        setDeployError('Deploy failed to start.');
        return;
      }
      await refreshDeployment();
    } catch {
      setDeployError('Network error.');
    } finally {
      setIsDeploying(false);
    }
  };

  const cfg = STATUS_CONFIG[deployment.status];
  const showDeployButton =
    deployment.status !== 'ready' && deployment.status !== 'deploying';

  if (collapsed) {
    return (
      <div
        className="w-10 h-10 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-shell)] flex items-center justify-center shrink-0 transition-all"
        title={`${cfg.label} - ${deployment.erpSoftware}`}
      >
        <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 rounded-lg bg-[var(--bg-shell)] border border-[var(--border-subtle)] p-3 text-[11px] transition-all duration-500 w-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Server className={`w-3.5 h-3.5 ${cfg.text}`} />
          <span className={`font-bold ${cfg.text} tracking-wide uppercase text-[10px]`}>
            {cfg.label}
          </span>
        </div>
      </div>

      {/* Progress (deploying) */}
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

      {/* Deploy Now — only when not live and not already deploying */}
      {showDeployButton && (
        <div className="mt-1 space-y-1.5">
          {deployment.status === 'pending' && (
            <p className="text-[10px] text-zinc-500 leading-relaxed">
              Provision ERPNext so import is ready when validation finishes.
            </p>
          )}
          {deployment.status === 'failed' && (
            <p className="text-[10px] text-red-400/80 leading-relaxed">
              Deployment did not complete. Try again.
            </p>
          )}
          <button
            type="button"
            onClick={handleDeploy}
            disabled={isDeploying}
            className="w-full py-2 rounded-lg bg-amber-500/10 border border-amber-500/25 hover:bg-amber-500/20 text-amber-400 font-semibold text-[11px] transition-all disabled:opacity-50"
          >
            {isDeploying ? 'Starting…' : 'Deploy Now'}
          </button>
          {deployError && (
            <p className="text-[10px] text-red-400">{deployError}</p>
          )}
        </div>
      )}

      {/* Live credentials — ready only */}
      {deployment.status === 'ready' && deployment.instanceUrl && (
        <div className="flex flex-col gap-1.5 mt-1 pt-1.5 border-t border-[var(--border-subtle)]">
          <div className="flex justify-between items-center group">
            <span className="text-zinc-500 text-[10px]">URL</span>
            <a
              href={deployment.instanceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-zinc-300 font-mono text-[10px] hover:text-white transition-colors flex items-center gap-1"
            >
              {deployment.instanceUrl.replace('https://', '')}{' '}
              <ExternalLink className="w-2.5 h-2.5" />
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
                <button
                  type="button"
                  onClick={() => navigator.clipboard.writeText(deployment.adminPassword!)}
                  className="text-zinc-600 hover:text-white transition-colors"
                >
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

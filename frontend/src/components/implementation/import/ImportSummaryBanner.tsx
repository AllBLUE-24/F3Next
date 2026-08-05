'use client';

import { AlertTriangle, CheckCircle, Info, Rocket } from 'lucide-react';

export type ImportUiPayload = {
  import_level: string;
  import_label?: string;
  executive_summary?: string;
  import_ready?: boolean;
  plan_status?: string;
  create_step_count?: number;
  data_gap_count?: number;
  blocked_reasons?: string[];
};

const LEVEL_STYLES: Record<string, { border: string; bg: string; icon: typeof CheckCircle; iconClass: string; badge: string }> = {
  success: {
    border: 'border-emerald-500/25',
    bg: 'bg-gradient-to-br from-emerald-950/40 via-transparent to-transparent',
    icon: Rocket,
    iconClass: 'text-emerald-400',
    badge: 'text-emerald-400 bg-emerald-500/15 border-emerald-500/25',
  },
  partial: {
    border: 'border-amber-500/25',
    bg: 'bg-gradient-to-br from-amber-950/30 via-transparent to-transparent',
    icon: Info,
    iconClass: 'text-amber-400',
    badge: 'text-amber-400 bg-amber-500/15 border-amber-500/25',
  },
  failed: {
    border: 'border-red-500/25',
    bg: 'bg-gradient-to-br from-red-950/40 via-transparent to-transparent',
    icon: AlertTriangle,
    iconClass: 'text-red-400',
    badge: 'text-red-400 bg-red-500/15 border-red-500/25',
  },
  blocked: {
    border: 'border-red-500/25',
    bg: 'bg-gradient-to-br from-red-950/40 via-transparent to-transparent',
    icon: AlertTriangle,
    iconClass: 'text-red-400',
    badge: 'text-red-400 bg-red-500/15 border-red-500/25',
  },
};

type Props = {
  payload: ImportUiPayload | null;
};

export function ImportSummaryBanner({ payload }: Props) {
  if (!payload) return null;

  const level = payload.import_level === 'failed' ? 'failed' : payload.import_level;
  const styles = LEVEL_STYLES[level] || LEVEL_STYLES.partial;
  const Icon = styles.icon;

  return (
    <div className={`rounded-2xl border ${styles.border} ${styles.bg} p-6 space-y-3`}>
      <div className="flex items-start gap-3">
        <div className={`w-9 h-9 rounded-xl border ${styles.border} flex items-center justify-center flex-shrink-0`}>
          <Icon className={`w-5 h-5 ${styles.iconClass}`} />
        </div>
        <div className="min-w-0">
          <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border ${styles.badge}`}>
            {payload.import_label || level}
          </span>
          <p className="text-white text-sm leading-relaxed mt-2">
            {payload.executive_summary || 'Review the import plan before approving live ERP writes.'}
          </p>
          {(payload.create_step_count ?? 0) > 0 && (
            <p className="text-xs text-zinc-400 mt-2">
              {payload.create_step_count} module(s) queued for import.
            </p>
          )}
          {(payload.blocked_reasons?.length ?? 0) > 0 && level === 'blocked' && (
            <p className="text-xs text-red-300/90 mt-2">{payload.blocked_reasons![0]}</p>
          )}
        </div>
      </div>
    </div>
  );
}

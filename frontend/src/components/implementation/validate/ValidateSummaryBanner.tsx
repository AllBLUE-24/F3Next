'use client';

import { AlertTriangle, CheckCircle, Info } from 'lucide-react';

export type ValidateUiPayload = {
  validation_level: string;
  validation_label?: string;
  executive_summary?: string;
  requires_acknowledgment?: boolean;
  import_ready?: boolean;
  blocking_unmapped_seeds?: string[];
};

const LEVEL_STYLES: Record<string, { border: string; bg: string; icon: typeof CheckCircle; iconClass: string; badge: string }> = {
  pass: {
    border: 'border-emerald-500/25',
    bg: 'bg-gradient-to-br from-emerald-950/40 via-transparent to-transparent',
    icon: CheckCircle,
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
  fail: {
    border: 'border-red-500/25',
    bg: 'bg-gradient-to-br from-red-950/40 via-transparent to-transparent',
    icon: AlertTriangle,
    iconClass: 'text-red-400',
    badge: 'text-red-400 bg-red-500/15 border-red-500/25',
  },
};

type Props = {
  payload: ValidateUiPayload;
  acknowledged: boolean;
  onAckChange: (v: boolean) => void;
};

export function ValidateSummaryBanner({ payload, acknowledged, onAckChange }: Props) {
  const level = payload.validation_level === 'failed' ? 'fail' : payload.validation_level;
  const styles = LEVEL_STYLES[level] || LEVEL_STYLES.partial;
  const Icon = styles.icon;
  const needsAck = payload.requires_acknowledgment === true;

  return (
    <div className={`rounded-2xl border ${styles.border} ${styles.bg} p-6 space-y-4`}>
      <div className="flex items-start gap-3">
        <div className={`w-9 h-9 rounded-xl border ${styles.border} flex items-center justify-center flex-shrink-0`}>
          <Icon className={`w-5 h-5 ${styles.iconClass}`} />
        </div>
        <div className="min-w-0">
          <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border ${styles.badge}`}>
            {payload.validation_label || level}
          </span>
          <p className="text-white text-sm leading-relaxed mt-2">
            {payload.executive_summary || 'Review mapped data before confirming import.'}
          </p>
          {(payload.blocking_unmapped_seeds?.length ?? 0) > 0 && (
            <p className="text-xs text-red-300/90 mt-2">
              Unmapped MVP modules: {payload.blocking_unmapped_seeds!.join(', ')}
            </p>
          )}
        </div>
      </div>
      {needsAck && level !== 'fail' && (
        <label className="flex gap-3 items-start p-4 rounded-xl border border-amber-500/20 bg-amber-500/5 cursor-pointer ml-12">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={acknowledged}
            onChange={(e) => onAckChange(e.target.checked)}
          />
          <span className="text-sm text-gray-300 leading-relaxed">
            I have reviewed validation warnings and accept proceeding to import with noted assumptions.
          </span>
        </label>
      )}
    </div>
  );
}

export function canConfirmImport(payload: ValidateUiPayload, acknowledged: boolean): boolean {
  if (!payload.import_ready) return false;
  if (payload.validation_level === 'fail' || payload.validation_level === 'failed') return false;
  if (payload.requires_acknowledgment && !acknowledged) return false;
  return true;
}

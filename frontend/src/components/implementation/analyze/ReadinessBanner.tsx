'use client';

import { AlertTriangle, CheckCircle, Info } from 'lucide-react';

export type ReadinessUiPayload = {
  readiness_level: 'green' | 'yellow' | 'red' | string;
  readiness_label?: string;
  executive_summary?: string;
  requires_acknowledgment?: boolean;
  can_continue_to_mapping?: boolean;
  minimum_viable_possible?: boolean;
  ready_doctypes?: string[];
  missing_doctypes?: string[];
};

const LEVEL_STYLES = {
  green: {
    border: 'border-emerald-500/25',
    bg: 'bg-gradient-to-br from-emerald-950/40 via-transparent to-transparent',
    icon: CheckCircle,
    iconClass: 'text-emerald-400',
    badge: 'text-emerald-400 bg-emerald-500/15 border-emerald-500/25',
  },
  yellow: {
    border: 'border-amber-500/25',
    bg: 'bg-gradient-to-br from-amber-950/30 via-transparent to-transparent',
    icon: Info,
    iconClass: 'text-amber-400',
    badge: 'text-amber-400 bg-amber-500/15 border-amber-500/25',
  },
  red: {
    border: 'border-red-500/25',
    bg: 'bg-gradient-to-br from-red-950/40 via-transparent to-transparent',
    icon: AlertTriangle,
    iconClass: 'text-red-400',
    badge: 'text-red-400 bg-red-500/15 border-red-500/25',
  },
};

type ReadinessBannerProps = {
  readiness: ReadinessUiPayload;
  acknowledged: boolean;
  onAckChange: (v: boolean) => void;
  onProceed?: () => void;
  proceeding?: boolean;
};

export function ReadinessBanner({
  readiness,
  acknowledged,
  onAckChange,
  onProceed,
  proceeding = false,
}: ReadinessBannerProps) {
  const level = (readiness.readiness_level || 'yellow') as keyof typeof LEVEL_STYLES;
  const styles = LEVEL_STYLES[level] || LEVEL_STYLES.yellow;
  const Icon = styles.icon;
  const needsAck = readiness.requires_acknowledgment === true;
  const canProceed = readiness.can_continue_to_mapping !== false && level !== 'red';

  return (
    <div className={`rounded-2xl border ${styles.border} ${styles.bg} p-6 space-y-4`}>
      <div className="flex items-start gap-3">
        <div className={`w-9 h-9 rounded-xl border ${styles.border} flex items-center justify-center flex-shrink-0`}>
          <Icon className={`w-5 h-5 ${styles.iconClass}`} />
        </div>
        <div className="min-w-0 flex-1">
          <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border ${styles.badge}`}>
            {readiness.readiness_label || level}
          </span>
          <p className="text-white text-sm leading-relaxed mt-2">
            {readiness.executive_summary || 'Your uploads are being compared to the Day-1 plan.'}
          </p>
          {(readiness.ready_doctypes?.length ?? 0) > 0 && (
            <p className="text-xs text-gray-500 mt-2">
              Covered: {readiness.ready_doctypes!.slice(0, 8).join(', ')}
              {(readiness.ready_doctypes?.length ?? 0) > 8 ? '…' : ''}
            </p>
          )}
        </div>
      </div>

      {needsAck && canProceed && (
        <label className="flex gap-3 items-start p-4 rounded-xl border border-amber-500/20 bg-amber-500/5 cursor-pointer ml-12">
          <input
            type="checkbox"
            className="mt-0.5"
            checked={acknowledged}
            onChange={(e) => onAckChange(e.target.checked)}
          />
          <span className="text-sm text-gray-300 leading-relaxed">
            I have reviewed the coverage matrix and understand mapping may use assumptions for gaps.
          </span>
        </label>
      )}

      {canProceed && onProceed && (level === 'green' || (needsAck && acknowledged)) && (
        <div className="ml-12">
          <button
            type="button"
            disabled={proceeding || (needsAck && !acknowledged)}
            onClick={onProceed}
            className="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 disabled:opacity-40 text-black text-sm font-bold transition-colors"
          >
            {proceeding ? 'Continuing…' : 'Continue to mapping'}
          </button>
        </div>
      )}
    </div>
  );
}

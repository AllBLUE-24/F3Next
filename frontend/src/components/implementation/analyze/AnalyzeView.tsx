'use client';
// PATH: src/components/implementation/analyze/AnalyzeView.tsx

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight, CheckCircle, Sparkles, ChevronDown, AlertTriangle, Info, Upload } from 'lucide-react';
import { useAnalysis } from '@/hooks/implementation/useAnalysis';
import { BrainVisualizer } from './BrainVisualizer';
import { TaskStream } from './TaskStream';
import type { AnalysisTask } from '@/types/implementation';
import { getBaseApiUrl } from '@/lib/config';

// ── Niche display lookup ────────────────────────────────────────────────────
const NICHE_DISPLAY: Record<string, { label: string; industry: string }> = {
  trading:                          { label: 'Trading / Distribution', industry: 'trading' },
  trading_fmcg_distributor:         { label: 'FMCG Distribution', industry: 'trading' },
  trading_hardware_variants:        { label: 'Hardware / Building Materials', industry: 'trading' },
  trading_autoparts_highvolume:     { label: 'Auto Parts (High Volume)', industry: 'trading' },
  manufacturing:                    { label: 'Manufacturing', industry: 'manufacturing' },
  manufacturing_garment_variants:   { label: 'Garment Manufacturing', industry: 'manufacturing' },
  manufacturing_food_batch:         { label: 'Food / Batch Manufacturing', industry: 'manufacturing' },
  manufacturing_fabrication_jobshop:{ label: 'Metal Fabrication / Job Shop', industry: 'manufacturing' },
  manufacturing_project_chemical:   { label: 'Chemical Manufacturing', industry: 'manufacturing' },
  service:                          { label: 'Professional Services', industry: 'service' },
  service_professional:             { label: 'Professional Services', industry: 'service' },
};

const ALL_NICHES = Object.keys(NICHE_DISPLAY);

// ── DataReadinessGateCard ──────────────────────────────────────────────────
// Shown inline in the main content area when stage === 'awaiting_data_readiness_confirmation'.
// Fetches open supervisor prompts and renders tiered CRITICAL / IMPORTANT cards
// so the user never has to find the sidebar.

type DRAction = {
  id: string;
  type: string;
  scope?: string;
  question?: string;
  options?: string[];
  metadata?: {
    tier?: string;
    critical_gaps?: Array<{ doctype: string; reason: string }>;
    important_gaps?: Array<{ doctype: string; reason: string }>;
  };
};

type DRPrompt = {
  id: string;
  step: string;
  status: string;
  actions?: DRAction[];
};

function DataReadinessGateCard({ jobId, onDone }: { jobId: string; onDone: () => void }) {
  const [prompts, setPrompts] = useState<DRPrompt[]>([]);
  const [responding, setResponding] = useState(false);
  const [fetchErr, setFetchErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const base = getBaseApiUrl();
      const res = await fetch(`${base}/api/implementation/supervisor-prompts/${jobId}`, { cache: 'no-store' });
      if (!res.ok) return;
      const data = await res.json();
      const open = (Array.isArray(data?.prompts) ? data.prompts : []).filter(
        (p: DRPrompt) => p.status === 'open',
      );
      setPrompts(open);
    } catch { /* best-effort */ }
  }, [jobId]);

  useEffect(() => { load(); }, [load]);

  const respond = async (prompt: DRPrompt, action: DRAction, option: string) => {
    setResponding(true);
    setFetchErr(null);
    try {
      const base = getBaseApiUrl();
      const res = await fetch(`${base}/api/implementation/supervisor-prompts/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: jobId,
          prompt_id: prompt.id,
          chosen_action_id: action.id,
          extra_data: { selected_option: option },
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      onDone();
    } catch (e: unknown) {
      setFetchErr(e instanceof Error ? e.message : 'Failed to submit');
    } finally {
      setResponding(false);
    }
  };

  if (prompts.length === 0) {
    // No open prompts yet — loading or all resolved
    return (
      <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 flex items-center gap-3 animate-pulse">
        <div className="w-4 h-4 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
        <span className="text-sm text-gray-500">Loading data readiness assessment…</span>
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Section header */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-white/[0.06]" />
        <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-500">
          Your input is needed
        </span>
        <div className="flex-1 h-px bg-white/[0.06]" />
      </div>

      {prompts.map((p) => {
        const critAct = (p.actions || []).find((a) => a.type === 'ask_user' && a.metadata?.tier === 'critical');
        const impAct  = (p.actions || []).find((a) => a.type === 'ask_user' && a.metadata?.tier === 'important');
        const fallAct = (p.actions || []).find((a) => a.type === 'ask_user');

        return (
          <div key={p.id} className="space-y-3">
            {/* ── CRITICAL card ─────────────────────────────── */}
            {critAct && critAct.question && (
              <div className="rounded-2xl border border-red-500/25 bg-gradient-to-br from-red-950/40 via-transparent to-transparent p-6 space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-xl bg-red-500/15 border border-red-500/25 flex items-center justify-center flex-shrink-0">
                    <AlertTriangle className="w-5 h-5 text-red-400" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-red-400 bg-red-500/15 border border-red-500/25 px-2 py-0.5 rounded-full">
                        Critical — Required
                      </span>
                    </div>
                    <p className="text-white text-sm leading-relaxed">{critAct.question}</p>
                  </div>
                </div>

                {/* Affected doctypes */}
                {critAct.metadata?.critical_gaps && critAct.metadata.critical_gaps.length > 0 && (
                  <div className="ml-12 flex flex-wrap gap-2">
                    {critAct.metadata.critical_gaps.map((g) => (
                      <span
                        key={g.doctype}
                        className="text-xs bg-red-500/10 border border-red-500/20 text-red-300 px-3 py-1 rounded-full"
                      >
                        {g.doctype}
                      </span>
                    ))}
                  </div>
                )}

                {/* Actions — critical: no skip */}
                <div className="ml-12 space-y-2">
                  {(critAct.options || ['Upload the missing files']).map((opt) => (
                    <button
                      key={opt}
                      disabled={responding}
                      onClick={() => respond(p, critAct, opt)}
                      className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/25 hover:bg-red-500/20 text-red-100 text-sm font-semibold transition-all disabled:opacity-50"
                    >
                      <Upload className="w-4 h-4 shrink-0" />
                      {responding ? 'Submitting…' : opt}
                      <ArrowRight className="w-4 h-4 ml-auto opacity-50" />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* ── IMPORTANT card ────────────────────────────── */}
            {impAct && impAct.question && (
              <div className="rounded-2xl border border-amber-500/20 bg-gradient-to-br from-amber-950/30 via-transparent to-transparent p-6 space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-xl bg-amber-500/15 border border-amber-500/25 flex items-center justify-center flex-shrink-0">
                    <Info className="w-5 h-5 text-amber-400" />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-amber-400 bg-amber-500/15 border border-amber-500/25 px-2 py-0.5 rounded-full">
                        Recommended — Industry best practice
                      </span>
                    </div>
                    <p className="text-gray-300 text-sm leading-relaxed">{impAct.question}</p>
                  </div>
                </div>

                {impAct.metadata?.important_gaps && impAct.metadata.important_gaps.length > 0 && (
                  <div className="ml-12 flex flex-wrap gap-2">
                    {impAct.metadata.important_gaps.map((g) => (
                      <span
                        key={g.doctype}
                        className="text-xs bg-amber-500/10 border border-amber-500/20 text-amber-300 px-3 py-1 rounded-full"
                      >
                        {g.doctype}
                      </span>
                    ))}
                  </div>
                )}

                <div className="ml-12 space-y-2">
                  {(impAct.options || []).map((opt) => {
                    const isUpload = opt.toLowerCase().includes('upload');
                    return (
                      <button
                        key={opt}
                        disabled={responding}
                        onClick={() => respond(p, impAct, opt)}
                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all disabled:opacity-50 ${
                          isUpload
                            ? 'bg-amber-500/10 border border-amber-500/25 hover:bg-amber-500/20 text-amber-100'
                            : 'bg-white/[0.03] border border-white/[0.08] hover:bg-white/[0.06] text-gray-400'
                        }`}
                      >
                        {isUpload ? <Upload className="w-4 h-4 shrink-0" /> : <ArrowRight className="w-4 h-4 shrink-0" />}
                        {responding ? 'Submitting…' : opt}
                        {!isUpload && (
                          <span className="ml-auto text-[10px] text-gray-600 font-normal normal-case">
                            not recommended
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Fallback: no tiered actions */}
            {!critAct && !impAct && fallAct && fallAct.question && (
              <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6 space-y-4">
                <p className="text-white text-sm leading-relaxed">{fallAct.question}</p>
                <div className="space-y-2">
                  {(fallAct.options || []).map((opt) => (
                    <button
                      key={opt}
                      disabled={responding}
                      onClick={() => respond(p, fallAct, opt)}
                      className="w-full text-left px-4 py-3 rounded-xl bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.07] text-gray-200 text-sm transition-all disabled:opacity-50"
                    >
                      {responding ? 'Submitting…' : opt}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })}

      {fetchErr && (
        <p className="text-xs text-red-400 font-mono px-1">{fetchErr}</p>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

interface Props {
  jobId: string;
  validateHref: string;
  devTasks?: AnalysisTask[]; // injected in dev mode — bypasses polling
}


export function AnalyzeView({ jobId, validateHref, devTasks }: Props) {
  const live = useAnalysis(devTasks ? null : jobId); // skip polling if devTasks provided
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [selectedNiche, setSelectedNiche] = useState<string | null>(null);
  const [showDropdown, setShowDropdown] = useState(false);

  // FIX: Added `?? []` so it never tries to run .filter() on undefined!
  const tasks    = devTasks ?? live.tasks ?? [];
  const profile  = live.profile;
  const isDone   = devTasks ? false : (live.isComplete || live.stage === 'awaiting_validation_submission');
  const stage    = live.stage;

  // When stage reaches f3iche_confirmation, pre-select the inferred niche
  useEffect(() => {
    if (stage === 'awaiting_f3iche_confirmation' && live.inferredNiche && !selectedNiche) {
      setSelectedNiche(live.inferredNiche);
    }
  }, [stage, live.inferredNiche, selectedNiche]);

  const doneTasks  = tasks.filter((t) => t.status === 'done').length;
  const totalTasks = tasks.filter((t) => t.status !== 'idle').length || 1;
  const pct        = Math.round((doneTasks / totalTasks) * 100);

  // Auto-advance only in real mode when analysis is fully complete
  useEffect(() => {
    if (!devTasks && isDone) {
      const t = setTimeout(() => router.push(`${validateHref}?jobId=${jobId}`), 1800);
      return () => clearTimeout(t);
    }
  }, [devTasks, isDone, router, validateHref, jobId]);

  // ── F3iche confirmation handler ─────────────────────────────────────────
  const handleConfirmF3iche = useCallback(async () => {
    if (!selectedNiche || confirming) return;
    setConfirming(true);
    try {
      const API_BASE = getBaseApiUrl();
      const nicheInfo = NICHE_DISPLAY[selectedNiche] || { label: selectedNiche, industry: 'trading' };
      const res = await fetch(`${API_BASE}/api/implementation/signal/f3iche-confirmed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: jobId,
          f3iche_user: selectedNiche,
          industry: nicheInfo.industry,
        }),
      });
      if (!res.ok) throw new Error('Failed to confirm F3iche');
      // Restart polling (hook will pick up stage change automatically)
      live.refresh();
    } catch (err) {
      console.error('F3iche confirmation failed:', err);
    } finally {
      setConfirming(false);
    }
  }, [selectedNiche, confirming, jobId]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-500 mb-2">Step 02 of 04</p>
        <h1 className="text-3xl font-black text-white mb-3">
          {isDone ? 'Analysis complete.' : 'Analyzing your data.'}
        </h1>
        <p className="text-gray-500 text-base leading-relaxed">
          {isDone
            ? 'We\'ve built your company profile. Review it in the next step.'
            : stage === 'awaiting_f3iche_confirmation'
              ? 'We\'ve identified your business type. Please confirm to continue.'
              : 'Our agent is reading your files, mapping your data, and building your company profile.'}
        </p>
        {devTasks && (
          <p className="mt-2 text-xs font-mono text-amber-600 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-1.5 inline-block">
            DEV MODE — showing mock tasks, polling disabled
          </p>
        )}
      </div>

      {/* Brain canvas */}
      <div className="relative rounded-2xl overflow-hidden border border-white/[0.06] bg-[#0D0D14]">
        <BrainVisualizer isActive={!isDone && stage !== 'awaiting_f3iche_confirmation'} />
        <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isDone ? (
              <CheckCircle className="w-4 h-4 text-green-400" />
            ) : (stage === 'awaiting_f3iche_confirmation' || stage === 'awaiting_mapping_confirmation') ? (
              <Sparkles className="w-4 h-4 text-amber-400" />
            ) : (
              <div className="w-4 h-4 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
            )}
            <span className="text-xs font-mono text-gray-500">
              {isDone ? 'Agent finished' : (stage === 'awaiting_f3iche_confirmation' || stage === 'awaiting_mapping_confirmation') ? 'Waiting for your confirmation' : 'Agent is thinking…'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-28 h-1 bg-white/[0.06] rounded-full overflow-hidden">
              <div
                className="h-full bg-amber-500 rounded-full transition-all duration-700"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs font-mono text-gray-600 tabular-nums w-8 text-right">{pct}%</span>
          </div>
        </div>
      </div>

      {/* Task stream */}
      <TaskStream tasks={tasks} />

      {/* ══════════════════════════════════════════════════════════════════════
          DATA READINESS GATE — appears inline when the workflow is blocked
          waiting for the user to provide or confirm missing data.
         ══════════════════════════════════════════════════════════════════ */}
      {stage === 'awaiting_data_readiness_confirmation' && (
        <DataReadinessGateCard jobId={jobId} onDone={live.refresh} />
      )}


      {/* ══════════════════════════════════════════════════════════════════════
          F3ICHE CONFIRMATION CARD — appears when workflow is waiting for signal
         ══════════════════════════════════════════════════════════════════════ */}
      {stage === 'awaiting_f3iche_confirmation' && (
        <div className="bg-gradient-to-br from-amber-500/10 via-transparent to-transparent border border-amber-500/20 rounded-2xl p-6 space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h3 className="text-white font-bold text-lg">Business type detected</h3>
              <p className="text-gray-400 text-sm mt-1">
                We analyzed your files and identified your business type.
                {live.confidence !== null && (
                  <span className="text-amber-400 ml-1 font-medium">{(live.confidence * 100).toFixed(0)}% confidence</span>
                )}
              </p>
            </div>
          </div>

          {/* Niche selector */}
          <div className="relative">
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              className="w-full flex items-center justify-between px-4 py-3 bg-white/[0.04] border border-white/10 rounded-xl text-left hover:border-amber-500/30 transition-colors"
            >
              <span className="text-white font-medium">
                {selectedNiche ? (NICHE_DISPLAY[selectedNiche]?.label || selectedNiche) : 'Select business type...'}
              </span>
              <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${showDropdown ? 'rotate-180' : ''}`} />
            </button>

            {showDropdown && (
              <div className="absolute z-20 mt-1 w-full bg-[#1a1a2e] border border-white/10 rounded-xl shadow-2xl max-h-64 overflow-y-auto">
                {ALL_NICHES.map((niche) => (
                  <button
                    key={niche}
                    onClick={() => { setSelectedNiche(niche); setShowDropdown(false); }}
                    className={`w-full text-left px-4 py-2.5 text-sm hover:bg-white/[0.06] transition-colors first:rounded-t-xl last:rounded-b-xl ${
                      selectedNiche === niche
                        ? 'text-amber-400 bg-amber-500/10'
                        : 'text-gray-300'
                    }`}
                  >
                    {NICHE_DISPLAY[niche]?.label || niche}
                    <span className="ml-2 text-xs text-gray-600 capitalize">{NICHE_DISPLAY[niche]?.industry}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Confirm button */}
          <button
            onClick={handleConfirmF3iche}
            disabled={!selectedNiche || confirming}
            className="w-full py-3 px-4 bg-amber-500 hover:bg-amber-400 disabled:bg-amber-500/30 disabled:cursor-not-allowed text-black font-bold rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            {confirming ? (
              <>
                <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                Confirming...
              </>
            ) : (
              <>Confirm &amp; Continue</>
            )}
          </button>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          MAPPING CONFIRMATION CARD
         ══════════════════════════════════════════════════════════════════════ */}
      {stage === 'awaiting_mapping_confirmation' && (
        <div className="bg-gradient-to-br from-green-500/10 via-transparent to-transparent border border-green-500/20 rounded-2xl p-6 space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-green-500/20 flex items-center justify-center flex-shrink-0">
              <CheckCircle className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <h3 className="text-white font-bold text-lg">Initial Mapping Complete</h3>
              <p className="text-gray-400 text-sm mt-1">
                Our agent has completed the first pass at mapping your uploaded files to the target ERPNext modules. Please confirm to proceed to final validation.
              </p>
            </div>
          </div>

          <button
            onClick={async () => {
              if (confirming) return;
              setConfirming(true);
              try {
                const API_BASE = getBaseApiUrl();
                const res = await fetch(`${API_BASE}/api/implementation/signal/mapping-confirmed`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    project_id: jobId,
                    approved: true,
                    user_feedback: ""
                  }),
                });
                if (!res.ok) throw new Error('Failed to confirm mapping');
                live.refresh();
              } catch (err) {
                console.error(err);
              } finally {
                setConfirming(false);
              }
            }}
            disabled={confirming}
            className="w-full py-3 px-4 bg-green-500 hover:bg-green-400 disabled:bg-green-500/30 disabled:cursor-not-allowed text-black font-bold rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            {confirming ? (
              <>
                <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                Approving...
              </>
            ) : (
              <>Approve Mappings &amp; Validate</>
            )}
          </button>
        </div>
      )}

      {/* Emerging profile teaser */}
      {profile && (
        <div className="bg-white/[0.02] border border-amber-500/20 rounded-xl p-5">
          <p className="text-xs font-bold uppercase tracking-widest text-amber-500 mb-3">Profile emerging</p>
          <div className="grid grid-cols-2 gap-3 text-xs">
            {[
              ['Company', profile.name || 'Detecting...'],
              ['Industry', profile.industry || 'Detecting...'],
              ['Currency', profile.currency || 'Detecting...'],
              // 👇 FIX: Safely fallback to an empty array before slicing! 👇
              ['Modules', (profile.modules || []).slice(0, 3).join(', ') + ((profile.modules || []).length > 3 ? '…' : '')],
            ].map(([k, v]) => (
              <div key={k as string}>
                <span className="text-gray-700">{k}</span>
                <p className="text-white font-medium mt-0.5">{v}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {isDone && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-green-500/10 border border-green-500/20">
          <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
          <p className="text-sm text-green-400">Analysis complete. Taking you to validation…</p>
          <ArrowRight className="w-4 h-4 text-green-400 ml-auto animate-pulse" />
        </div>
      )}

      {stage === 'error' && (
        <div className="flex items-center gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20">
          <p className="text-sm text-red-400">An error occurred during analysis. Please try again.</p>
        </div>
      )}

      {!devTasks && live.error && (
        <p className="text-xs text-red-400 font-mono">{live.error}</p>
      )}
    </div>
  );
}
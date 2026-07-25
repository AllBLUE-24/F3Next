'use client';
// PATH: src/components/implementation/analyze/AnalyzeView.tsx

import { useCallback, useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { ArrowRight, CheckCircle, Sparkles, AlertTriangle, Info, Upload, X } from 'lucide-react';
import { useAnalysis } from '@/hooks/implementation/useAnalysis';
import { BrainVisualizer } from './BrainVisualizer';
import { TaskStream } from './TaskStream';
import type { AnalysisTask } from '@/types/implementation';
import { getBaseApiUrl } from '@/lib/config';
import { SupervisorInlineUploader } from '../supervisor/SupervisorInlineUploader';
import { ReadinessMatrixTable, type ReadinessMatrixRow } from './ReadinessMatrixTable';
import { ReadinessBanner, type ReadinessUiPayload } from './ReadinessBanner';

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

type SessionSummary = {
  batch_count?: number;
  total_files?: number;
  user_import_note?: string | null;
  file_batches?: Array<{
    batch_index?: number;
    uploaded_at?: string;
    note?: string;
    files?: Array<{ file_name?: string; object_path?: string }>;
  }>;
} | null;

function DataReadinessGateCard({
  jobId,
  onDone,
  sessionSummary,
  requireAckForContinue = false,
  acknowledged = true,
}: {
  jobId: string;
  onDone: () => void;
  sessionSummary?: SessionSummary;
  requireAckForContinue?: boolean;
  acknowledged?: boolean;
}) {
  const [prompts, setPrompts] = useState<DRPrompt[]>([]);
  const [responding, setResponding] = useState(false);
  const [fetchErr, setFetchErr] = useState<string | null>(null);
  const [activeUpload, setActiveUpload] = useState<{ promptId: string; actionId: string; selectedOption: string } | null>(null);
  const [assistantNote, setAssistantNote] = useState("");

  const params = useParams<{ companySlug: string }>();
  const companySlug = params?.companySlug || 'unknown';

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
    const isContinue = option.toLowerCase().includes('continue');
    if (isContinue && requireAckForContinue && !acknowledged) {
      setFetchErr('Please review the coverage matrix and check the acknowledgment box first.');
      return;
    }
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
          extra_data: {
            selected_option: option,
            ...(assistantNote.trim() ? { user_note: assistantNote.trim() } : {}),
          },
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
            {sessionSummary && (sessionSummary.batch_count ?? 0) > 1 && (
              <div className="rounded-xl border border-amber-500/15 bg-amber-500/[0.05] px-4 py-3 text-[11px] text-amber-200">
                Re-upload round {sessionSummary.batch_count} is active. {sessionSummary.total_files ?? 0} files are currently in the union.
              </div>
            )}
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
                  {activeUpload?.promptId === p.id && activeUpload?.actionId === critAct.id ? (
                    <SupervisorInlineUploader
                      projectId={jobId}
                      companySlug={companySlug}
                      promptId={p.id}
                      actionId={critAct.id}
                      selectedOption={activeUpload.selectedOption}
                      userNote={assistantNote.trim()}
                      onSuccess={() => {
                        setActiveUpload(null);
                        setAssistantNote("");
                        onDone();
                      }}
                      onCancel={() => setActiveUpload(null)}
                    />
                  ) : (
                    (critAct.options || ['Upload the missing files']).map((opt) => (
                      <button
                        key={opt}
                        disabled={responding}
                        onClick={() => {
                          if (opt.toLowerCase().includes("upload")) {
                            setActiveUpload({ promptId: p.id, actionId: critAct.id, selectedOption: opt });
                          } else {
                            respond(p, critAct, opt);
                          }
                        }}
                        className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/25 hover:bg-red-500/20 text-red-100 text-sm font-semibold transition-all disabled:opacity-50"
                      >
                        <Upload className="w-4 h-4 shrink-0" />
                        {responding ? 'Submitting…' : opt}
                        <ArrowRight className="w-4 h-4 ml-auto opacity-50" />
                      </button>
                    ))
                  )}
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
                  {activeUpload?.promptId === p.id && activeUpload?.actionId === impAct.id ? (
                    <SupervisorInlineUploader
                      projectId={jobId}
                      companySlug={companySlug}
                      promptId={p.id}
                      actionId={impAct.id}
                      selectedOption={activeUpload.selectedOption}
                      userNote={assistantNote.trim()}
                      onSuccess={() => {
                        setActiveUpload(null);
                        setAssistantNote("");
                        onDone();
                      }}
                      onCancel={() => setActiveUpload(null)}
                    />
                  ) : (
                    (impAct.options || []).map((opt) => {
                      const isUpload = opt.toLowerCase().includes('upload');
                      const isContinue = opt.toLowerCase().includes('continue');
                      const blocked = isContinue && requireAckForContinue && !acknowledged;
                      return (
                        <button
                          key={opt}
                          disabled={responding || blocked}
                          onClick={() => {
                            if (isUpload) {
                            setActiveUpload({ promptId: p.id, actionId: impAct.id, selectedOption: opt });
                            } else {
                            respond(p, impAct, opt);
                            }
                          }}
                          title={blocked ? 'Acknowledge the coverage review first' : undefined}
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
                    })
                  )}
                </div>
              </div>
            )}

            {/* Fallback: no tiered actions */}
            {!critAct && !impAct && fallAct && fallAct.question && (
              <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-6 space-y-4">
                <p className="text-white text-sm leading-relaxed">{fallAct.question}</p>
                <div className="space-y-2">
                  {(fallAct.options || []).map((opt) => {
                    const isContinue = opt.toLowerCase().includes('continue');
                    const blocked = isContinue && requireAckForContinue && !acknowledged;
                    return (
                    <button
                      key={opt}
                      disabled={responding || blocked}
                      onClick={() => respond(p, fallAct, opt)}
                      title={blocked ? 'Acknowledge the coverage review first' : undefined}
                      className="w-full text-left px-4 py-3 rounded-xl bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.07] text-gray-200 text-sm transition-all disabled:opacity-50"
                    >
                      {responding ? 'Submitting…' : opt}
                    </button>
                    );
                  })}
                </div>
              </div>
            )}
            <div className="space-y-1.5">
              <label className="block text-[10px] uppercase tracking-wider text-gray-600">
                Add a note for the assistant
              </label>
              <textarea
                value={assistantNote}
                onChange={(e) => setAssistantNote(e.target.value)}
                placeholder="Optional clarification before you respond."
                maxLength={800}
                className="w-full min-h-[72px] rounded-xl bg-black/20 border border-white/[0.08] px-3 py-2 text-sm text-white placeholder:text-gray-600 outline-none focus:border-amber-500/40 resize-y"
              />
            </div>
          </div>
        );
      })}

      {fetchErr && (
        <p className="text-xs text-red-400 font-mono px-1">{fetchErr}</p>
      )}
    </div>
  );
}

// ── Readiness panel (matrix + banner) ───────────────────────────────────────

function ReadinessPanel({
  jobId,
  onRefresh,
  onAckChange,
  acknowledged,
  onRequiresAckChange,
}: {
  jobId: string;
  onRefresh: () => void;
  onAckChange: (v: boolean) => void;
  acknowledged: boolean;
  onRequiresAckChange?: (v: boolean) => void;
}) {
  const [readiness, setReadiness] = useState<(ReadinessUiPayload & { matrix?: { rows?: ReadinessMatrixRow[] } }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [proceeding, setProceeding] = useState(false);

  const load = useCallback(async () => {
    try {
      const base = getBaseApiUrl();
      const res = await fetch(`${base}/api/implementation/readiness/${jobId}`, { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        const payload = data?.readiness ?? null;
        setReadiness(payload);
        onRequiresAckChange?.(payload?.requires_acknowledgment === true);
      }
    } catch {
      /* best-effort */
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => { load(); }, [load]);

  const handleProceed = async () => {
    setProceeding(true);
    try {
      const base = getBaseApiUrl();
      await fetch(`${base}/api/implementation/readiness/decisions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: jobId,
          decision: readiness?.readiness_level === 'yellow' ? 'acknowledge_yellow' : 'proceed',
        }),
      });
      onRefresh();
    } catch {
      /* supervisor path may still handle continue */
    } finally {
      setProceeding(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6 flex items-center gap-3 animate-pulse">
        <div className="w-4 h-4 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
        <span className="text-sm text-gray-500">Building readiness matrix…</span>
      </div>
    );
  }

  if (!readiness) return null;

  return (
    <div className="space-y-4">
      <ReadinessBanner
        readiness={readiness}
        acknowledged={acknowledged}
        onAckChange={onAckChange}
        onProceed={handleProceed}
        proceeding={proceeding}
      />
      <ReadinessMatrixTable rows={readiness.matrix?.rows ?? []} />
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
  const [confirmedF3iche, setConfirmedF3iche] = useState(false);
  const [confirmedMapping, setConfirmedMapping] = useState(false);
  const [showCorrection, setShowCorrection] = useState(false);
  const [correctionText, setCorrectionText] = useState('');
  const [readinessAcked, setReadinessAcked] = useState(false);
  const [readinessNeedsAck, setReadinessNeedsAck] = useState(false);

  // FIX: Added `?? []` so it never tries to run .filter() on undefined!
  const tasks    = devTasks ?? live.tasks ?? [];
  const profile  = live.profile;
  const stage    = live.stage;
  const pipelineReady = !devTasks && stage === 'awaiting_validation_submission';
  const isDone   = devTasks ? false : live.isComplete;
  const showComplete = isDone || pipelineReady;

  const f3icheProposal = live.f3icheConfirmation;

  // Clear confirm locks once workflow advances past each gate
  useEffect(() => {
    if (stage && stage !== 'awaiting_f3iche_confirmation') {
      setConfirmedF3iche(false);
    }
  }, [stage]);

  useEffect(() => {
    if (stage && stage !== 'awaiting_mapping_confirmation') {
      setConfirmedMapping(false);
    }
  }, [stage]);

  useEffect(() => {
    if (pipelineReady && validateHref && jobId) {
      router.replace(`${validateHref}?jobId=${encodeURIComponent(jobId)}`);
    }
  }, [pipelineReady, validateHref, jobId, router]);

  const doneTasks  = tasks.filter((t) => t.status === 'done').length;
  const totalTasks = tasks.filter((t) => t.status !== 'idle').length || 1;
  const pct        = Math.round((doneTasks / totalTasks) * 100);

  const submitF3icheConfirmation = useCallback(async (accepted: boolean) => {
    if (confirming) return;
    if (!accepted && !correctionText.trim()) return;
    setConfirming(true);
    try {
      const API_BASE = getBaseApiUrl();
      const res = await fetch(`${API_BASE}/api/implementation/signal/f3iche-confirmed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: jobId,
          accepted,
          correction_text: accepted ? undefined : correctionText.trim(),
        }),
      });
      if (!res.ok) throw new Error('Failed to confirm business type');
      setConfirmedF3iche(true);
      setShowCorrection(false);
      live.refresh();
    } catch (err) {
      console.error('F3iche confirmation failed:', err);
    } finally {
      setConfirming(false);
    }
  }, [confirming, correctionText, jobId, live]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-500 mb-2">Step 02 of 04</p>
        <h1 className="text-3xl font-black text-white mb-3">
          {showComplete ? 'Analysis complete.' : 'Analyzing your data.'}
        </h1>
        <p className="text-gray-500 text-base leading-relaxed">
          {showComplete
            ? 'We\'ve built your company profile. Continue to validation when you\'re ready.'
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
        <BrainVisualizer isActive={!showComplete && stage !== 'awaiting_f3iche_confirmation'} />
        <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {showComplete ? (
              <CheckCircle className="w-4 h-4 text-green-400" />
            ) : (stage === 'awaiting_f3iche_confirmation' || stage === 'awaiting_mapping_confirmation') ? (
              <Sparkles className="w-4 h-4 text-amber-400" />
            ) : (
              <div className="w-4 h-4 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
            )}
            <span className="text-xs font-mono text-gray-500">
              {showComplete ? 'Agent finished' : (stage === 'awaiting_f3iche_confirmation' || stage === 'awaiting_mapping_confirmation') ? 'Waiting for your confirmation' : 'Agent is thinking…'}
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

      {live.session && (live.session.batch_count ?? 0) > 1 && (
        <div className="rounded-2xl border border-amber-500/15 bg-amber-500/[0.05] px-4 py-3 text-sm text-amber-100">
          Re-upload round {live.session.batch_count} detected. The workflow is using {live.session.total_files ?? 0} files across all upload waves.
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          DATA READINESS GATE — appears inline when the workflow is blocked
          waiting for the user to provide or confirm missing data.
         ══════════════════════════════════════════════════════════════════ */}
      {stage === 'awaiting_data_readiness_confirmation' && (
        <>
          <ReadinessPanel
            jobId={jobId}
            onRefresh={live.refresh}
            acknowledged={readinessAcked}
            onAckChange={setReadinessAcked}
            onRequiresAckChange={setReadinessNeedsAck}
          />
          <DataReadinessGateCard
            jobId={jobId}
            onDone={live.refresh}
            sessionSummary={live.session}
            requireAckForContinue={readinessNeedsAck}
            acknowledged={readinessAcked}
          />
        </>
      )}


      {/* ══════════════════════════════════════════════════════════════════════
          F3ICHE CONFIRMATION CARD — appears when workflow is waiting for signal
         ══════════════════════════════════════════════════════════════════════ */}
      {stage === 'awaiting_f3iche_confirmation' && confirmedF3iche && (
        <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-5 py-4">
          <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0" />
          <p className="text-sm text-emerald-300">Business type confirmed — continuing analysis…</p>
        </div>
      )}

      {stage === 'awaiting_f3iche_confirmation' && !confirmedF3iche && (
        <div className="bg-gradient-to-br from-amber-500/10 via-transparent to-transparent border border-amber-500/20 rounded-2xl p-6 space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h3 className="text-white font-bold text-lg">Confirm your business type</h3>
              {f3icheProposal?.display_name && (
                <p className="text-amber-300 text-sm font-medium mt-1">{f3icheProposal.display_name}</p>
              )}
              {live.confidence !== null && (
                <p className="text-gray-500 text-xs mt-1">{(live.confidence * 100).toFixed(0)}% confidence</p>
              )}
            </div>
          </div>

          <p className="text-gray-300 text-sm leading-relaxed">
            {f3icheProposal?.confirmation_message ||
              'We are analyzing your files and discovery context. The confirmation message will appear shortly.'}
          </p>

          {(f3icheProposal?.evidence_from_files?.length ?? 0) > 0 && (
            <div className="text-xs text-gray-500 space-y-1">
              <p className="font-semibold text-gray-400 uppercase tracking-wide">From your files</p>
              <ul className="list-disc list-inside space-y-0.5">
                {f3icheProposal!.evidence_from_files!.slice(0, 4).map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}

          {(f3icheProposal?.evidence_from_discovery?.length ?? 0) > 0 && (
            <div className="text-xs text-gray-500 space-y-1">
              <p className="font-semibold text-gray-400 uppercase tracking-wide">From discovery</p>
              <ul className="list-disc list-inside space-y-0.5">
                {f3icheProposal!.evidence_from_discovery!.slice(0, 3).map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}

          {(f3icheProposal?.conflicts?.length ?? 0) > 0 && (
            <div className="flex items-start gap-2 text-amber-400/90 text-xs bg-amber-500/5 border border-amber-500/15 rounded-lg px-3 py-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <p>{f3icheProposal!.conflicts!.join(' ')}</p>
            </div>
          )}

          {!showCorrection ? (
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => submitF3icheConfirmation(true)}
                disabled={!f3icheProposal?.proposed_f3iche || confirming}
                className="flex-1 py-3 px-4 bg-amber-500 hover:bg-amber-400 disabled:bg-amber-500/30 disabled:cursor-not-allowed text-black font-bold rounded-xl transition-colors"
              >
                {confirming ? 'Confirming…' : 'Yes, that\'s right'}
              </button>
              <button
                type="button"
                onClick={() => setShowCorrection(true)}
                disabled={confirming}
                className="flex-1 py-3 px-4 bg-white/[0.04] border border-white/10 hover:border-white/20 text-gray-300 font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
              >
                <X className="w-4 h-4" />
                No, not quite
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              <textarea
                value={correctionText}
                onChange={(e) => setCorrectionText(e.target.value)}
                placeholder="Tell us what we got wrong — e.g. we manufacture coatings and run installation projects, not pure trading."
                rows={3}
                className="w-full px-4 py-3 bg-white/[0.04] border border-white/10 rounded-xl text-sm text-white placeholder:text-gray-600 resize-none focus:outline-none focus:border-amber-500/40"
              />
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => submitF3icheConfirmation(false)}
                  disabled={!correctionText.trim() || confirming}
                  className="flex-1 py-3 px-4 bg-amber-500 hover:bg-amber-400 disabled:opacity-40 text-black font-bold rounded-xl"
                >
                  {confirming ? 'Sending…' : 'Submit correction'}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowCorrection(false); setCorrectionText(''); }}
                  className="px-4 py-3 text-gray-500 hover:text-gray-300 text-sm"
                >
                  Back
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════
          MAPPING CONFIRMATION CARD
         ══════════════════════════════════════════════════════════════════════ */}
      {stage === 'awaiting_mapping_confirmation' && confirmedMapping && (
        <div className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-5 py-4">
          <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0" />
          <p className="text-sm text-emerald-300">Mappings approved — proceeding to validation…</p>
        </div>
      )}

      {stage === 'awaiting_mapping_confirmation' && !confirmedMapping && (
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
                setConfirmedMapping(true);
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

      {pipelineReady && (
        <button
          type="button"
          onClick={() => router.push(`${validateHref}?jobId=${jobId}`)}
          className="w-full flex items-center gap-3 p-4 rounded-xl bg-green-500/10 border border-green-500/20 hover:bg-green-500/15 transition-colors text-left"
        >
          <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
          <p className="text-sm text-green-400">Mapping and validation are ready. Review your data before import.</p>
          <ArrowRight className="w-4 h-4 text-green-400 ml-auto" />
        </button>
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
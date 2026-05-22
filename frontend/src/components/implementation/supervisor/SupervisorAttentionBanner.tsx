"use client";

/**
 * SupervisorAttentionBanner
 *
 * A full-width, sticky banner that appears at the TOP of the implementation
 * shell whenever there are open supervisor prompts requiring user input.
 *
 * This solves the core UX problem: the supervisor panel is hidden on the right
 * and users scroll past it without realising the workflow is blocked waiting
 * for their input.
 *
 * Behaviour:
 *   - Polls supervisor-prompts API every 5s (lightweight: just checking count).
 *   - When openPrompts.length > 0: shows a non-dismissible sticky banner.
 *   - The banner shows the first critical message inline (above the fold).
 *   - On smaller screens (xl:hidden), includes a "View details" expand area
 *     that shows the full prompt card inline so users don't need the sidebar.
 *   - When no open prompts: renders nothing (zero height, no layout shift).
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Info, Upload, ChevronDown, ChevronUp, ArrowRight } from "lucide-react";
import { getBaseApiUrl } from "@/lib/config";
import { useImplementation } from "@/contexts/ImplementationContext";
import { SupervisorInlineUploader } from "./SupervisorInlineUploader";

type ActionTier = "critical" | "important" | string;

type SupervisorAction = {
  id: string;
  type: string;
  scope?: string;
  question?: string;
  options?: string[];
  metadata?: {
    tier?: ActionTier;
    critical_gaps?: Array<{ doctype: string; reason: string }>;
    important_gaps?: Array<{ doctype: string; reason: string }>;
    missing_required_fields?: string[];
  };
};

type SupervisorPrompt = {
  id: string;
  step: string;
  status: string;
  summary_for_ui?: string | null;
  actions?: SupervisorAction[];
};

type SessionSummary = {
  batch_count?: number;
  total_files?: number;
} | null;

export function SupervisorAttentionBanner() {
  const { session } = useImplementation();
  const projectId = session.id;

  const [prompts, setPrompts] = useState<SupervisorPrompt[]>([]);
  const [expanded, setExpanded] = useState(false);
  const [responding, setResponding] = useState(false);
  const [respondError, setRespondError] = useState<string | null>(null);
  const [activeUpload, setActiveUpload] = useState<{ promptId: string; actionId: string; selectedOption: string } | null>(null);
  const [assistantNote, setAssistantNote] = useState("");
  const [sessionSummary, setSessionSummary] = useState<SessionSummary>(null);

  const openPrompts = useMemo(
    () => prompts.filter((p) => p.status === "open"),
    [prompts]
  );

  const poll = useCallback(async () => {
    if (!projectId) return;
    try {
      const base = getBaseApiUrl();
      const [res, stateRes] = await Promise.all([
        fetch(`${base}/api/implementation/supervisor-prompts/${projectId}`, { cache: "no-store" }),
        fetch(`${base}/api/implementation/state/${projectId}`, { cache: "no-store" }),
      ]);
      if (!res.ok) return;
      const data = await res.json();
      setPrompts(Array.isArray(data?.prompts) ? data.prompts : []);
      if (stateRes.ok) {
        const stateData = await stateRes.json();
        setSessionSummary(stateData?.session ?? null);
      }
    } catch {
      // silent — banner is best-effort, never blocks the main flow
    }
  }, [projectId]);

  useEffect(() => {
    poll();
    const interval = setInterval(poll, 5000);
    return () => clearInterval(interval);
  }, [poll]);

  const respond = useCallback(
    async (prompt: SupervisorPrompt, action: SupervisorAction, option?: string) => {
      setResponding(true);
      setRespondError(null);
      try {
        const base = getBaseApiUrl();
        const res = await fetch(`${base}/api/implementation/supervisor-prompts/respond`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: projectId,
            prompt_id: prompt.id,
            chosen_action_id: action.id,
            extra_data: {
              ...(option ? { selected_option: option } : {}),
              ...(assistantNote.trim() ? { user_note: assistantNote.trim() } : {}),
            },
          }),
        });
        if (!res.ok) throw new Error(await res.text());
        await poll(); // immediately refresh
        setExpanded(false);
      } catch (e: unknown) {
        setRespondError(e instanceof Error ? e.message : "Failed to submit response");
      } finally {
        setResponding(false);
      }
    },
    [assistantNote, projectId, poll]
  );

  // Nothing to show
  if (openPrompts.length === 0) return null;

  // Pick the most important prompt to surface inline
  const primary = openPrompts[0];
  const criticalAction = (primary.actions || []).find(
    (a) => a.type === "ask_user" && a.metadata?.tier === "critical"
  );
  const importantAction = (primary.actions || []).find(
    (a) => a.type === "ask_user" && a.metadata?.tier === "important"
  );
  const primaryAction = criticalAction ?? importantAction;
  const isCritical = !!criticalAction;

  const bannerBg = isCritical
    ? "bg-red-950/60 border-red-500/40"
    : "bg-amber-950/50 border-amber-500/30";
  const iconColor = isCritical ? "text-red-400" : "text-amber-400";
  const BannerIcon = isCritical ? AlertTriangle : Info;
  const badgeBg = isCritical
    ? "bg-red-500/20 text-red-300 border-red-500/30"
    : "bg-amber-500/20 text-amber-300 border-amber-500/30";

  // Inline message — first sentence of the question, capped for the banner
  const shortMsg = primaryAction?.question
    ? primaryAction.question.split(".")[0] + "."
    : isCritical
    ? "Critical data is missing. The pipeline is paused until you provide the required files."
    : "Some recommended data is missing for your industry setup.";

  return (
    <div
      className={`w-full border-b ${bannerBg} backdrop-blur-sm shrink-0 z-40`}
      role="alert"
      aria-live="assertive"
    >
      {/* ── Main banner row ──────────────────────────────── */}
      <div className="flex items-center gap-3 px-5 py-3">
        {/* Icon */}
        <div
          className={`w-7 h-7 rounded-lg border ${badgeBg} flex items-center justify-center shrink-0`}
        >
          <BannerIcon className={`w-4 h-4 ${iconColor}`} />
        </div>

        {/* Badge + message */}
        <div className="flex-1 min-w-0 flex flex-wrap items-center gap-x-3 gap-y-0.5">
          <span
            className={`text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border ${badgeBg}`}
          >
            {isCritical ? "Action required" : "Recommendation"}
          </span>
          <p className="text-sm text-white/90 truncate">{shortMsg}</p>
          {sessionSummary && (sessionSummary.batch_count ?? 0) > 1 && (
            <span className="text-[10px] font-mono text-amber-300/80">
              {sessionSummary.batch_count} upload waves · {sessionSummary.total_files ?? 0} files
            </span>
          )}
        </div>

        {/* Count badge */}
        {openPrompts.length > 1 && (
          <span className="text-xs font-mono text-zinc-400 shrink-0">
            +{openPrompts.length - 1} more
          </span>
        )}

        {/* Expand toggle */}
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-1 text-xs font-medium text-white/70 hover:text-white transition-colors shrink-0 px-2 py-1 rounded-lg hover:bg-white/[0.06]"
        >
          {expanded ? (
            <>
              <span>Collapse</span>
              <ChevronUp className="w-3.5 h-3.5" />
            </>
          ) : (
            <>
              <span>View details</span>
              <ChevronDown className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      </div>

      {/* ── Expanded detail area ─────────────────────────── */}
      {expanded && (
        <div className="border-t border-white/[0.06] px-5 py-4 space-y-4 max-w-4xl">
          {openPrompts.map((p) => {
            const cAction = (p.actions || []).find(
              (a) => a.type === "ask_user" && a.metadata?.tier === "critical"
            );
            const iAction = (p.actions || []).find(
              (a) => a.type === "ask_user" && a.metadata?.tier === "important"
            );
            const fallbackAction = (p.actions || []).find((a) => a.type === "ask_user");

            return (
              <div key={p.id} className="space-y-3">
                {/* Critical block */}
                {cAction && cAction.question && (
                  <div className="space-y-2">
                    <div className="flex items-start gap-2.5">
                      <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                      <div>
                        <p className="text-xs font-bold text-red-300 uppercase tracking-wide mb-1">
                          Critical — Cannot proceed without this
                        </p>
                        <p className="text-sm text-zinc-200 leading-relaxed">{cAction.question}</p>
                        {cAction.metadata?.critical_gaps && cAction.metadata.critical_gaps.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {cAction.metadata.critical_gaps.map((g) => (
                              <span
                                key={g.doctype}
                                className="text-[11px] bg-red-500/15 border border-red-500/25 text-red-300 px-2 py-0.5 rounded-full"
                              >
                                {g.doctype}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                    {/* Critical: only upload option */}
                    <div className="ml-6.5 max-w-md w-full">
                      {activeUpload?.promptId === p.id && activeUpload?.actionId === cAction.id ? (
                        <SupervisorInlineUploader
                          projectId={projectId}
                          companySlug={session.companySlug}
                          promptId={p.id}
                          actionId={cAction.id}
                          selectedOption={activeUpload.selectedOption}
                          userNote={assistantNote.trim()}
                          onSuccess={() => {
                            setActiveUpload(null);
                            setAssistantNote("");
                            poll();
                            setExpanded(false);
                          }}
                          onCancel={() => setActiveUpload(null)}
                        />
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {(cAction.options || ["Upload the missing files"]).map((opt) => (
                            <button
                              key={opt}
                              disabled={responding}
                              onClick={() => {
                                if (opt.toLowerCase().includes("upload")) {
                                  setActiveUpload({ promptId: p.id, actionId: cAction.id, selectedOption: opt });
                                } else {
                                  respond(p, cAction, opt);
                                }
                              }}
                              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500/15 border border-red-500/30 hover:bg-red-500/25 text-red-200 text-sm font-medium transition-colors disabled:opacity-50"
                            >
                              <Upload className="w-4 h-4" />
                              {responding ? "Submitting…" : opt}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Divider */}
                {cAction && iAction && (
                  <div className="border-t border-white/[0.05]" />
                )}

                {/* Important block */}
                {iAction && iAction.question && (
                  <div className="space-y-2">
                    <div className="flex items-start gap-2.5">
                      <Info className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
                      <div>
                        <p className="text-xs font-bold text-amber-300 uppercase tracking-wide mb-1">
                          Recommended — Industry best practice
                        </p>
                        <p className="text-sm text-zinc-300 leading-relaxed">{iAction.question}</p>
                        {iAction.metadata?.important_gaps && iAction.metadata.important_gaps.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {iAction.metadata.important_gaps.map((g) => (
                              <span
                                key={g.doctype}
                                className="text-[11px] bg-amber-500/15 border border-amber-500/25 text-amber-300 px-2 py-0.5 rounded-full"
                              >
                                {g.doctype}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="ml-6.5 max-w-md w-full">
                      {activeUpload?.promptId === p.id && activeUpload?.actionId === iAction.id ? (
                        <SupervisorInlineUploader
                          projectId={projectId}
                          companySlug={session.companySlug}
                          promptId={p.id}
                          actionId={iAction.id}
                          selectedOption={activeUpload.selectedOption}
                          userNote={assistantNote.trim()}
                          onSuccess={() => {
                            setActiveUpload(null);
                            setAssistantNote("");
                            poll();
                            setExpanded(false);
                          }}
                          onCancel={() => setActiveUpload(null)}
                        />
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {(iAction.options || []).map((opt) => {
                            const isUpload = opt.toLowerCase().includes("upload");
                            return (
                              <button
                                key={opt}
                                disabled={responding}
                                onClick={() => {
                                  if (isUpload) {
                                    setActiveUpload({ promptId: p.id, actionId: iAction.id, selectedOption: opt });
                                  } else {
                                  respond(p, iAction, opt);
                                  }
                                }}
                                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${
                                  isUpload
                                    ? "bg-amber-500/15 border border-amber-500/30 hover:bg-amber-500/25 text-amber-200"
                                    : "bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.07] text-zinc-400"
                                }`}
                              >
                                {isUpload ? <Upload className="w-4 h-4" /> : <ArrowRight className="w-4 h-4" />}
                                {responding ? "Submitting…" : opt}
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Fallback for no-tier actions */}
                {!cAction && !iAction && fallbackAction && fallbackAction.question && (
                  <div className="space-y-2">
                    <p className="text-sm text-zinc-200 leading-relaxed">{fallbackAction.question}</p>
                    <div className="flex flex-wrap gap-2">
                      {(fallbackAction.options || []).map((opt) => (
                        <button
                          key={opt}
                          disabled={responding}
                          onClick={() => respond(p, fallbackAction, opt)}
                          className="px-4 py-2 rounded-lg bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.07] text-sm text-zinc-300 transition-colors disabled:opacity-50"
                        >
                          {responding ? "Submitting…" : opt}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                <div className="space-y-1.5">
                  <label className="block text-[10px] uppercase tracking-wider text-zinc-500">
                    Add a note for the assistant
                  </label>
                  <textarea
                    value={assistantNote}
                    onChange={(e) => setAssistantNote(e.target.value)}
                    placeholder="Optional clarification before you respond."
                    maxLength={800}
                    className="w-full min-h-[70px] rounded-lg bg-black/20 border border-white/[0.08] px-3 py-2 text-sm text-white placeholder:text-gray-600 outline-none focus:border-amber-500/40 resize-y"
                  />
                </div>
              </div>
            );
          })}

          {respondError && (
            <p className="text-xs text-red-400 font-mono">{respondError}</p>
          )}
        </div>
      )}
    </div>
  );
}

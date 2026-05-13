"use client";

import { useEffect, useMemo, useState } from "react";
import { getBaseApiUrl } from "@/lib/config";
import { useImplementation } from "@/contexts/ImplementationContext";

type SupervisorAction = {
  id: string;
  type: "auto_fix" | "ask_user" | "hard_block" | string;
  scope?: string;
  question?: string;
  options?: string[];
};

type SupervisorPrompt = {
  id: string;
  step: string;
  status: string;
  summary_for_ui?: string | null;
  actions?: SupervisorAction[];
  created_at?: string | null;
};

type DataReadinessGap = {
  doctype: string;
  criticality?: "critical" | "non_critical" | "optional" | string;
  reason?: string;
  recommendation?: string;
  missing_fields?: string[];
  source_file?: string;
  description?: string;
  can_proceed_without?: boolean;
};

type DataReadinessReport = {
  ready_doctypes?: unknown[];
  partial_doctypes?: DataReadinessGap[];
  missing_doctypes?: DataReadinessGap[];
  unmappable_chunks?: Array<{ filename?: string; description?: string; reason?: string }>;
  gap_report?: Record<string, unknown>;
  minimum_viable_possible?: boolean;
  user_action_required?: boolean;
  questions_for_user?: Array<{ id: string; question: string; options: string[] }>;
  import_readiness_score?: number;
  executive_summary?: string | null;
};

export function SupervisorPanel() {
  const { session } = useImplementation();
  const projectId = session.id;

  const [prompts, setPrompts] = useState<SupervisorPrompt[]>([]);
  const [readiness, setReadiness] = useState<DataReadinessReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [respondingId, setRespondingId] = useState<string | null>(null);

  const openPrompts = useMemo(() => prompts.filter((p) => p.status === "open"), [prompts]);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const base = getBaseApiUrl();
      const [promptsRes, readinessRes] = await Promise.all([
        fetch(`${base}/api/implementation/supervisor-prompts/${projectId}`, { cache: "no-store" }),
        fetch(`${base}/api/implementation/data-readiness/${projectId}`, { cache: "no-store" }),
      ]);
      if (!promptsRes.ok) throw new Error(await promptsRes.text());
      const promptsData = await promptsRes.json();
      setPrompts(Array.isArray(promptsData?.prompts) ? promptsData.prompts : []);
      if (readinessRes.ok) {
        const readinessData = await readinessRes.json();
        setReadiness(readinessData?.data_readiness ?? null);
      } else if (readinessRes.status === 404) {
        setReadiness(null);
      } else {
        throw new Error(await readinessRes.text());
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load supervisor prompts");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 3000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function respond(prompt: SupervisorPrompt, action: SupervisorAction, selectedOption?: string) {
    setRespondingId(prompt.id);
    try {
      const base = getBaseApiUrl();
      const res = await fetch(`${base}/api/implementation/supervisor-prompts/respond`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          prompt_id: prompt.id,
          chosen_action_id: action.id,
          extra_data: selectedOption ? { selected_option: selectedOption } : {},
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to respond");
    } finally {
      setRespondingId(null);
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-3 border-b border-[var(--border-subtle)] bg-[var(--bg-shell)]">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-semibold text-zinc-200">Implementation Assistant</div>
            <div className="text-[11px] text-zinc-500">Supervisor prompts</div>
          </div>
          <button
            onClick={refresh}
            className="text-xs px-2 py-1 rounded-md border border-[var(--border-subtle)] text-zinc-300 hover:bg-white/[0.04]"
            disabled={loading}
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {error && (
          <div className="text-xs text-red-300 border border-red-500/20 bg-red-500/10 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        {readiness && (
          <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-3 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-[11px] text-zinc-500">Data readiness</div>
                <div className="text-sm font-semibold text-zinc-200">Pre-mapping assessment</div>
              </div>
              <div className="text-right">
                <div className="text-[10px] text-zinc-500 uppercase tracking-wide">Score</div>
                <div className="text-sm font-mono text-zinc-200">
                  {Math.round((readiness.import_readiness_score ?? 0) * 100)}%
                </div>
              </div>
            </div>

            {readiness.executive_summary && (
              <div className="text-xs text-zinc-300 leading-relaxed">{readiness.executive_summary}</div>
            )}

            <div className="h-2 rounded-full bg-white/[0.05] overflow-hidden">
              <div
                className="h-full bg-amber-500 rounded-full transition-all duration-500"
                style={{ width: `${Math.round((readiness.import_readiness_score ?? 0) * 100)}%` }}
              />
            </div>

            <div className="grid grid-cols-3 gap-2 text-[11px]">
              <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-2 py-2">
                <div className="text-emerald-200 font-medium">Ready</div>
                <div className="text-emerald-100/80 font-mono">
                  {Array.isArray(readiness.ready_doctypes) ? readiness.ready_doctypes.length : 0}
                </div>
              </div>
              <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 px-2 py-2">
                <div className="text-amber-200 font-medium">Partial</div>
                <div className="text-amber-100/80 font-mono">{readiness.partial_doctypes?.length ?? 0}</div>
              </div>
              <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-2 py-2">
                <div className="text-red-200 font-medium">Missing</div>
                <div className="text-red-100/80 font-mono">{readiness.missing_doctypes?.length ?? 0}</div>
              </div>
            </div>

            {readiness.user_action_required && (
              <div className="text-[11px] rounded-lg border border-amber-500/20 bg-amber-500/10 px-2 py-2 text-amber-100">
                Action required before mapping can safely continue.
              </div>
            )}

            {!!readiness.partial_doctypes?.length && (
              <div className="space-y-1">
                <div className="text-[10px] uppercase tracking-wide text-zinc-500">Partial</div>
                {readiness.partial_doctypes.slice(0, 3).map((gap) => (
                  <div key={`${gap.doctype}-${gap.reason ?? ""}`} className="text-[11px] rounded-lg border border-white/5 bg-white/[0.03] px-2 py-2">
                    <div className="font-medium text-zinc-200">{gap.doctype}</div>
                    <div className="text-zinc-400">{gap.reason}</div>
                  </div>
                ))}
              </div>
            )}

            {!!readiness.missing_doctypes?.length && (
              <div className="space-y-1">
                <div className="text-[10px] uppercase tracking-wide text-zinc-500">Missing</div>
                {readiness.missing_doctypes.slice(0, 3).map((gap) => (
                  <div key={`${gap.doctype}-${gap.reason ?? ""}`} className="text-[11px] rounded-lg border border-white/5 bg-white/[0.03] px-2 py-2">
                    <div className="font-medium text-zinc-200">{gap.doctype}</div>
                    <div className="text-zinc-400">{gap.reason}</div>
                  </div>
                ))}
              </div>
            )}

            {!!readiness.unmappable_chunks?.length && (
              <div className="space-y-1">
                <div className="text-[10px] uppercase tracking-wide text-zinc-500">Unmappable</div>
                {readiness.unmappable_chunks.slice(0, 3).map((chunk, idx) => (
                  <div key={`${chunk.filename ?? "chunk"}-${idx}`} className="text-[11px] rounded-lg border border-white/5 bg-white/[0.03] px-2 py-2">
                    <div className="font-medium text-zinc-200">{chunk.filename ?? "Unknown file"}</div>
                    <div className="text-zinc-400">{chunk.reason ?? chunk.description ?? "No ERPNext match"}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {openPrompts.length === 0 && !loading && (
          <div className="text-xs text-zinc-500">
            No open prompts. If the system detects issues, they’ll appear here.
          </div>
        )}

        {openPrompts.map((p) => {
          const ask = (p.actions || []).find((a) => a.type === "ask_user");
          const hard = (p.actions || []).find((a) => a.type === "hard_block");
          const title = hard ? "Blocked" : ask ? "Needs input" : "Notice";

          return (
            <div
              key={p.id}
              className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-3 space-y-2"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-[11px] text-zinc-500">{p.step}</div>
                  <div className="text-sm font-semibold text-zinc-200">{title}</div>
                </div>
                <div className="text-[10px] text-zinc-500 font-mono">{p.id.slice(0, 8)}</div>
              </div>

              {p.summary_for_ui && (
                <div className="text-xs text-zinc-300 leading-relaxed">{p.summary_for_ui}</div>
              )}

              {ask?.question && (
                <div className="text-xs text-zinc-200 leading-relaxed">{ask.question}</div>
              )}

              {ask?.options && ask.options.length > 0 && (
                <div className="space-y-2 pt-1">
                  {ask.options.map((opt) => (
                    <button
                      key={opt}
                      disabled={respondingId === p.id}
                      onClick={() => respond(p, ask, opt)}
                      className="w-full text-left text-xs px-3 py-2 rounded-lg border border-[var(--border-subtle)] hover:bg-white/[0.04] text-zinc-200 disabled:opacity-50"
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              )}

              {!ask && p.actions && p.actions.length > 0 && (
                <div className="text-[11px] text-zinc-500">
                  Actions: {p.actions.map((a) => a.type).join(", ")}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}


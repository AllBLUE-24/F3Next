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

export function SupervisorPanel() {
  const { session } = useImplementation();
  const projectId = session.id;

  const [prompts, setPrompts] = useState<SupervisorPrompt[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [respondingId, setRespondingId] = useState<string | null>(null);

  const openPrompts = useMemo(() => prompts.filter((p) => p.status === "open"), [prompts]);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const base = getBaseApiUrl();
      const res = await fetch(`${base}/api/implementation/supervisor-prompts/${projectId}`, {
        cache: "no-store",
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setPrompts(Array.isArray(data?.prompts) ? data.prompts : []);
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


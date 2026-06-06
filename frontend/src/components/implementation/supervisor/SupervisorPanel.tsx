"use client";

/**
 * SupervisorPanel — right-side assistant panel for the Implementation shell.
 *
 * v2 — rich two-tier gap display:
 *   🔴 CRITICAL  — relational ERPNext dependency; pipeline blocked.
 *   🟡 IMPORTANT — industry best-practice gap; can continue but not recommended.
 *
 * Design philosophy:
 *   - Natural-language messages from the Supervisor LLM (no raw MCQ dump).
 *   - Critical items have ONE action: "Upload missing files". No skip option.
 *   - Important items offer "Upload recommended files" OR a clearly-warned "Continue".
 *   - Data readiness summary is always shown when available (score + tier counts).
 *   - Open prompts that need user input are visually emphasized at the top.
 */

import { useEffect, useMemo, useState, useCallback } from "react";
import { usePathname } from "next/navigation";
import {
  AlertTriangle, Info, CheckCircle2, Upload,
  ArrowRight, RefreshCw, Sparkles, ChevronDown, ChevronUp,
} from "lucide-react";
import { getBaseApiUrl } from "@/lib/config";
import { useImplementation } from "@/contexts/ImplementationContext";
import type { ValidatePreviewData } from "@/lib/api/implementation_api";

import { SupervisorInlineUploader } from "./SupervisorInlineUploader";
import { ChatMessageList, type ChatMessage } from "./ChatMessageList";
import { ChatBar } from "./ChatBar";

// ── Types ─────────────────────────────────────────────────────────────────────

type ActionTier = "critical" | "important" | string;

type SupervisorAction = {
  id: string;
  type: "auto_fix" | "ask_user" | "hard_block" | string;
  scope?: string;
  question?: string;
  options?: string[];
  metadata?: {
    tier?: ActionTier;
    critical_gaps?: Array<{ doctype: string; reason: string }>;
    important_gaps?: Array<{ doctype: string; reason: string }>;
    missing_required_fields?: string[];
    unmappable_chunks?: unknown[];
  };
};

type SupervisorPrompt = {
  id: string;
  step: string;
  status: string;
  summary_for_ui?: string | null;
  actions?: SupervisorAction[];
  created_at?: string | null;
};

type SessionSummary = {
  status?: string | null;
  user_import_note?: string | null;
  total_files?: number;
  batch_count?: number;
  file_batches?: Array<{
    batch_index?: number;
    uploaded_at?: string;
    note?: string;
    files?: Array<{ file_name?: string; object_path?: string }>;
  }>;
} | null;

type DataReadinessGap = {
  doctype: string;
  criticality?: "critical" | "non_critical" | "optional" | string;
  reason?: string;
  recommendation?: string;
  missing_fields?: string[];
  can_proceed_without?: boolean;
};

type DataReadinessReady = {
  doctype: string;
  source_file?: string;
  coverage_pct?: number;
  ready_with_assumptions?: boolean;
  evidence_type?: string;
  coverage_note?: string;
};

type DataReadinessReport = {
  ready_doctypes?: DataReadinessReady[];
  partial_doctypes?: DataReadinessGap[];
  missing_doctypes?: DataReadinessGap[];
  unmappable_chunks?: Array<{ filename?: string; description?: string; reason?: string }>;
  minimum_viable_possible?: boolean;
  user_action_required?: boolean;
  import_readiness_score?: number;
  executive_summary?: string | null;
};

// ── Step from route ───────────────────────────────────────────────────────────

function pathnameToChatStep(pathname: string): string {
  if (pathname.includes("/validate")) return "validate";
  if (pathname.includes("/import") || pathname.includes("/sandbox")) return "import";
  if (pathname.includes("/analyze")) return "analyze";
  return "upload";
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 80 ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
    : pct >= 50 ? "text-amber-400 border-amber-500/30 bg-amber-500/10"
    : "text-red-400 border-red-500/30 bg-red-500/10";
  return (
    <span className={`text-xs font-mono px-2 py-0.5 rounded-full border ${color}`}>
      {pct}%
    </span>
  );
}

function ValidationOverallBadge({ overall }: { overall: string }) {
  if (overall === "fail") {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/25">
        <AlertTriangle className="w-2.5 h-2.5" /> Has Errors
      </span>
    );
  }
  if (overall === "partial") {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/25">
        <AlertTriangle className="w-2.5 h-2.5" /> Passed with Warnings
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
      <CheckCircle2 className="w-2.5 h-2.5" /> All Passed
    </span>
  );
}

function buildReadinessSummaryMessage(readiness: DataReadinessReport): string {
  const pct = Math.round((readiness.import_readiness_score ?? 0) * 100);
  const ready = readiness.ready_doctypes?.length ?? 0;
  const critical = [
    ...(readiness.missing_doctypes || []),
    ...(readiness.partial_doctypes || []),
  ].filter((g) => g.criticality === "critical").length;
  const important = [
    ...(readiness.missing_doctypes || []),
    ...(readiness.partial_doctypes || []),
  ].filter((g) => g.criticality === "non_critical").length;
  const lines = [
    `**Data readiness: ${pct}%** — ${ready} doctype${ready === 1 ? "" : "s"} pass dry-run preflight.`,
  ];
  if (critical > 0) lines.push(`${critical} critical gap${critical === 1 ? "" : "s"} need attention.`);
  if (important > 0) lines.push(`${important} important gap${important === 1 ? "" : "s"} — you can continue with caution.`);
  if (readiness.executive_summary) lines.push(readiness.executive_summary);
  return lines.join("\n\n");
}

function buildValidationSummaryMessage(preview: ValidatePreviewData): string {
  const totalRecords = preview.doctypes.reduce((s, d) => s + (d.total_rows ?? 0), 0);
  const withErrors = preview.doctypes.filter(
    (d) => d.validation_status === "fail" || d.validation_status === "failed" || (d.errors?.length ?? 0) > 0
  ).length;
  const overall =
    preview.validation_overall === "fail"
      ? "has errors"
      : preview.validation_overall === "partial"
        ? "passed with warnings"
        : "all passed";
  const lines = [
    `**Validation ${overall}** — ${preview.doctypes.length} doctype${preview.doctypes.length === 1 ? "" : "s"}, ${totalRecords} records.`,
  ];
  if (withErrors > 0) lines.push(`${withErrors} doctype${withErrors === 1 ? "" : "s"} with validation errors.`);
  if ((preview.mapping_gaps?.length ?? 0) > 0) {
    lines.push("**Not mapped:**");
    for (const gap of preview.mapping_gaps ?? []) {
      lines.push(`• ${gap.message}`);
    }
  }
  if ((preview.unmapped_seeds?.length ?? 0) > 0) {
    lines.push(
      `MVP seeds without mapped data: ${preview.unmapped_seeds!.join(", ")}.`
    );
  }
  if ((preview.open_critical_gaps ?? 0) > 0) {
    lines.push(`${preview.open_critical_gaps} open critical gap${preview.open_critical_gaps === 1 ? "" : "s"} remain.`);
  }
  return lines.join("\n\n");
}

function ValidationSummaryCard({ preview }: { preview: ValidatePreviewData }) {
  const totalRecords = preview.doctypes.reduce((s, d) => s + (d.total_rows ?? 0), 0);
  const withErrors = preview.doctypes.filter(
    (d) => d.validation_status === "fail" || d.validation_status === "failed" || (d.errors?.length ?? 0) > 0
  ).length;
  const withWarnings = preview.doctypes.filter(
    (d) =>
      d.validation_status === "partial" ||
      d.validation_status === "passed_with_warnings" ||
      (d.warnings?.length ?? 0) > 0
  ).length;

  const rawDqs = preview.profile?.data_quality_score;
  const dqsPct =
    rawDqs != null && !Number.isNaN(Number(rawDqs))
      ? Math.round(Number(rawDqs) * 100)
      : null;
  const dqsCapped = Boolean(preview.profile?.data_quality_capped);

  return (
    <div className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-card)] overflow-hidden">
      <div className="px-4 py-3 border-b border-white/[0.05] flex items-center justify-between">
        <div>
          <p className="text-[10px] text-zinc-500 uppercase tracking-wide">Validation</p>
          <p className="text-xs font-semibold text-zinc-200 mt-0.5">Post-mapping validation</p>
        </div>
        <ValidationOverallBadge overall={preview.validation_overall} />
      </div>

      <div className="p-4 space-y-3">
        <div className="grid grid-cols-3 gap-2">
          <div className="rounded-lg bg-white/[0.03] border border-white/[0.06] px-2.5 py-2 text-center">
            <p className="text-[10px] text-zinc-500 font-medium">Doctypes</p>
            <p className="text-sm font-mono text-zinc-200 mt-0.5">{preview.doctypes.length}</p>
          </div>
          <div className="rounded-lg bg-amber-500/[0.08] border border-amber-500/15 px-2.5 py-2 text-center">
            <p className="text-[10px] text-amber-400/70 font-medium">Warnings</p>
            <p className="text-sm font-mono text-amber-300 mt-0.5">{withWarnings}</p>
          </div>
          <div className="rounded-lg bg-red-500/[0.08] border border-red-500/15 px-2.5 py-2 text-center">
            <p className="text-[10px] text-red-400/70 font-medium">Errors</p>
            <p className="text-sm font-mono text-red-300 mt-0.5">{withErrors}</p>
          </div>
        </div>

        <p className="text-[11px] text-zinc-500">
          {totalRecords} total records mapped across {preview.doctypes.length} doctype
          {preview.doctypes.length === 1 ? "" : "s"}.
        </p>

        {dqsPct != null && (
          <p className="text-[11px] text-zinc-400">
            Data quality:{" "}
            <span className="font-mono text-zinc-200">
              {dqsPct}%
              {dqsCapped ? " (capped — validation warnings)" : ""}
            </span>
          </p>
        )}
      </div>
    </div>
  );
}

function TierBadge({ tier }: { tier: ActionTier }) {
  if (tier === "critical") {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/25">
        <AlertTriangle className="w-2.5 h-2.5" /> Critical
      </span>
    );
  }
  if (tier === "important" || tier === "non_critical") {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/25">
        <Info className="w-2.5 h-2.5" /> Important
      </span>
    );
  }
  return null;
}

function ReadyList({ items }: { items: DataReadinessReady[] }) {
  const [open, setOpen] = useState(true);
  if (!items.length) return null;

  return (
    <div className="rounded-lg border border-emerald-500/15 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-white/[0.02] transition-colors text-left"
      >
        <span className="text-[11px] font-semibold text-emerald-300/90">
          Covered in upload{" "}
          <span className="text-zinc-500 font-normal">({items.length})</span>
        </span>
        {open ? (
          <ChevronUp className="w-3 h-3 text-zinc-600" />
        ) : (
          <ChevronDown className="w-3 h-3 text-zinc-600" />
        )}
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-2">
          {items.map((item) => (
            <div key={item.doctype} className="flex items-start gap-2">
              <span className="mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0 bg-emerald-400" />
              <div className="min-w-0">
                <p className="text-[11px] font-semibold text-zinc-200">
                  {item.doctype}
                  {item.ready_with_assumptions && (
                    <span className="ml-1.5 text-[10px] font-normal text-amber-400/80">
                      (defaults)
                    </span>
                  )}
                </p>
                {item.source_file && (
                  <p className="text-[10px] text-zinc-500 mt-0.5">from {item.source_file}</p>
                )}
                {item.coverage_note && (
                  <p className="text-[10px] text-zinc-500 leading-relaxed mt-0.5">
                    {item.coverage_note}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function GapList({
  gaps,
  tier,
  collapsed,
}: {
  gaps: DataReadinessGap[];
  tier: "critical" | "important";
  collapsed?: boolean;
}) {
  const [open, setOpen] = useState(!collapsed);
  const borderColor = tier === "critical" ? "border-red-500/15" : "border-amber-500/15";
  const dotColor = tier === "critical" ? "bg-red-400" : "bg-amber-400";

  return (
    <div className={`rounded-lg border ${borderColor} overflow-hidden`}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-white/[0.02] transition-colors text-left"
      >
        <span className="text-[11px] font-semibold text-zinc-300">
          {tier === "critical" ? "Must provide" : "Recommended"}{" "}
          <span className="text-zinc-500 font-normal">({gaps.length})</span>
        </span>
        {open ? (
          <ChevronUp className="w-3 h-3 text-zinc-600" />
        ) : (
          <ChevronDown className="w-3 h-3 text-zinc-600" />
        )}
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-2">
          {gaps.map((gap) => (
            <div key={gap.doctype} className="flex items-start gap-2">
              <span className={`mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${dotColor}`} />
              <div className="min-w-0">
                <p className="text-[11px] font-semibold text-zinc-200">{gap.doctype}</p>
                {gap.reason && (
                  <p className="text-[11px] text-zinc-500 leading-relaxed mt-0.5">{gap.reason}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PromptCard({
  prompt,
  onRespond,
  responding,
  projectId,
  companySlug,
}: {
  prompt: SupervisorPrompt;
  onRespond: (prompt: SupervisorPrompt, action: SupervisorAction, option?: string, userNote?: string) => void;
  responding: boolean;
  projectId: string;
  companySlug: string;
}) {
  const [activeUpload, setActiveUpload] = useState<{ actionId: string; selectedOption: string; userNote?: string } | null>(null);
  const [userNote, setUserNote] = useState("");

  const criticalAction = (prompt.actions || []).find(
    (a) => a.type === "ask_user" && a.metadata?.tier === "critical"
  );
  const importantAction = (prompt.actions || []).find(
    (a) => a.type === "ask_user" && a.metadata?.tier === "important"
  );
  const genericAskAction = (prompt.actions || []).find(
    (a) => a.type === "ask_user" && !a.metadata?.tier
  );

  // Prefer tiered actions; fall back to generic ask_user
  const hasStructured = criticalAction || importantAction;

  return (
    <div className="rounded-xl border border-white/[0.07] bg-[var(--bg-card)] overflow-hidden">
      {/* Header strip */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/[0.05] bg-white/[0.02]">
        <Sparkles className="w-3.5 h-3.5 text-amber-400" />
        <span className="text-xs font-semibold text-zinc-200">Implementation Assistant</span>
        <span className="ml-auto text-[10px] text-zinc-600 font-mono">{prompt.step}</span>
      </div>

      <div className="p-4 space-y-4">
        {/* ── CRITICAL block ─────────────────────────────── */}
        {criticalAction && criticalAction.question && (
          <div className="space-y-3">
            <div className="flex items-start gap-2.5">
              <div className="mt-0.5 w-7 h-7 rounded-lg bg-red-500/15 border border-red-500/25 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
              </div>
              <div className="min-w-0">
                <TierBadge tier="critical" />
                <p className="mt-1.5 text-[12px] text-zinc-200 leading-relaxed">
                  {criticalAction.question}
                </p>
              </div>
            </div>

            {/* Affected doctypes detail */}
            {criticalAction.metadata?.critical_gaps && criticalAction.metadata.critical_gaps.length > 0 && (
              <div className="ml-9 space-y-1">
                {criticalAction.metadata.critical_gaps.map((g) => (
                  <div key={g.doctype} className="flex items-start gap-1.5">
                    <span className="mt-1.5 w-1 h-1 rounded-full bg-red-400/60 flex-shrink-0" />
                    <span className="text-[11px] font-semibold text-red-300">{g.doctype}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Missing fields (validation node) */}
            {criticalAction.metadata?.missing_required_fields && criticalAction.metadata.missing_required_fields.length > 0 && (
              <div className="ml-9 bg-red-500/[0.07] rounded-lg px-3 py-2">
                <p className="text-[10px] text-red-400/70 uppercase tracking-wide font-medium mb-1.5">Missing fields</p>
                <div className="flex flex-wrap gap-1">
                  {criticalAction.metadata.missing_required_fields.map((f) => (
                    <span key={f} className="text-[10px] font-mono bg-red-500/15 text-red-300 px-1.5 py-0.5 rounded">
                      {f}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Action buttons — critical: only upload, no skip */}
            <div className="ml-9 space-y-2">
              {activeUpload?.actionId === criticalAction.id ? (
                <SupervisorInlineUploader
                  projectId={projectId}
                  companySlug={companySlug}
                  promptId={prompt.id}
                  actionId={criticalAction.id}
                  selectedOption={activeUpload.selectedOption}
                  userNote={activeUpload.userNote || ""}
                  onSuccess={() => {
                    setActiveUpload(null);
                    setUserNote("");
                  }}
                  onCancel={() => setActiveUpload(null)}
                />
              ) : (
                (criticalAction.options || ["Upload the missing files"]).map((opt) => (
                  <button
                    key={opt}
                    disabled={responding}
                    onClick={() => {
                      if (opt.toLowerCase().includes("upload")) {
                        setActiveUpload({ actionId: criticalAction.id, selectedOption: opt, userNote: userNote.trim() });
                      } else {
                        onRespond(prompt, criticalAction, opt, userNote.trim());
                      }
                    }}
                    className="w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg bg-red-500/10 border border-red-500/25 hover:bg-red-500/20 text-red-200 text-xs font-medium transition-colors disabled:opacity-50"
                  >
                    <span className="flex items-center gap-2">
                      <Upload className="w-3.5 h-3.5" />
                      {opt}
                    </span>
                    <ArrowRight className="w-3 h-3 opacity-60" />
                  </button>
                ))
              )}
            </div>
          </div>
        )}

        {/* Divider when both tiers present */}
        {criticalAction && importantAction && (
          <div className="border-t border-white/[0.05]" />
        )}

        {/* ── IMPORTANT block ────────────────────────────── */}
        {importantAction && importantAction.question && (
          <div className="space-y-3">
            <div className="flex items-start gap-2.5">
              <div className="mt-0.5 w-7 h-7 rounded-lg bg-amber-500/15 border border-amber-500/25 flex items-center justify-center flex-shrink-0">
                <Info className="w-3.5 h-3.5 text-amber-400" />
              </div>
              <div className="min-w-0">
                <TierBadge tier="important" />
                <p className="mt-1.5 text-[12px] text-zinc-300 leading-relaxed">
                  {importantAction.question}
                </p>
              </div>
            </div>

            {importantAction.metadata?.important_gaps && importantAction.metadata.important_gaps.length > 0 && (
              <div className="ml-9 space-y-1">
                {importantAction.metadata.important_gaps.map((g) => (
                  <div key={g.doctype} className="flex items-start gap-1.5">
                    <span className="mt-1.5 w-1 h-1 rounded-full bg-amber-400/60 flex-shrink-0" />
                    <span className="text-[11px] font-semibold text-amber-300">{g.doctype}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Action buttons — important: upload OR continue with warning */}
            <div className="ml-9 space-y-2">
              {activeUpload?.actionId === importantAction.id ? (
                <SupervisorInlineUploader
                  projectId={projectId}
                  companySlug={companySlug}
                  promptId={prompt.id}
                  actionId={importantAction.id}
                  selectedOption={activeUpload.selectedOption}
                  userNote={activeUpload.userNote || ""}
                  onSuccess={() => {
                    setActiveUpload(null);
                    setUserNote("");
                  }}
                  onCancel={() => setActiveUpload(null)}
                />
              ) : (
                (importantAction.options || []).map((opt) => {
                  const isUpload = opt.toLowerCase().includes("upload");
                  const isContinue = !isUpload;
                  return (
                    <button
                      key={opt}
                      disabled={responding}
                      onClick={() => {
                        if (isUpload) {
                          setActiveUpload({ actionId: importantAction.id, selectedOption: opt, userNote: userNote.trim() });
                        } else {
                          onRespond(prompt, importantAction, opt, userNote.trim());
                        }
                      }}
                      className={`w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg border text-xs font-medium transition-colors disabled:opacity-50 ${
                        isUpload
                          ? "bg-amber-500/10 border-amber-500/25 hover:bg-amber-500/20 text-amber-200"
                          : "bg-white/[0.03] border-white/[0.07] hover:bg-white/[0.06] text-zinc-400"
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        {isUpload ? <Upload className="w-3.5 h-3.5" /> : <ArrowRight className="w-3.5 h-3.5" />}
                        {opt}
                      </span>
                      {isContinue && (
                        <span className="text-[9px] text-zinc-600 ml-1 normal-case font-normal">not recommended</span>
                      )}
                    </button>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* ── Generic fallback (no tiered actions) ──────── */}
        {!hasStructured && genericAskAction && genericAskAction.question && (
          <div className="space-y-3">
            <p className="text-[12px] text-zinc-300 leading-relaxed">{genericAskAction.question}</p>
            {(genericAskAction.options || []).map((opt) => (
              <button
                key={opt}
                disabled={responding}
                onClick={() => onRespond(prompt, genericAskAction, opt, userNote.trim())}
                className="w-full text-left text-xs px-3 py-2.5 rounded-lg border border-[var(--border-subtle)] hover:bg-white/[0.04] text-zinc-200 disabled:opacity-50 transition-colors"
              >
                {opt}
              </button>
            ))}
          </div>
        )}
        <div className="space-y-1.5">
          <label className="block text-[10px] uppercase tracking-wider text-zinc-600">
            Add a note for the assistant
          </label>
          <textarea
            value={userNote}
            onChange={(e) => setUserNote(e.target.value)}
            placeholder="Optional clarification before you respond."
            maxLength={800}
            className="w-full min-h-[70px] rounded-lg bg-black/20 border border-white/[0.06] px-3 py-2 text-[12px] text-zinc-200 placeholder:text-zinc-600 outline-none focus:border-amber-500/40 resize-y"
          />
        </div>
      </div>
    </div>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────

export function SupervisorPanel() {
  const { session } = useImplementation();
  const projectId = session.id;
  const pathname = usePathname();
  const isPostMappingRoute =
    pathname.includes("/validate") || pathname.includes("/import") || pathname.includes("/sandbox");
  const chatStep = pathnameToChatStep(pathname);

  const [prompts, setPrompts] = useState<SupervisorPrompt[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [readiness, setReadiness] = useState<DataReadinessReport | null>(null);
  const [validatePreview, setValidatePreview] = useState<ValidatePreviewData | null>(null);
  const [sessionSummary, setSessionSummary] = useState<SessionSummary>(null);
  const [workflowStage, setWorkflowStage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [respondingId, setRespondingId] = useState<string | null>(null);
  const [chatSending, setChatSending] = useState(false);

  const openPrompts = useMemo(
    () => prompts.filter((p) => p.status === "open"),
    [prompts]
  );
  const totalFiles = sessionSummary?.total_files ?? 0;
  const batchCount = sessionSummary?.batch_count ?? 0;

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const base = getBaseApiUrl();
      const fetches: Promise<Response>[] = [
        fetch(`${base}/api/implementation/supervisor-prompts/${projectId}`, { cache: "no-store" }),
        fetch(`${base}/api/implementation/data-readiness/${projectId}`, { cache: "no-store" }),
        fetch(`${base}/api/implementation/state/${projectId}`, { cache: "no-store" }),
        fetch(`${base}/api/implementation/chat/${projectId}`, { cache: "no-store" }),
      ];
      const results = await Promise.all(fetches);
      const [promptsRes, readinessRes, stateRes, chatRes, validateRes] = isPostMappingRoute
        ? [
            ...results.slice(0, 4),
            await fetch(`${base}/api/implementation/validate-preview/${projectId}`, {
              cache: "no-store",
            }),
          ]
        : [...results, undefined];

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

      if (stateRes.ok) {
        const stateData = await stateRes.json();
        setSessionSummary(stateData?.session ?? null);
        setWorkflowStage(stateData?.stage ?? null);
      }

      if (chatRes.ok) {
        const chatData = await chatRes.json();
        setChatMessages(Array.isArray(chatData?.messages) ? chatData.messages : []);
      }

      if (isPostMappingRoute && validateRes) {
        if (validateRes.ok) {
          setValidatePreview(await validateRes.json());
        } else if (validateRes.status === 404) {
          setValidatePreview(null);
        }
      } else {
        setValidatePreview(null);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load supervisor data");
    } finally {
      setLoading(false);
    }
  }, [projectId, isPostMappingRoute, chatStep]);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 4000);
    return () => clearInterval(interval);
  }, [refresh]);

  const sendChat = useCallback(
    async (message: string) => {
      setChatSending(true);
      setError(null);
      try {
        const base = getBaseApiUrl();
        const res = await fetch(`${base}/api/implementation/chat/${projectId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, step: chatStep }),
        });
        if (!res.ok) throw new Error(await res.text());
        await refresh();
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to send message");
      } finally {
        setChatSending(false);
      }
    },
    [projectId, chatStep, refresh]
  );

  const respond = useCallback(
    async (prompt: SupervisorPrompt, action: SupervisorAction, selectedOption?: string, userNote?: string) => {
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
            extra_data: {
              ...(selectedOption ? { selected_option: selectedOption } : {}),
              ...(userNote ? { user_note: userNote } : {}),
            },
          }),
        });
        if (!res.ok) throw new Error(await res.text());
        await refresh();
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to respond");
      } finally {
        setRespondingId(null);
      }
    },
    [projectId, refresh]
  );

  // Derived readiness stats
  const criticalGaps = useMemo(
    () =>
      [
        ...(readiness?.missing_doctypes || []),
        ...(readiness?.partial_doctypes || []),
      ].filter((g) => g.criticality === "critical"),
    [readiness]
  );
  const importantGaps = useMemo(
    () =>
      [
        ...(readiness?.missing_doctypes || []),
        ...(readiness?.partial_doctypes || []),
      ].filter((g) => g.criticality === "non_critical"),
    [readiness]
  );

  const displayMessages = useMemo(() => {
    const synth: ChatMessage[] = [];
    if (isPostMappingRoute && validatePreview && validatePreview.doctypes.length > 0) {
      synth.push({
        id: "__synth_validation__",
        role: "system",
        content: buildValidationSummaryMessage(validatePreview),
        message_type: "validation_summary",
      });
    } else if (readiness && !isPostMappingRoute) {
      synth.push({
        id: "__synth_readiness__",
        role: "system",
        content: buildReadinessSummaryMessage(readiness),
        message_type: "readiness_summary",
      });
    }
    const seen = new Set(chatMessages.map((m) => m.id));
    const merged = [...synth.filter((m) => !seen.has(m.id)), ...chatMessages];
    return merged;
  }, [chatMessages, readiness, validatePreview, isPostMappingRoute]);

  return (
    <div className="h-full flex flex-col text-sm">
      {/* ── Header ────────────────────────────────────────── */}
      <div className="px-4 py-3 border-b border-[var(--border-subtle)] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-400" />
          <div>
            <div className="text-xs font-semibold text-zinc-200">Implementation Assistant</div>
            {openPrompts.length > 0 && (
              <div className="text-[10px] text-amber-400 font-medium">
                {openPrompts.length} item{openPrompts.length > 1 ? "s" : ""} need your input
              </div>
            )}
            {openPrompts.length === 0 && workflowStage === 'import_blocked' && (
              <div className="text-[10px] text-red-400 font-medium">Import blocked — resolve critical gaps</div>
            )}
            {openPrompts.length === 0 && (workflowStage === 'complete' || workflowStage === 'complete_with_errors') && (
              <div className={`text-[10px] font-medium ${workflowStage === 'complete_with_errors' ? 'text-amber-400' : 'text-emerald-400'}`}>
                {workflowStage === 'complete_with_errors'
                  ? 'Import finished — some steps failed'
                  : 'Import complete'}
              </div>
            )}
            {openPrompts.length === 0 && workflowStage === 'importing' && (
              <div className="text-[10px] text-amber-400 font-medium">Live import running…</div>
            )}
            {openPrompts.length === 0 &&
              workflowStage !== 'import_blocked' &&
              workflowStage !== 'complete' &&
              workflowStage !== 'complete_with_errors' &&
              workflowStage !== 'importing' && (
              <div className="text-[10px] text-zinc-600">Monitoring your import</div>
            )}
            {batchCount > 1 && workflowStage !== 'import_blocked' && workflowStage !== 'complete' && workflowStage !== 'complete_with_errors' && (
              <div className="text-[10px] text-amber-400 font-medium">
                Re-upload round {batchCount} in progress · {totalFiles} files tracked
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!isPostMappingRoute && readiness && (
            <ScoreBadge score={readiness.import_readiness_score ?? 0} />
          )}
          {isPostMappingRoute && validatePreview && (
            <ValidationOverallBadge overall={validatePreview.validation_overall} />
          )}
          <button
            onClick={refresh}
            disabled={loading}
            className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04] transition-colors disabled:opacity-40"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* ── Chat-first body ───────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col min-h-0">
        {error && (
          <div className="text-[11px] text-red-300 border border-red-500/20 bg-red-500/10 rounded-lg px-3 py-2 mb-3 shrink-0">
            {error}
          </div>
        )}

        <div className="flex-1 min-h-0">
          <ChatMessageList
            messages={displayMessages}
            loading={loading && displayMessages.length === 0}
          />
        </div>

        {openPrompts.map((p) => (
          <div key={p.id} className="mt-4 shrink-0">
            <PromptCard
              prompt={p}
              onRespond={respond}
              responding={respondingId === p.id}
              projectId={projectId}
              companySlug={session.companySlug}
            />
          </div>
        ))}

        {openPrompts.length === 0 &&
          !readiness &&
          !validatePreview &&
          !loading &&
          displayMessages.length === 0 && (
          <div className="flex flex-col items-center gap-3 py-8 text-center">
            <CheckCircle2 className="w-8 h-8 text-zinc-700" />
            <p className="text-xs text-zinc-600 leading-relaxed max-w-[200px]">
              No issues detected. The assistant will alert you here if anything needs your attention.
            </p>
          </div>
        )}
      </div>

      <ChatBar onSend={sendChat} sending={chatSending} disabled={loading} />
    </div>
  );
}

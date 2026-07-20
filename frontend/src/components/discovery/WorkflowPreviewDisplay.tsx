"use client";

import { useMemo, useState } from "react";

export interface ExpectedDataItem {
  doctype: string;
  user_friendly_name: string;
  description: string;
  example_files: string[];
}

export interface WorkflowExplanation {
  workflow_summary: string;
  business_flow_explanation: string;
  expected_data: ExpectedDataItem[];
  setup_phases?: Array<{
    phase: string;
    name: string;
    description: string;
    doctypes: string[];
  }>;
  upload_checklist?: string[];
}

interface WorkflowPreviewDisplayProps {
  preview: {
    workflow_explanation: WorkflowExplanation;
    seed_doctypes: string[];
    deferred_doctypes?: string[];
    required_doctypes?: string[];
    promoted_doctypes?: string[];
    dual_system_note?: string;
    scoping_reasoning?: string;
    plan_reasoning?: string;
  };
  onConfirm: (adjustments: {
    confirmed_doctypes: string[];
    added_doctypes: string[];
    removed_doctypes: string[];
    notes: string;
  }) => void | Promise<void>;
  isSubmitting?: boolean;
}

export default function WorkflowPreviewDisplay({
  preview,
  onConfirm,
  isSubmitting = false,
}: WorkflowPreviewDisplayProps) {
  const initialSelected = useMemo(
    () => new Set(preview.seed_doctypes),
    [preview.seed_doctypes]
  );
  const [selected, setSelected] = useState<Set<string>>(initialSelected);
  const [notes, setNotes] = useState("");

  const expectedData = useMemo(() => {
    const fromLlm = preview.workflow_explanation.expected_data ?? [];
    const byDoctype = new Map(fromLlm.map((item) => [item.doctype, item]));
    return preview.seed_doctypes.map(
      (dt) =>
        byDoctype.get(dt) ?? {
          doctype: dt,
          user_friendly_name: dt,
          description: `Spreadsheets or exports for ${dt}`,
          example_files: [`${dt.toLowerCase().replace(/ /g, "_")}_master.xlsx`],
        }
    );
  }, [preview.workflow_explanation.expected_data, preview.seed_doctypes]);

  const deferred = preview.deferred_doctypes ?? [];
  const promoted = useMemo(
    () => new Set(preview.promoted_doctypes ?? []),
    [preview.promoted_doctypes]
  );

  const toggle = (doctype: string, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(doctype);
      else next.delete(doctype);
      return next;
    });
  };

  const handleConfirm = () => {
    const confirmed = Array.from(selected);
    const removed = preview.seed_doctypes.filter((d) => !selected.has(d));
    onConfirm({
      confirmed_doctypes: confirmed,
      added_doctypes: confirmed.filter((d) => !preview.seed_doctypes.includes(d)),
      removed_doctypes: removed,
      notes,
    });
  };

  return (
    <div className="space-y-6 fade-in-up">
      <div className="surface-card p-6 sm:p-8" style={{ borderRadius: "var(--radius-xl)" }}>
        <h2 className="text-xl font-bold text-white mb-2">Your Day-1 MVP plan</h2>
        {preview.dual_system_note && (
          <p className="text-amber-400/90 text-xs mb-3 leading-relaxed">{preview.dual_system_note}</p>
        )}
        <p className="text-zinc-400 text-sm leading-relaxed mb-4">
          {preview.workflow_explanation.workflow_summary}
        </p>
        <p className="text-zinc-500 text-sm leading-relaxed">
          {preview.workflow_explanation.business_flow_explanation}
        </p>
      </div>

      <div className="surface-card p-6 sm:p-8" style={{ borderRadius: "var(--radius-xl)" }}>
        <h3 className="text-lg font-semibold text-white mb-1">Day-1 data we need</h3>
        <p className="text-zinc-600 text-xs mb-4">
          Checked modules are in scope for your MVP. We will ask for these files after you confirm.
        </p>
        <div className="space-y-3">
          {expectedData.map((item) => (
            <label
              key={item.doctype}
              className="flex gap-3 p-4 rounded-xl border border-amber-500/20 bg-amber-500/5 cursor-pointer hover:bg-amber-500/8 transition-colors"
            >
              <input
                type="checkbox"
                className="mt-1"
                checked={selected.has(item.doctype)}
                onChange={(e) => toggle(item.doctype, e.target.checked)}
              />
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-white text-sm flex items-center gap-2 flex-wrap">
                  {item.user_friendly_name}
                  {promoted.has(item.doctype) && (
                    <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
                      Required for traceability
                    </span>
                  )}
                </div>
                <div className="text-zinc-500 text-xs mt-1">{item.description}</div>
                {item.example_files?.length > 0 && (
                  <div className="text-zinc-600 text-xs mt-2">
                    Likely files: {item.example_files.join(", ")}
                  </div>
                )}
              </div>
            </label>
          ))}
        </div>
      </div>

      {deferred.length > 0 && (
        <div className="surface-card p-6 sm:p-8 opacity-80" style={{ borderRadius: "var(--radius-xl)" }}>
          <h3 className="text-sm font-semibold text-zinc-500 mb-2">Later phases (not Day-1)</h3>
          <p className="text-zinc-600 text-xs mb-3">
            Deferred based on your bottleneck — we will not ask for these until after the first import.
          </p>
          <div className="flex flex-wrap gap-2">
            {deferred.map((dt) => (
              <span
                key={dt}
                className="px-2.5 py-1 rounded-lg text-xs text-zinc-500 border border-zinc-800 bg-zinc-900/50"
              >
                {dt}
              </span>
            ))}
          </div>
        </div>
      )}

      {preview.workflow_explanation.upload_checklist &&
        preview.workflow_explanation.upload_checklist.length > 0 && (
          <div className="surface-card p-6 sm:p-8" style={{ borderRadius: "var(--radius-xl)" }}>
            <h3 className="text-lg font-semibold text-white mb-3">Upload checklist (Day-1)</h3>
            <ul className="list-disc list-inside text-zinc-400 text-sm space-y-1">
              {preview.workflow_explanation.upload_checklist.map((line, idx) => (
                <li key={idx}>{line}</li>
              ))}
            </ul>
          </div>
        )}

      <div className="surface-card p-6 sm:p-8" style={{ borderRadius: "var(--radius-xl)" }}>
        <h3 className="text-lg font-semibold text-white mb-2">
          Any additional modules or workflows?
        </h3>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="e.g. We also need project costing for field crews..."
          className="w-full min-h-[100px] rounded-xl bg-black/30 border border-[var(--border-subtle)] text-sm text-zinc-300 p-3 focus:outline-none focus:border-amber-500/40"
        />
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleConfirm}
          disabled={isSubmitting || selected.size === 0}
          className="px-6 py-2.5 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black text-sm font-bold rounded-xl transition-colors"
        >
          {isSubmitting ? "Saving blueprint…" : "Confirm workflow & continue"}
        </button>
      </div>
    </div>
  );
}

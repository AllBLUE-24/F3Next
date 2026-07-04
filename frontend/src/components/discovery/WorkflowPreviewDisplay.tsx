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
    required_doctypes?: string[];
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

  const expectedData =
    preview.workflow_explanation.expected_data?.length > 0
      ? preview.workflow_explanation.expected_data
      : preview.seed_doctypes.map((dt) => ({
          doctype: dt,
          user_friendly_name: dt,
          description: `Data for ${dt}`,
          example_files: [`${dt.toLowerCase().replace(/ /g, "_")}.csv`],
        }));

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
        <h2 className="text-xl font-bold text-white mb-2">Your implementation workflow</h2>
        <p className="text-zinc-400 text-sm leading-relaxed mb-4">
          {preview.workflow_explanation.workflow_summary}
        </p>
        <p className="text-zinc-500 text-sm leading-relaxed">
          {preview.workflow_explanation.business_flow_explanation}
        </p>
      </div>

      <div className="surface-card p-6 sm:p-8" style={{ borderRadius: "var(--radius-xl)" }}>
        <h3 className="text-lg font-semibold text-white mb-4">Modules & files to upload</h3>
        <div className="space-y-3">
          {expectedData.map((item) => (
            <label
              key={item.doctype}
              className="flex gap-3 p-4 rounded-xl border border-[var(--border-subtle)] bg-white/[0.02] cursor-pointer hover:bg-white/[0.04] transition-colors"
            >
              <input
                type="checkbox"
                className="mt-1"
                checked={selected.has(item.doctype)}
                onChange={(e) => toggle(item.doctype, e.target.checked)}
              />
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-white text-sm">{item.user_friendly_name}</div>
                <div className="text-zinc-500 text-xs mt-1">{item.description}</div>
                {item.example_files?.length > 0 && (
                  <div className="text-zinc-600 text-xs mt-2">
                    Example files: {item.example_files.join(", ")}
                  </div>
                )}
              </div>
            </label>
          ))}
        </div>
      </div>

      {preview.workflow_explanation.upload_checklist &&
        preview.workflow_explanation.upload_checklist.length > 0 && (
          <div className="surface-card p-6 sm:p-8" style={{ borderRadius: "var(--radius-xl)" }}>
            <h3 className="text-lg font-semibold text-white mb-3">Upload checklist</h3>
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
          placeholder="e.g. We also need delivery notes, quality inspections, or project costing..."
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

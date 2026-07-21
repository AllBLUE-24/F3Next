"use client";

import { useMemo, useState } from "react";
import type { UploadSchemaDoctype, ValidatorWarning } from "@/lib/api/hooks_api";

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
    assurance?: { level?: string; reasons?: string[] };
    closure_test?: string;
    promotion_reasons?: Record<string, string>;
    validator_warnings?: ValidatorWarning[];
    upload_schema_preview?: Record<string, UploadSchemaDoctype>;
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
  const [expandedSchema, setExpandedSchema] = useState<string | null>(null);

  const validatorWarnings = preview.validator_warnings ?? [];
  const promotionReasons = preview.promotion_reasons ?? {};
  const uploadSchema = preview.upload_schema_preview ?? {};

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

  const assuranceLevel = preview.assurance?.level?.toLowerCase();
  const assuranceStyles =
    assuranceLevel === "green"
      ? "border-emerald-500/25 bg-emerald-500/8 text-emerald-300"
      : assuranceLevel === "red"
        ? "border-red-500/25 bg-red-500/8 text-red-300"
        : "border-amber-500/25 bg-amber-500/8 text-amber-300";
  const assuranceLabel =
    assuranceLevel === "green"
      ? "High confidence"
      : assuranceLevel === "red"
        ? "Needs review"
        : assuranceLevel === "yellow"
          ? "Review recommended"
          : null;
  const isBlocked = assuranceLevel === "red";

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
      {assuranceLabel && (
        <div className={`surface-card p-4 sm:p-5 border ${assuranceStyles}`} style={{ borderRadius: "var(--radius-xl)" }}>
          <div className="text-xs font-bold uppercase tracking-wider mb-1">{assuranceLabel}</div>
          {preview.assurance?.reasons?.map((reason, idx) => (
            <p key={idx} className="text-sm leading-relaxed opacity-90">
              {reason}
            </p>
          ))}
        </div>
      )}

      {preview.closure_test && (
        <div className="surface-card p-4 sm:p-5 border border-zinc-800" style={{ borderRadius: "var(--radius-xl)" }}>
          <div className="text-xs font-bold uppercase tracking-wider text-zinc-500 mb-1">Closure test</div>
          <p className="text-sm text-zinc-300 leading-relaxed">{preview.closure_test}</p>
        </div>
      )}

      {preview.plan_reasoning && (
        <div className="surface-card p-4 sm:p-5 border border-zinc-800" style={{ borderRadius: "var(--radius-xl)" }}>
          <div className="text-xs font-bold uppercase tracking-wider text-zinc-500 mb-1">Why this scope</div>
          <p className="text-sm text-zinc-300 leading-relaxed">{preview.plan_reasoning}</p>
        </div>
      )}

      {validatorWarnings.length > 0 && (
        <div className="surface-card p-4 sm:p-5 border border-amber-500/25 bg-amber-500/5" style={{ borderRadius: "var(--radius-xl)" }}>
          <div className="text-xs font-bold uppercase tracking-wider text-amber-400 mb-2">Validator notes</div>
          <ul className="space-y-2">
            {validatorWarnings.map((w, idx) => (
              <li key={idx} className="text-sm text-zinc-300 leading-relaxed">
                {w.message}
                {w.suggested_doctypes && w.suggested_doctypes.length > 0 && (
                  <span className="text-zinc-500 text-xs block mt-0.5">
                    Suggested: {w.suggested_doctypes.join(", ")}
                  </span>
                )}
              </li>
            ))}
          </ul>
          <p className="text-zinc-600 text-xs mt-3">
            Add context in the notes below if you want us to adjust scope before upload.
          </p>
        </div>
      )}

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
                    <span
                      className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 max-w-full truncate"
                      title={promotionReasons[item.doctype] || "Promoted by validator"}
                    >
                      {promotionReasons[item.doctype]
                        ? promotionReasons[item.doctype].slice(0, 48) +
                          (promotionReasons[item.doctype].length > 48 ? "…" : "")
                        : "Validator promoted"}
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

      {Object.keys(uploadSchema).length > 0 && (
        <div className="surface-card p-6 sm:p-8" style={{ borderRadius: "var(--radius-xl)" }}>
          <h3 className="text-lg font-semibold text-white mb-1">Expected spreadsheet columns</h3>
          <p className="text-zinc-600 text-xs mb-4">
            From our field-mapping KB — what each Day-1 file should contain before upload.
          </p>
          <div className="space-y-2">
            {preview.seed_doctypes
              .filter((dt) => uploadSchema[dt]?.kb_available)
              .map((dt) => {
                const schema = uploadSchema[dt];
                const open = expandedSchema === dt;
                return (
                  <div key={dt} className="border border-zinc-800 rounded-xl overflow-hidden">
                    <button
                      type="button"
                      className="w-full flex justify-between items-center px-4 py-3 text-left text-sm font-medium text-white hover:bg-zinc-900/50"
                      onClick={() => setExpandedSchema(open ? null : dt)}
                    >
                      {dt}
                      <span className="text-zinc-600 text-xs">
                        {schema.required_columns.length} required
                      </span>
                    </button>
                    {open && (
                      <div className="px-4 pb-4 space-y-3 border-t border-zinc-800">
                        {schema.required_columns.length > 0 && (
                          <div>
                            <div className="text-xs text-zinc-500 mb-1">Required columns</div>
                            <div className="flex flex-wrap gap-1.5">
                              {schema.required_columns.map((col) => (
                                <span
                                  key={col.field}
                                  className="px-2 py-0.5 rounded text-xs bg-amber-500/10 text-amber-300 border border-amber-500/20"
                                  title={col.synonyms?.join(", ")}
                                >
                                  {col.label}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {schema.optional_columns.length > 0 && (
                          <div>
                            <div className="text-xs text-zinc-500 mb-1">Optional columns</div>
                            <div className="flex flex-wrap gap-1.5">
                              {schema.optional_columns.map((col) => (
                                <span
                                  key={col.field}
                                  className="px-2 py-0.5 rounded text-xs text-zinc-500 border border-zinc-800"
                                >
                                  {col.label}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
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
          placeholder={
            validatorWarnings.length > 0
              ? "Tell us if a validator note is wrong or if scope should change…"
              : "e.g. We also need project costing for field crews..."
          }
          className="w-full min-h-[100px] rounded-xl bg-black/30 border border-[var(--border-subtle)] text-sm text-zinc-300 p-3 focus:outline-none focus:border-amber-500/40"
        />
      </div>

      {isBlocked && (
        <p className="text-red-400/90 text-sm text-right">
          Plan has structural validation errors — adjust modules or add notes before continuing.
        </p>
      )}

      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleConfirm}
          disabled={isSubmitting || selected.size === 0 || isBlocked}
          className="px-6 py-2.5 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black text-sm font-bold rounded-xl transition-colors"
        >
          {isSubmitting ? "Saving blueprint…" : "Confirm workflow & continue"}
        </button>
      </div>
    </div>
  );
}

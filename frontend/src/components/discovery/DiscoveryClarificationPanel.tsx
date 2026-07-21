"use client";

import { useMemo, useState } from "react";

export interface ClarifyingQuestion {
  id: string;
  prompt: string;
  question_type: "single_choice" | "multi_choice" | "yes_no";
  options: Array<{ value: string; label: string }>;
  why?: string;
}

interface DiscoveryClarificationPanelProps {
  questions: ClarifyingQuestion[];
  onSubmit: (answers: Record<string, string | string[]>) => void | Promise<void>;
  isSubmitting?: boolean;
}

export default function DiscoveryClarificationPanel({
  questions,
  onSubmit,
  isSubmitting = false,
}: DiscoveryClarificationPanelProps) {
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});

  const allAnswered = useMemo(
    () => questions.every((q) => {
      const val = answers[q.id];
      if (Array.isArray(val)) return val.length > 0;
      return typeof val === "string" && val.trim().length > 0;
    }),
    [answers, questions]
  );

  const setSingle = (id: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [id]: value }));
  };

  const toggleMulti = (id: string, value: string, checked: boolean) => {
    setAnswers((prev) => {
      const current = Array.isArray(prev[id]) ? [...(prev[id] as string[])] : [];
      const next = checked
        ? [...new Set([...current, value])]
        : current.filter((v) => v !== value);
      return { ...prev, [id]: next };
    });
  };

  return (
    <div
      className="surface-card p-6 sm:p-8 space-y-5"
      style={{ borderRadius: "var(--radius-xl)" }}
    >
      <div>
        <h2 className="text-lg font-bold text-white mb-1">Quick clarifications</h2>
        <p className="text-zinc-500 text-sm leading-relaxed">
          Before I lock your Day-1 plan, I need a few specifics so we scope the right ERPNext modules —
          not a generic template.
        </p>
      </div>

      {questions.map((q) => (
        <div key={q.id} className="space-y-2">
          <div className="text-sm font-semibold text-white">{q.prompt}</div>
          {q.why && <div className="text-xs text-zinc-600">{q.why}</div>}
          <div className="space-y-2 mt-2">
            {q.question_type === "multi_choice"
              ? q.options.map((opt) => (
                  <label
                    key={opt.value}
                    className="flex gap-2 items-start p-3 rounded-lg border border-zinc-800 bg-zinc-900/40 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      className="mt-0.5"
                      checked={Array.isArray(answers[q.id]) && (answers[q.id] as string[]).includes(opt.value)}
                      onChange={(e) => toggleMulti(q.id, opt.value, e.target.checked)}
                    />
                    <span className="text-sm text-zinc-300">{opt.label}</span>
                  </label>
                ))
              : q.options.map((opt) => (
                  <label
                    key={opt.value}
                    className="flex gap-2 items-start p-3 rounded-lg border border-zinc-800 bg-zinc-900/40 cursor-pointer"
                  >
                    <input
                      type="radio"
                      name={q.id}
                      className="mt-0.5"
                      checked={answers[q.id] === opt.value}
                      onChange={() => setSingle(q.id, opt.value)}
                    />
                    <span className="text-sm text-zinc-300">{opt.label}</span>
                  </label>
                ))}
          </div>
        </div>
      ))}

      <div className="flex justify-end pt-2">
        <button
          type="button"
          disabled={!allAnswered || isSubmitting}
          onClick={() => onSubmit(answers)}
          className="px-5 py-2.5 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black text-sm font-bold rounded-xl transition-colors"
        >
          {isSubmitting ? "Building plan…" : "Continue to Day-1 plan"}
        </button>
      </div>
    </div>
  );
}

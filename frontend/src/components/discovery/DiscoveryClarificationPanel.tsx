"use client";

import { useMemo, useState } from "react";

const OTHER_VALUE = "other";

export interface ClarifyingQuestion {
  id: string;
  prompt: string;
  question_type:
    | "single_choice"
    | "single_choice_with_other"
    | "multi_choice"
    | "multi_choice_with_other"
    | "yes_no";
  options: Array<{ value: string; label: string }>;
  allows_other?: boolean;
}

interface DiscoveryClarificationPanelProps {
  questions: ClarifyingQuestion[];
  onSubmit: (answers: Record<string, string | string[]>) => void | Promise<void>;
  isSubmitting?: boolean;
}

function isMulti(type: ClarifyingQuestion["question_type"]) {
  return type === "multi_choice" || type === "multi_choice_with_other";
}

function allowsOther(type: ClarifyingQuestion["question_type"], explicit?: boolean) {
  return (
    explicit === true ||
    type === "single_choice_with_other" ||
    type === "multi_choice_with_other"
  );
}

export default function DiscoveryClarificationPanel({
  questions,
  onSubmit,
  isSubmitting = false,
}: DiscoveryClarificationPanelProps) {
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [otherText, setOtherText] = useState<Record<string, string>>({});

  const allAnswered = useMemo(
    () =>
      questions.every((q) => {
        const val = answers[q.id];
        const otherEnabled = allowsOther(q.question_type, q.allows_other);

        if (isMulti(q.question_type)) {
          const selected = Array.isArray(val) ? val : [];
          if (selected.length === 0) return false;
          if (otherEnabled && selected.includes(OTHER_VALUE)) {
            return Boolean(otherText[q.id]?.trim());
          }
          return true;
        }

        if (typeof val !== "string" || !val.trim()) return false;
        if (otherEnabled && val === OTHER_VALUE) {
          return Boolean(otherText[q.id]?.trim());
        }
        return true;
      }),
    [answers, otherText, questions]
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

  const handleSubmit = () => {
    const payload: Record<string, string | string[]> = {};
    for (const q of questions) {
      const val = answers[q.id];
      const detail = otherText[q.id]?.trim() || "";
      const otherEnabled = allowsOther(q.question_type, q.allows_other);

      if (isMulti(q.question_type)) {
        const selected = Array.isArray(val) ? [...val] : [];
        if (otherEnabled && selected.includes(OTHER_VALUE)) {
          const withoutOther = selected.filter((v) => v !== OTHER_VALUE);
          payload[q.id] = detail
            ? [...withoutOther, `${OTHER_VALUE}:${detail}`]
            : withoutOther;
        } else {
          payload[q.id] = selected;
        }
      } else if (typeof val === "string" && otherEnabled && val === OTHER_VALUE && detail) {
        payload[q.id] = `${OTHER_VALUE}:${detail}`;
      } else {
        payload[q.id] = val as string;
      }
    }
    onSubmit(payload);
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

      {questions.map((q) => {
        const otherEnabled = allowsOther(q.question_type, q.allows_other);
        const showOtherField =
          otherEnabled &&
          (isMulti(q.question_type)
            ? Array.isArray(answers[q.id]) && (answers[q.id] as string[]).includes(OTHER_VALUE)
            : answers[q.id] === OTHER_VALUE);

        return (
          <div key={q.id} className="space-y-2">
            <div className="text-sm font-semibold text-white">{q.prompt}</div>
            <div className="space-y-2 mt-2">
              {isMulti(q.question_type)
                ? q.options.map((opt) => (
                    <label
                      key={opt.value}
                      className="flex gap-2 items-start p-3 rounded-lg border border-zinc-800 bg-zinc-900/40 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        className="mt-0.5"
                        checked={
                          Array.isArray(answers[q.id]) &&
                          (answers[q.id] as string[]).includes(opt.value)
                        }
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
            {showOtherField && (
              <textarea
                value={otherText[q.id] || ""}
                onChange={(e) =>
                  setOtherText((prev) => ({ ...prev, [q.id]: e.target.value }))
                }
                placeholder="Describe your situation…"
                className="w-full min-h-[72px] rounded-lg bg-black/30 border border-zinc-800 text-sm text-zinc-300 p-3 focus:outline-none focus:border-amber-500/40"
              />
            )}
          </div>
        );
      })}

      <div className="flex justify-end pt-2">
        <button
          type="button"
          disabled={!allAnswered || isSubmitting}
          onClick={handleSubmit}
          className="px-5 py-2.5 bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black text-sm font-bold rounded-xl transition-colors"
        >
          {isSubmitting ? "Building plan…" : "Continue to Day-1 plan"}
        </button>
      </div>
    </div>
  );
}

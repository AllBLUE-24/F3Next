"use client";

/**
 * Clarification UI — choice gaps (candidates) or free-text blocking gaps.
 */

import React, {
  useState, useRef, useEffect,
  type KeyboardEvent, type ChangeEvent,
} from "react";
import { OPTIONAL_FIELD_SKIP_PHRASES } from "@/types/gates";

interface Props {
  question: string;
  round: number;
  field?: string;
  candidates?: string[];
  lockedContext?: string[];
  onAnswer: (answer: string) => void;
  submitting?: boolean;
}

export default function ClarificationBlock({
  question,
  round,
  field,
  candidates = [],
  lockedContext = [],
  onAnswer,
  submitting = false,
}: Props): React.JSX.Element {
  const [value, setValue] = useState<string>("");
  const [selected, setSelected] = useState<string>("");
  const [focused, setFocused] = useState<boolean>(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const hasChoices = candidates.length > 0;
  const isOptionalField = field === "delivery_date" || field === "schedule_date";

  useEffect((): void => {
    if (!hasChoices) {
      inputRef.current?.focus();
    }
  }, [question, hasChoices]);

  function submit(answer?: string): void {
    const trimmed = (answer ?? (hasChoices ? selected : value)).trim();
    if (!trimmed || submitting) return;
    onAnswer(trimmed);
    setValue("");
    setSelected("");
  }

  function handleKey(e: KeyboardEvent<HTMLInputElement>): void {
    if (e.key === "Enter") { e.preventDefault(); submit(); }
  }

  return (
    <div style={{
      borderTop:  "1px solid #21262d",
      background: "#0d1117",
      flexShrink: 0,
    }}>
      {lockedContext.length > 0 && (
        <div style={{ padding: "8px 20px 0", display: "flex", flexWrap: "wrap", gap: "6px" }}>
          {lockedContext.map((line) => (
            <span
              key={line}
              style={{
                fontSize: "10px",
                color: "#8b949e",
                border: "1px solid #30363d",
                borderRadius: "3px",
                padding: "2px 8px",
              }}
            >
              {line}
            </span>
          ))}
        </div>
      )}

      <div style={{
        padding:    "12px 20px 10px",
        borderLeft: "3px solid #e3b341",
        background: "linear-gradient(90deg, rgba(227,179,65,0.04) 0%, transparent 100%)",
        marginBottom: "2px",
      }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: "8px" }}>
          <span style={{ color: "#e3b341", fontSize: "11px", flexShrink: 0, marginTop: "2px" }}>?</span>
          <div>
            <p style={{ color: "#e3b341", fontSize: "12.5px", lineHeight: 1.6, letterSpacing: "0.2px" }}>
              {question}
            </p>
            {round > 1 && (
              <p style={{ color: "#484f58", fontSize: "10px", marginTop: "3px" }}>
                clarification round {round}
              </p>
            )}
          </div>
        </div>
      </div>

      {hasChoices ? (
        <div style={{ padding: "8px 20px 12px", display: "flex", flexDirection: "column", gap: "6px" }}>
          {candidates.map((c) => (
            <label
              key={c}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "8px 10px",
                border: `1px solid ${selected === c ? "#e3b341" : "#30363d"}`,
                borderRadius: "4px",
                cursor: submitting ? "not-allowed" : "pointer",
                opacity: submitting ? 0.6 : 1,
              }}
            >
              <input
                type="radio"
                name="clarify-candidate"
                value={c}
                checked={selected === c}
                disabled={submitting}
                onChange={() => setSelected(c)}
                style={{ accentColor: "#e3b341" }}
              />
              <span style={{ color: "#c9d1d9", fontSize: "12.5px" }}>{c}</span>
            </label>
          ))}
          <button
            onClick={() => submit()}
            disabled={!selected.trim() || submitting}
            style={{
              alignSelf: "flex-start",
              marginTop: "4px",
              background: selected.trim() && !submitting ? "#e3b341" : "transparent",
              border: `1px solid ${selected.trim() ? "#e3b341" : "#30363d"}`,
              color: selected.trim() && !submitting ? "#0d1117" : "#484f58",
              fontSize: "10px",
              fontWeight: 600,
              letterSpacing: "1.5px",
              padding: "6px 14px",
              borderRadius: "3px",
              cursor: selected.trim() && !submitting ? "pointer" : "not-allowed",
            }}
          >
            {submitting ? "SENDING…" : "USE SELECTION"}
          </button>
        </div>
      ) : (
        <>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 20px 10px",
          }}>
            <span style={{ color: "#e3b341", fontSize: "14px", fontWeight: 600, flexShrink: 0 }}>?</span>
            <input
              ref={inputRef}
              type="text"
              value={value}
              placeholder="type your answer..."
              disabled={submitting}
              onChange={(e: ChangeEvent<HTMLInputElement>): void => setValue(e.target.value)}
              onKeyDown={handleKey}
              onFocus={(): void => setFocused(true)}
              onBlur={(): void => setFocused(false)}
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                borderBottom: `1px solid ${focused ? "#e3b341" : "#30363d"}`,
                outline: "none",
                fontFamily: "inherit",
                fontSize: "13px",
                color: "#c9d1d9",
                caretColor: "#e3b341",
                padding: "4px 0",
                letterSpacing: "0.3px",
                transition: "border-color 0.2s",
              }}
              spellCheck={false}
              autoComplete="off"
            />
            <button
              onClick={() => submit()}
              disabled={!value.trim() || submitting}
              style={{
                background: value.trim() && !submitting ? "#e3b341" : "transparent",
                border: `1px solid ${value.trim() ? "#e3b341" : "#30363d"}`,
                color: value.trim() && !submitting ? "#0d1117" : "#484f58",
                fontSize: "10px",
                fontFamily: "inherit",
                fontWeight: 600,
                letterSpacing: "1.5px",
                padding: "4px 12px",
                borderRadius: "3px",
                cursor: value.trim() && !submitting ? "pointer" : "not-allowed",
                flexShrink: 0,
              }}
            >
              {submitting ? "…" : "ANSWER"}
            </button>
          </div>

          {isOptionalField && (
            <div style={{ padding: "0 20px 10px", display: "flex", gap: "8px", flexWrap: "wrap" }}>
              {OPTIONAL_FIELD_SKIP_PHRASES.slice(0, 3).map((phrase) => (
                <button
                  key={phrase}
                  type="button"
                  disabled={submitting}
                  onClick={() => submit(phrase)}
                  style={{
                    fontSize: "10px",
                    color: "#8b949e",
                    border: "1px solid #30363d",
                    borderRadius: "999px",
                    padding: "3px 10px",
                    background: "transparent",
                    cursor: submitting ? "not-allowed" : "pointer",
                  }}
                >
                  {phrase}
                </button>
              ))}
            </div>
          )}

          <p style={{ color: "#21262d", fontSize: "9.5px", padding: "0 20px 10px", letterSpacing: "0.5px" }}>
            ↵ to answer
          </p>
        </>
      )}
    </div>
  );
}

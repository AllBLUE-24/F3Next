"use client";

/**
 * components/OS/ClarificationBlock.tsx
 *
 * Shown when the workflow needs a clarification answer.
 * Replaces the TerminalInput entirely — renders as a question prompt
 * in the same terminal style, keeping the visual flow unbroken.
 */

import React, {
  useState, useRef, useEffect,
  type KeyboardEvent, type ChangeEvent,
} from "react";

interface Props {
  question: string;
  round:    number;
  onAnswer: (answer: string) => void;
}

export default function ClarificationBlock({ question, round, onAnswer }: Props): React.JSX.Element {
  const [value,   setValue]   = useState<string>("");
  const [focused, setFocused] = useState<boolean>(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect((): void => {
    inputRef.current?.focus();
  }, [question]);

  function submit(): void {
    const trimmed = value.trim();
    if (!trimmed) return;
    onAnswer(trimmed);
    setValue("");
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
      {/* Question block */}
      <div style={{
        padding:    "12px 20px 10px",
        borderLeft: "3px solid #e3b341",
        background: "linear-gradient(90deg, rgba(227,179,65,0.04) 0%, transparent 100%)",
        marginBottom: "2px",
      }}>
        <div style={{
          display:    "flex",
          alignItems: "flex-start",
          gap:        "8px",
        }}>
          <span style={{ color: "#e3b341", fontSize: "11px", flexShrink: 0, marginTop: "2px" }}>?</span>
          <div>
            <p style={{
              color:      "#e3b341",
              fontSize:   "12.5px",
              lineHeight: 1.6,
              letterSpacing: "0.2px",
            }}>
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

      {/* Answer input */}
      <div style={{
        display:    "flex",
        alignItems: "center",
        gap:        "8px",
        padding:    "10px 20px 10px",
      }}>
        <span style={{ color: "#e3b341", fontSize: "14px", fontWeight: 600, flexShrink: 0 }}>?</span>

        <input
          ref={inputRef}
          type="text"
          value={value}
          placeholder="type your answer..."
          onChange={(e: ChangeEvent<HTMLInputElement>): void => setValue(e.target.value)}
          onKeyDown={handleKey}
          onFocus={(): void => setFocused(true)}
          onBlur={(): void => setFocused(false)}
          style={{
            flex:       1,
            background: "transparent",
            border:     "none",
            borderBottom: `1px solid ${focused ? "#e3b341" : "#30363d"}`,
            outline:    "none",
            fontFamily: "inherit",
            fontSize:   "13px",
            color:      "#c9d1d9",
            caretColor: "#e3b341",
            padding:    "4px 0",
            letterSpacing: "0.3px",
            transition: "border-color 0.2s",
          }}
          spellCheck={false}
          autoComplete="off"
        />

        <button
          onClick={submit}
          disabled={!value.trim()}
          style={{
            background:   value.trim() ? "#e3b341" : "transparent",
            border:       `1px solid ${value.trim() ? "#e3b341" : "#30363d"}`,
            color:        value.trim() ? "#0d1117" : "#484f58",
            fontSize:     "10px",
            fontFamily:   "inherit",
            fontWeight:   600,
            letterSpacing:"1.5px",
            padding:      "4px 12px",
            borderRadius: "3px",
            cursor:       value.trim() ? "pointer" : "not-allowed",
            transition:   "all 0.15s",
            flexShrink:   0,
          }}
        >
          ANSWER
        </button>
      </div>

      <p style={{ color: "#21262d", fontSize: "9.5px", padding: "0 20px 10px", letterSpacing: "0.5px" }}>
        ↵ to answer
      </p>
    </div>
  );
}
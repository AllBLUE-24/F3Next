"use client";

/**
 * components/OS/TerminalInput.tsx
 *
 * The command prompt input at the bottom.
 * Looks like:  [companyId] $  <input>
 *
 * Features:
 *  - Enter to submit, Shift+Enter for newline
 *  - Command history: ↑ / ↓ to cycle through past prompts
 *  - Auto-growing textarea (max 6 lines)
 *  - Disabled + loading state while processing
 *  - Error state with dismiss button
 */

import React, {
  useState, useRef, useEffect, useCallback,
  type KeyboardEvent, type ChangeEvent,
} from "react";
import type { UiPhase } from "@/types/types";

interface Props {
  companyId:        string;
  onSubmit:         (prompt: string) => void;
  disabled?:        boolean;
  phase:            UiPhase;
  onDismissError?:  () => void;
}

const MAX_HISTORY = 50;

export default function TerminalInput({
  companyId, onSubmit, disabled = false, phase, onDismissError,
}: Props): React.JSX.Element {
  const [value,    setValue]    = useState<string>("");
  const [focused,  setFocused]  = useState<boolean>(false);
  const [history,  setHistory]  = useState<string[]>([]);
  const [histIdx,  setHistIdx]  = useState<number>(-1);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isError     = phase === "error";
  const isLoading   = phase === "submitting" || phase === "polling";

  // Auto-focus when unlocked
  useEffect((): void => {
    if (!disabled) textareaRef.current?.focus();
  }, [disabled]);

  // Auto-resize
  const resize = useCallback((): void => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const lineH  = 22; // px per line at 13px mono
    const maxH   = lineH * 6;
    el.style.height = `${Math.min(el.scrollHeight, maxH)}px`;
  }, []);

  useEffect((): void => { resize(); }, [value, resize]);

  // Submit
  const submit = useCallback((): void => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    // Add to history
    setHistory((prev: string[]) => {
      const next = [trimmed, ...prev.filter((h: string) => h !== trimmed)];
      return next.slice(0, MAX_HISTORY);
    });
    setHistIdx(-1);
    setValue("");
    onSubmit(trimmed);
  }, [value, disabled, onSubmit]);

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>): void => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
      return;
    }
    // History navigation
    if (e.key === "ArrowUp" && value === "") {
      e.preventDefault();
      const nextIdx = Math.min(histIdx + 1, history.length - 1);
      setHistIdx(nextIdx);
      setValue(history[nextIdx] ?? "");
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      const nextIdx = histIdx - 1;
      if (nextIdx < 0) { setHistIdx(-1); setValue(""); }
      else { setHistIdx(nextIdx); setValue(history[nextIdx] ?? ""); }
    }
  }, [submit, value, history, histIdx]);

  const prompt = `${companyId.toLowerCase()}`;

  return (
    <div style={{
      borderTop:  "1px solid #161b22",
      background: "#0d1117",
      flexShrink: 0,
    }}>
      {/* Error banner */}
      {isError && onDismissError && (
        <div style={{
          display:     "flex",
          alignItems:  "center",
          gap:         "8px",
          padding:     "8px 20px",
          background:  "rgba(248,81,73,.08)",
          borderBottom:"1px solid rgba(248,81,73,.2)",
        }}>
          <span style={{ color: "#f85149", fontSize: "11px", flex: 1 }}>
            Command failed. Review the output above.
          </span>
          <button
            onClick={onDismissError}
            style={{
              background: "transparent",
              border:     "1px solid rgba(248,81,73,.4)",
              color:      "#f85149",
              fontSize:   "10px",
              padding:    "2px 10px",
              borderRadius: "4px",
              cursor:     "pointer",
              letterSpacing: "1px",
            }}
          >
            CLEAR
          </button>
        </div>
      )}

      {/* Prompt line */}
      <div style={{
        display:    "flex",
        alignItems: "flex-end",
        gap:        "0",
        padding:    "12px 20px 12px",
        outline:    focused ? "none" : "none",
      }}>
        {/* $ prefix */}
        <div style={{
          display:    "flex",
          alignItems: "flex-end",
          gap:        "6px",
          paddingBottom: "1px",
          flexShrink: 0,
          marginRight: "8px",
        }}>
          <span style={{ color: "#58a6ff", fontSize: "12px", letterSpacing: "0.5px" }}>
            {prompt}
          </span>
          <span style={{
            color:      isLoading ? "#f0a500" : isError ? "#f85149" : "#f0a500",
            fontSize:   "14px",
            fontWeight: 600,
            lineHeight: 1,
            marginBottom: "2px",
            transition: "color 0.2s",
          }}>
            $
          </span>
        </div>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={value}
          rows={1}
          disabled={disabled}
          placeholder={
            isLoading ? "processing..." :
            isError   ? "type next command or CLEAR above..." :
            "type a command..."
          }
          onChange={(e: ChangeEvent<HTMLTextAreaElement>): void => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={(): void => setFocused(true)}
          onBlur={(): void => setFocused(false)}
          style={{
            flex:       1,
            background: "transparent",
            border:     "none",
            outline:    "none",
            resize:     "none",
            overflow:   "hidden",
            fontFamily: "inherit",
            fontSize:   "13px",
            lineHeight: "22px",
            color:      disabled ? "#484f58" : "#c9d1d9",
            caretColor: "#f0a500",
            letterSpacing: "0.3px",
          }}
          spellCheck={false}
          autoCorrect="off"
          autoCapitalize="off"
        />

        {/* Loading indicator OR send hint */}
        <div style={{
          flexShrink: 0,
          paddingBottom: "2px",
          marginLeft: "8px",
        }}>
          {isLoading ? (
            <span style={{
              color:      "#f0a500",
              fontSize:   "10px",
              letterSpacing: "1.5px",
              animation:  "blink 1s step-end infinite",
            }}>
              ▮
            </span>
          ) : value.trim() ? (
            <span style={{ color: "#30363d", fontSize: "9.5px", letterSpacing: "0.5px" }}>
              ↵
            </span>
          ) : null}
        </div>
      </div>

      {/* Hint bar */}
      <div style={{
        display:    "flex",
        alignItems: "center",
        gap:        "16px",
        padding:    "0 20px 10px",
        color:      "#30363d",
        fontSize:   "9.5px",
        letterSpacing: "0.5px",
      }}>
        <span>↵ run</span>
        <span>⇧↵ newline</span>
        <span>↑↓ history</span>
        {history.length > 0 && (
          <span style={{ marginLeft: "auto", color: "#21262d" }}>
            {history.length} in history
          </span>
        )}
      </div>

      <style>{`
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        textarea::placeholder { color: #30363d; }
        textarea:disabled::placeholder { color: #21262d; }
      `}</style>
    </div>
  );
}
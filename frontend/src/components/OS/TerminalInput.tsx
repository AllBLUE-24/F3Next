"use client";

/**
 * components/OS/TerminalInput.tsx
 *
 * Upgraded Premium Terminal Input with "Modes".
 * Hit TAB to cycle through: EXECUTE ⚡, ANALYZE 📊, SEARCH 🔍
 */

import React, {
  useState, useRef, useEffect, useCallback,
  type KeyboardEvent, type ChangeEvent,
} from "react";
import type { UiPhase } from "@/types/types";

export type CommandMode = "execute" | "analyze" | "search";

interface Props {
  companyId:        string;
  onSubmit:         (prompt: string, mode: CommandMode) => void;
  disabled?:        boolean;
  phase:            UiPhase;
  onDismissError?:  () => void;
}

const MAX_HISTORY = 50;

const MODES: Record<CommandMode, { label: string; color: string; icon: string }> = {
  execute: { label: "EXECUTE", color: "#f0a500", icon: "⚡" },
  analyze: { label: "ANALYZE", color: "#a371f7", icon: "📊" },
  search:  { label: "SEARCH",  color: "#38bdf8", icon: "🔍" },
};

const MODE_KEYS = Object.keys(MODES) as CommandMode[];

export default function TerminalInput({
  companyId, onSubmit, disabled = false, phase, onDismissError,
}: Props): React.JSX.Element {
  const [value,    setValue]    = useState<string>("");
  const [mode,     setMode]     = useState<CommandMode>("execute");
  const [focused,  setFocused]  = useState<boolean>(false);
  const [history,  setHistory]  = useState<string[]>([]);
  const [histIdx,  setHistIdx]  = useState<number>(-1);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isError     = phase === "error";
  const isLoading   = phase === "submitting" || phase === "polling";
  const activeMode  = MODES[mode];

  // Auto-focus when unlocked
  useEffect((): void => {
    if (!disabled) textareaRef.current?.focus();
  }, [disabled]);

  // Auto-resize
  const resize = useCallback((): void => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const lineH  = 22; 
    const maxH   = lineH * 6;
    el.style.height = `${Math.min(el.scrollHeight, maxH)}px`;
  }, []);

  useEffect((): void => { resize(); }, [value, resize]);

  // Submit
  const submit = useCallback((): void => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    setHistory((prev: string[]) => {
      const next = [trimmed, ...prev.filter((h: string) => h !== trimmed)];
      return next.slice(0, MAX_HISTORY);
    });
    setHistIdx(-1);
    setValue("");
    onSubmit(trimmed, mode);
  }, [value, disabled, mode, onSubmit]);

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>): void => {
    // Mode Switching
    if (e.key === "Tab") {
      e.preventDefault();
      const currentIdx = MODE_KEYS.indexOf(mode);
      setMode(MODE_KEYS[(currentIdx + 1) % MODE_KEYS.length]);
      return;
    }
    // Submit
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
  }, [submit, value, history, histIdx, mode]);

  return (
    <div style={{
      borderTop:  "1px solid #161b22",
      background: "#0a0d14",
      flexShrink: 0,
      position:   "relative",
      boxShadow:  focused ? `0 -10px 30px ${activeMode.color}08` : "none",
      transition: "box-shadow 0.3s ease",
    }}>
      {/* Error banner */}
      {isError && onDismissError && (
        <div style={{
          display: "flex", alignItems: "center", gap: "8px", padding: "8px 20px",
          background: "rgba(248,81,73,.08)", borderBottom:"1px solid rgba(248,81,73,.2)",
        }}>
          <span style={{ color: "#f85149", fontSize: "11px", flex: 1 }}>
            Command failed. Review the output above.
          </span>
          <button onClick={onDismissError} style={{
              background: "transparent", border: "1px solid rgba(248,81,73,.4)",
              color: "#f85149", fontSize: "10px", padding: "2px 10px", borderRadius: "4px",
              cursor: "pointer", letterSpacing: "1px",
            }}>CLEAR</button>
        </div>
      )}

      {/* Prompt container */}
      <div style={{
        display: "flex", alignItems: "flex-start", padding: "14px 20px", gap: "12px",
      }}>
        {/* Mode Badge */}
        <div 
          onClick={() => {
            const currentIdx = MODE_KEYS.indexOf(mode);
            setMode(MODE_KEYS[(currentIdx + 1) % MODE_KEYS.length]);
            textareaRef.current?.focus();
          }}
          style={{
            display: "flex", alignItems: "center", gap: "6px",
            padding: "4px 8px", borderRadius: "6px", cursor: "pointer",
            background: `${activeMode.color}15`,
            border: `1px solid ${activeMode.color}30`,
            marginTop: "1px", flexShrink: 0,
            transition: "all 0.2s ease",
            userSelect: "none"
        }}>
          <span style={{ fontSize: "10px" }}>{activeMode.icon}</span>
          <span style={{ 
            color: activeMode.color, fontSize: "9.5px", fontWeight: 700, 
            letterSpacing: "1px", paddingTop: "1px" 
          }}>
            {activeMode.label}
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
            "What would you like to do?..."
          }
          onChange={(e: ChangeEvent<HTMLTextAreaElement>): void => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={(): void => setFocused(true)}
          onBlur={(): void => setFocused(false)}
          style={{
            flex: 1, background: "transparent", border: "none", outline: "none",
            resize: "none", overflow: "hidden", fontFamily: "inherit",
            fontSize: "14px", lineHeight: "24px", color: disabled ? "#484f58" : "#e6edf3",
            caretColor: activeMode.color, letterSpacing: "0.3px", marginTop: "1px"
          }}
          spellCheck={false}
        />

        {/* Loading indicator */}
        <div style={{ flexShrink: 0, marginTop: "6px" }}>
          {isLoading ? (
            <span style={{ color: activeMode.color, fontSize: "10px", animation: "blink 1s step-end infinite" }}>▮</span>
          ) : value.trim() ? (
            <span style={{ color: "#30363d", fontSize: "10px" }}>↵</span>
          ) : null}
        </div>
      </div>

      {/* Hint bar */}
      <div style={{
        display: "flex", alignItems: "center", gap: "16px", padding: "0 20px 12px",
        color: "#30363d", fontSize: "9.5px", letterSpacing: "0.5px",
      }}>
        <span><kbd style={kbdStyle}>⇥</kbd> tab to cycle mode</span>
        <span><kbd style={kbdStyle}>↵</kbd> run</span>
        <span><kbd style={kbdStyle}>⇧↵</kbd> newline</span>
        <span><kbd style={kbdStyle}>↑</kbd> history</span>
        {history.length > 0 && <span style={{ marginLeft: "auto", color: "#21262d" }}>{history.length} in history</span>}
      </div>

      <style>{`
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        textarea::placeholder { color: #30363d; }
        textarea:disabled::placeholder { color: #21262d; }
      `}</style>
    </div>
  );
}

const kbdStyle = {
  background: "#161b22", padding: "2px 4px", borderRadius: "3px", 
  border: "1px solid #30363d", fontSize: "9px", marginRight: "4px"
};
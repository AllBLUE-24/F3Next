"use client";

/**
 * components/OS/ConfirmationBlock.tsx
 *
 * Shown when the OS needs user approval before executing.
 * Renders INLINE above the input — like a "diff preview" before a git push.
 * Not a modal. Never overlays content.
 */

import React from "react";
import type { ConfirmationRequest } from "@/lib/api/os-api";

interface Props {
  request:  ConfirmationRequest;
  onDecide: (decision: "confirm" | "cancel") => void;
}

const RISK_COLORS = {
  low:    { accent: "#3fb950", bg: "rgba(63,185,80,0.05)",  border: "rgba(63,185,80,0.3)"  },
  medium: { accent: "#e3b341", bg: "rgba(227,179,65,0.05)", border: "rgba(227,179,65,0.3)" },
  high:   { accent: "#f85149", bg: "rgba(248,81,73,0.05)",  border: "rgba(248,81,73,0.3)"  },
} as const;

export default function ConfirmationBlock({ request, onDecide }: Props): React.JSX.Element {
  const risk    = (request.risk_level ?? "medium") as keyof typeof RISK_COLORS;
  const colors  = RISK_COLORS[risk] ?? RISK_COLORS.medium;
  const preview = request.preview;

  return (
    <div style={{
      borderTop:  `1px solid ${colors.border}`,
      background: colors.bg,
      flexShrink: 0,
      maxHeight:  "280px",
      overflowY:  "auto",
      scrollbarWidth: "thin",
      scrollbarColor: "#30363d #0d1117",
    }}>
      {/* Header */}
      <div style={{
        display:    "flex",
        alignItems: "center",
        gap:        "8px",
        padding:    "12px 20px 8px",
        borderBottom: "1px solid #161b22",
      }}>
        <span style={{ color: colors.accent, fontSize: "12px", fontWeight: 600 }}>⚠</span>
        <span style={{ color: colors.accent, fontSize: "11px", fontWeight: 600, letterSpacing: "1.5px" }}>
          CONFIRM REQUIRED
        </span>
        <span style={{
          marginLeft:   "auto",
          fontSize:     "9px",
          fontWeight:   700,
          letterSpacing:"2px",
          padding:      "1px 8px",
          border:       `1px solid ${colors.border}`,
          color:        colors.accent,
          borderRadius: "3px",
        }}>
          {risk.toUpperCase()} RISK
        </span>
      </div>

      {/* Preview */}
      {preview && (
        <div style={{ padding: "10px 20px", display: "flex", flexDirection: "column", gap: "8px" }}>

          {preview.action_summary && (
            <div style={{ display: "flex", gap: "8px" }}>
              <span style={{ color: "#484f58", fontSize: "10px", letterSpacing: "1px", flexShrink: 0, marginTop: "3px" }}>
                ACTION
              </span>
              <span style={{ color: "#c9d1d9", fontSize: "12.5px" }}>{preview.action_summary}</span>
            </div>
          )}

          {preview.entities && preview.entities.length > 0 && (
            <div style={{ display: "flex", gap: "8px", alignItems: "flex-start" }}>
              <span style={{ color: "#484f58", fontSize: "10px", letterSpacing: "1px", flexShrink: 0, marginTop: "3px" }}>
                FIELDS
              </span>
              <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                {preview.entities.map((line: string, i: number) => (
                  <span key={i} style={{ color: "#8b949e", fontSize: "11.5px", fontFamily: "inherit" }}>
                    {line}
                  </span>
                ))}
              </div>
            </div>
          )}

          {preview.warnings && preview.warnings.length > 0 && (
            <div style={{
              padding:    "6px 10px",
              borderLeft: "2px solid #e3b341",
              background: "rgba(227,179,65,0.05)",
              borderRadius: "0 3px 3px 0",
            }}>
              {preview.warnings.map((w: { field: string; message: string }, i: number) => (
                <p key={i} style={{ color: "#e3b341", fontSize: "11.5px" }}>⚠ {w.message}</p>
              ))}
            </div>
          )}

          {preview.auto_corrections && preview.auto_corrections.length > 0 && (
            <div style={{
              padding:    "6px 10px",
              borderLeft: "2px solid #58a6ff",
              background: "rgba(88,166,255,0.05)",
              borderRadius: "0 3px 3px 0",
            }}>
              {preview.auto_corrections.map((c: { field: string; corrected: string; reason: string }, i: number) => (
                <p key={i} style={{ color: "#58a6ff", fontSize: "11px" }}>
                  ~ {c.field}: {c.corrected}
                  {c.reason && <span style={{ color: "#484f58" }}> — {c.reason}</span>}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div style={{
        display:    "flex",
        gap:        "10px",
        padding:    "10px 20px 14px",
        borderTop:  "1px solid #161b22",
      }}>
        <button
          onClick={(): void => onDecide("cancel")}
          style={{
            background:   "transparent",
            border:       "1px solid #30363d",
            color:        "#6e7681",
            fontSize:     "11px",
            fontFamily:   "inherit",
            fontWeight:   500,
            letterSpacing:"1.5px",
            padding:      "6px 16px",
            borderRadius: "3px",
            cursor:       "pointer",
            transition:   "all 0.15s",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.borderColor = "#f85149";
            (e.currentTarget as HTMLButtonElement).style.color = "#f85149";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.borderColor = "#30363d";
            (e.currentTarget as HTMLButtonElement).style.color = "#6e7681";
          }}
        >
          CANCEL
        </button>
        <button
          onClick={(): void => onDecide("confirm")}
          style={{
            background:   colors.accent,
            border:       `1px solid ${colors.accent}`,
            color:        "#0d1117",
            fontSize:     "11px",
            fontFamily:   "inherit",
            fontWeight:   700,
            letterSpacing:"1.5px",
            padding:      "6px 20px",
            borderRadius: "3px",
            cursor:       "pointer",
            transition:   "opacity 0.15s",
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "0.85"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "1"; }}
        >
          CONFIRM ↵
        </button>

        {risk === "high" && (
          <span style={{ color: "#f85149", fontSize: "10px", alignSelf: "center", marginLeft: "4px" }}>
            ⚠ irreversible
          </span>
        )}
      </div>
    </div>
  );
}
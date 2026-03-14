"use client";

/**
 * components/OS/PipelineStatus.tsx
 *
 * Horizontal pipeline step tracker shown only while a command is processing.
 * Design: looks like a build pipeline in a CI tool — steps separated by arrows,
 * current step highlighted in amber with a pulse, completed steps in faded green.
 */

import React from "react";
import { PIPELINE_STEPS, STEP_STATUS, type PipelineKey } from "@/types/types";
import type { AgentStep } from "@/lib/api/os-api";

interface Props {
  step:    AgentStep;
  visible: boolean;
}

// Pause states that pause between specific steps
const PAUSE_STEP_MAP: Partial<Record<AgentStep, PipelineKey>> = {
  awaiting_clarification: "clarity",
  awaiting_confirmation:  "validating",
};

export default function PipelineStatus({ step, visible }: Props): React.JSX.Element | null {
  if (!visible && step === "") return null;

  const effectiveStep = (PAUSE_STEP_MAP[step] ?? step) as PipelineKey | "";
  const currentIdx    = PIPELINE_STEPS.findIndex((s) => s.key === effectiveStep);
  const statusLabel   = STEP_STATUS[step] ?? "Processing...";

  return (
    <div style={{
      borderBottom: "1px solid #161b22",
      background:   "#0d1117",
      padding:      "10px 20px",
      flexShrink:   0,
      opacity:      visible ? 1 : 0,
      transition:   "opacity 0.3s ease",
    }}>
      {/* Status label */}
      <div style={{
        fontSize:    "10px",
        color:       "#f0a500",
        letterSpacing: "1.5px",
        textTransform: "uppercase",
        marginBottom: "8px",
        display:     "flex",
        alignItems:  "center",
        gap:         "8px",
      }}>
        <Spinner />
        {statusLabel}
      </div>

      {/* Step pills */}
      <div style={{
        display:    "flex",
        alignItems: "center",
        gap:        "0",
        overflowX:  "auto",
        paddingBottom: "2px",
      }}>
        {PIPELINE_STEPS.map((s, i) => {
          const done    = currentIdx > i;
          const active  = currentIdx === i;
          const pending = currentIdx < i || currentIdx === -1;

          return (
            <React.Fragment key={s.key}>
              {i > 0 && (
                <span style={{
                  color:      done ? "#238636" : "#30363d",
                  fontSize:   "10px",
                  margin:     "0 4px",
                  flexShrink: 0,
                  transition: "color 0.3s",
                }}>▸</span>
              )}
              <div style={{
                display:     "flex",
                alignItems:  "center",
                gap:         "5px",
                padding:     "2px 8px",
                borderRadius: "4px",
                border:      `1px solid ${active ? "#f0a500" : done ? "#238636" : "#21262d"}`,
                background:  active ? "rgba(240,165,0,.08)" : done ? "rgba(35,134,54,.06)" : "transparent",
                flexShrink:  0,
                transition:  "all 0.25s ease",
              }}>
                {/* Indicator dot */}
                <span style={{
                  width:        "5px",
                  height:       "5px",
                  borderRadius: "50%",
                  background:   active ? "#f0a500" : done ? "#3fb950" : "#30363d",
                  boxShadow:    active ? "0 0 8px #f0a500" : done ? "0 0 4px #3fb950" : "none",
                  animation:    active ? "pulseDot 1.2s ease-in-out infinite" : "none",
                  flexShrink:   0,
                }} />
                <span style={{
                  fontSize:    "9.5px",
                  fontWeight:  active ? 600 : 400,
                  letterSpacing: "1px",
                  color:       active ? "#f0a500" : done ? "#3fb950" : "#484f58",
                  whiteSpace:  "nowrap",
                  transition:  "color 0.25s",
                }}>
                  {s.label}
                </span>
              </div>
            </React.Fragment>
          );
        })}
      </div>

      <style>{`
        @keyframes pulseDot {
          0%, 100% { opacity: 1; transform: scale(1); }
          50%       { opacity: 0.5; transform: scale(1.3); }
        }
      `}</style>
    </div>
  );
}

function Spinner(): React.JSX.Element {
  return (
    <svg
      width="10" height="10" viewBox="0 0 10 10" fill="none"
      style={{ animation: "spin 0.8s linear infinite", flexShrink: 0 }}
    >
      <circle cx="5" cy="5" r="4" stroke="#f0a50040" strokeWidth="1.5" />
      <path d="M5 1a4 4 0 0 1 4 4" stroke="#f0a500" strokeWidth="1.5" strokeLinecap="round" />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </svg>
  );
}
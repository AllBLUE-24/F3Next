"use client";

/**
 * components/OS/OutputLog.tsx
 *
 * The main scrollable output area.
 * Messages render as terminal output — NOT chat bubbles.
 *
 *   User prompt:     > create SO for ABC...          (amber, left)
 *   Assistant resp:  structured block, teal left border
 *   System note:     · dimmed, centered
 *   Error:           ✗ message in red
 */

import React, { useEffect, useRef } from "react";
import type { LogEntry, UiPhase } from "@/types/types";

interface Props {
  entries:   LogEntry[];
  companyId: string;
  phase:     UiPhase;
}

function formatTime(d: Date): string {
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState({ companyId }: { companyId: string }): React.JSX.Element {
  const examples = [
    "Create SO for ABC Industries — 100 units of Product-001 at ₹500",
    "Check stock of Steel Rod 10mm in Main Warehouse",
    "Show all pending sales orders this month",
    "Record payment from Tata Corp ₹50,000 via NEFT",
    "Create purchase order for Steel Corp — 500 kg HR sheets at ₹70/kg",
  ];

  return (
    <div style={{
      display:        "flex",
      flexDirection:  "column",
      alignItems:     "flex-start",
      justifyContent: "center",
      height:         "100%",
      padding:        "40px 28px",
      gap:            "24px",
    }}>
      {/* Wordmark */}
      <div>
        <p style={{ color: "#f0a500", fontSize: "13px", fontWeight: 700, letterSpacing: "3px", marginBottom: "4px" }}>
          ERP-OS
        </p>
        <p style={{ color: "#30363d", fontSize: "11px", letterSpacing: "1px" }}>
          {companyId.toUpperCase()} · NATURAL LANGUAGE INTERFACE
        </p>
      </div>

      {/* Welcome line */}
      <div style={{ borderLeft: "2px solid #238636", paddingLeft: "14px" }}>
        <p style={{ color: "#8b949e", fontSize: "12.5px", lineHeight: 1.7 }}>
          Type a command in plain English below.<br />
          The OS will parse, validate and execute it against your ERPNext instance.
        </p>
      </div>

      {/* Example commands */}
      <div>
        <p style={{ color: "#484f58", fontSize: "10px", letterSpacing: "2px", marginBottom: "10px" }}>
          EXAMPLE COMMANDS
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {examples.map((ex, i) => (
            <div
              key={i}
              style={{
                display:    "flex",
                alignItems: "flex-start",
                gap:        "8px",
                opacity:    1 - i * 0.14,
              }}
            >
              <span style={{ color: "#f0a50060", fontSize: "11px", flexShrink: 0, marginTop: "1px" }}>$</span>
              <span style={{ color: "#6e7681", fontSize: "11.5px", lineHeight: 1.5 }}>{ex}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Individual log entries ───────────────────────────────────────────────────

function UserEntry({ entry }: { entry: LogEntry }): React.JSX.Element {
  return (
    <div style={{
      display:  "flex",
      gap:      "10px",
      padding:  "10px 28px",
      borderTop: "1px solid #161b22",
    }}>
      <span style={{ color: "#f0a500", fontSize: "13px", flexShrink: 0, marginTop: "1px", fontWeight: 600 }}>$</span>
      <div style={{ flex: 1 }}>
        <span style={{ color: "#f0a500", fontSize: "13px", lineHeight: 1.6, letterSpacing: "0.3px" }}>
          {entry.content}
        </span>
        <div style={{ color: "#30363d", fontSize: "9.5px", marginTop: "3px", letterSpacing: "0.5px" }}>
          {formatTime(entry.timestamp)}
        </div>
      </div>
    </div>
  );
}

function AssistantEntry({ entry }: { entry: LogEntry }): React.JSX.Element {
  const lines = entry.content.split("\n");

  return (
    <div style={{
      display:    "flex",
      gap:        "10px",
      padding:    "10px 28px 14px",
      borderTop:  "1px solid #161b22",
      borderLeft: "3px solid #00d4aa",
      marginLeft: "0",
      background: "linear-gradient(90deg, rgba(0,212,170,0.03) 0%, transparent 100%)",
    }}>
      <span style={{ color: "#00d4aa40", fontSize: "13px", flexShrink: 0, marginTop: "1px" }}>◈</span>
      <div style={{ flex: 1 }}>
        {lines.map((line: string, i: number) => {
          // Detect lines starting with ✅/❌/⚠️ for special styling
          const isSuccess = line.startsWith("✅");
          const isError   = line.startsWith("❌");
          const isWarn    = line.startsWith("⚠");
          const isBullet  = line.startsWith("•") || line.startsWith("-") || line.startsWith("→");
          const isHeader  = line.startsWith("#") || (line.endsWith(":") && !isBullet && line.length < 40);

          return (
            <p
              key={i}
              style={{
                fontSize:   "13px",
                lineHeight: 1.7,
                margin:     "0 0 2px",
                color:      isSuccess ? "#3fb950"
                           : isError   ? "#f85149"
                           : isWarn    ? "#e3b341"
                           : isHeader  ? "#c9d1d9"
                           : isBullet  ? "#8b949e"
                           : "#adbac7",
                fontWeight: isHeader ? 600 : 400,
                paddingLeft: isBullet ? "4px" : "0",
              }}
            >
              {line || "\u00a0"}
            </p>
          );
        })}
        <div style={{ color: "#30363d", fontSize: "9.5px", marginTop: "6px", letterSpacing: "0.5px" }}>
          {formatTime(entry.timestamp)}
        </div>
      </div>
    </div>
  );
}

function SystemEntry({ entry }: { entry: LogEntry }): React.JSX.Element {
  return (
    <div style={{ padding: "6px 28px", borderTop: "1px solid #161b22" }}>
      <span style={{ color: "#484f58", fontSize: "11px" }}>
        · {entry.content}
      </span>
    </div>
  );
}

function ErrorEntry({ entry }: { entry: LogEntry }): React.JSX.Element {
  return (
    <div style={{
      display:    "flex",
      gap:        "10px",
      padding:    "10px 28px",
      borderTop:  "1px solid #161b22",
      borderLeft: "3px solid #f85149",
      background: "linear-gradient(90deg, rgba(248,81,73,0.05) 0%, transparent 100%)",
    }}>
      <span style={{ color: "#f85149", fontSize: "13px", flexShrink: 0, marginTop: "1px" }}>✗</span>
      <span style={{ color: "#f85149", fontSize: "13px", lineHeight: 1.6 }}>{entry.content}</span>
    </div>
  );
}

// ─── OutputLog ────────────────────────────────────────────────────────────────

export default function OutputLog({ entries, companyId, phase }: Props): React.JSX.Element {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect((): void => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  if (entries.length === 0) {
    return <EmptyState companyId={companyId} />;
  }

  return (
    <div style={{
      height:    "100%",
      overflowY: "auto",
      overflowX: "hidden",
      // Custom scrollbar
      scrollbarWidth: "thin",
      scrollbarColor: "#30363d #0d1117",
    }}>
      <div style={{ paddingTop: "8px", paddingBottom: "8px" }}>
        {entries.map((e: LogEntry) => {
          if (e.role === "user")      return <UserEntry      key={e.id} entry={e} />;
          if (e.role === "assistant") return <AssistantEntry key={e.id} entry={e} />;
          if (e.role === "error")     return <ErrorEntry     key={e.id} entry={e} />;
          return                             <SystemEntry    key={e.id} entry={e} />;
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
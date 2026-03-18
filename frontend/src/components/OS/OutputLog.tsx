"use client";

/**
 * components/OS/OutputLog.tsx
 *
 * Upgraded Output Log with modern dashboard empty state
 * and CSS fade-in animations for entries.
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

function EmptyState({ companyId }: { companyId: string }): React.JSX.Element {
  return (
    <div className="fade-in" style={{
      display: "flex", flexDirection: "column", height: "100%",
      padding: "50px 32px", gap: "32px",
    }}>
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
          <span style={{ background: "#f0a500", color: "#000", padding: "2px 6px", borderRadius: "4px", fontSize: "10px", fontWeight: 800, letterSpacing: "1px" }}>F3NEXT</span>
          <p style={{ color: "#c9d1d9", fontSize: "18px", fontWeight: 600, letterSpacing: "1px" }}>
            ERP Operating System
          </p>
        </div>
        <p style={{ color: "#6e7681", fontSize: "12px", letterSpacing: "0.5px" }}>
          Connected to: <strong style={{ color: "#8b949e" }}>{companyId.toUpperCase()}</strong>
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px", maxWidth: "800px" }}>
        {/* EXECUTE */}
        <div style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: "8px", padding: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
            <span style={{ fontSize: "14px" }}>⚡</span>
            <span style={{ color: "#f0a500", fontSize: "11px", fontWeight: 700, letterSpacing: "1px" }}>EXECUTE MODE</span>
          </div>
          <p style={{ color: "#8b949e", fontSize: "11.5px", lineHeight: 1.6 }}>Create, update, or submit documents to the ERP.</p>
          <p style={{ color: "#484f58", fontSize: "10px", marginTop: "12px" }}>"Create a PO for 5 laptops"</p>
        </div>
        {/* ANALYZE */}
        <div style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: "8px", padding: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
            <span style={{ fontSize: "14px" }}>📊</span>
            <span style={{ color: "#a371f7", fontSize: "11px", fontWeight: 700, letterSpacing: "1px" }}>ANALYZE MODE</span>
          </div>
          <p style={{ color: "#8b949e", fontSize: "11.5px", lineHeight: 1.6 }}>Generate reports, calculate totals, and chart data.</p>
          <p style={{ color: "#484f58", fontSize: "10px", marginTop: "12px" }}>"Show me sales by region"</p>
        </div>
        {/* SEARCH */}
        <div style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: "8px", padding: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
            <span style={{ fontSize: "14px" }}>🔍</span>
            <span style={{ color: "#38bdf8", fontSize: "11px", fontWeight: 700, letterSpacing: "1px" }}>SEARCH MODE</span>
          </div>
          <p style={{ color: "#8b949e", fontSize: "11.5px", lineHeight: 1.6 }}>Find specific records, customers, or items quickly.</p>
          <p style={{ color: "#484f58", fontSize: "10px", marginTop: "12px" }}>"Find invoice INV-002"</p>
        </div>
      </div>
    </div>
  );
}

function UserEntry({ entry }: { entry: LogEntry }): React.JSX.Element {
  return (
    <div className="fade-in" style={{ display: "flex", gap: "12px", padding: "12px 32px", borderTop: "1px solid #161b22" }}>
      <span style={{ color: "#6e7681", fontSize: "13px", flexShrink: 0, marginTop: "2px" }}>❯</span>
      <div style={{ flex: 1 }}>
        <span style={{ color: "#e6edf3", fontSize: "13.5px", lineHeight: 1.6, fontWeight: 500, letterSpacing: "0.2px" }}>
          {entry.content}
        </span>
        <div style={{ color: "#30363d", fontSize: "9.5px", marginTop: "4px", letterSpacing: "0.5px" }}>{formatTime(entry.timestamp)}</div>
      </div>
    </div>
  );
}

function AssistantEntry({ entry }: { entry: LogEntry }): React.JSX.Element {
  const lines = entry.content.split("\n");
  return (
    <div className="fade-in" style={{
      display: "flex", gap: "12px", padding: "12px 32px 16px", borderTop: "1px solid #161b22",
      borderLeft: "3px solid #00d4aa", marginLeft: "0", background: "linear-gradient(90deg, rgba(0,212,170,0.03) 0%, transparent 100%)",
    }}>
      <span style={{ color: "#00d4aa40", fontSize: "14px", flexShrink: 0, marginTop: "2px" }}>◈</span>
      <div style={{ flex: 1 }}>
        {lines.map((line: string, i: number) => {
          const isSuccess = line.startsWith("✅");
          const isError   = line.startsWith("❌");
          const isWarn    = line.startsWith("⚠");
          const isHeader  = line.startsWith("#") || (line.endsWith(":") && line.length < 40);
          return (
            <p key={i} style={{
              fontSize: "13px", lineHeight: 1.7, margin: "0 0 4px",
              color: isSuccess ? "#3fb950" : isError ? "#f85149" : isWarn ? "#e3b341" : isHeader ? "#e6edf3" : "#adbac7",
              fontWeight: isHeader ? 600 : 400,
            }}>
              {line || "\u00a0"}
            </p>
          );
        })}
        <div style={{ color: "#30363d", fontSize: "9.5px", marginTop: "8px", letterSpacing: "0.5px" }}>{formatTime(entry.timestamp)}</div>
      </div>
    </div>
  );
}

function SystemEntry({ entry }: { entry: LogEntry }): React.JSX.Element {
  return (
    <div className="fade-in" style={{ padding: "8px 32px", borderTop: "1px solid #161b22" }}>
      <span style={{ color: "#484f58", fontSize: "11px", fontStyle: "italic" }}>· {entry.content}</span>
    </div>
  );
}

function ErrorEntry({ entry }: { entry: LogEntry }): React.JSX.Element {
  return (
    <div className="fade-in" style={{
      display: "flex", gap: "12px", padding: "12px 32px", borderTop: "1px solid #161b22",
      borderLeft: "3px solid #f85149", background: "linear-gradient(90deg, rgba(248,81,73,0.05) 0%, transparent 100%)",
    }}>
      <span style={{ color: "#f85149", fontSize: "13px", flexShrink: 0, marginTop: "2px" }}>✗</span>
      <span style={{ color: "#f85149", fontSize: "13px", lineHeight: 1.6 }}>{entry.content}</span>
    </div>
  );
}

export default function OutputLog({ entries, companyId, phase }: Props): React.JSX.Element {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect((): void => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [entries]);

  if (entries.length === 0) return <EmptyState companyId={companyId} />;

  return (
    <div style={{ height: "100%", overflowY: "auto", overflowX: "hidden", scrollbarWidth: "thin", scrollbarColor: "#30363d #080a0e" }}>
      <style>{`
        @keyframes slideFade {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .fade-in { animation: slideFade 0.25s ease-out forwards; }
      `}</style>
      <div style={{ paddingTop: "8px", paddingBottom: "16px" }}>
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
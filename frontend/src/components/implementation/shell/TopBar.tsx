'use client';
// PATH: src/components/implementation/shell/TopBar.tsx

import { useParams } from 'next/navigation';

export function TopBar() {
  const params = useParams<{ companySlug: string; userSlug: string }>();

  const companySlug = params.companySlug ?? '';
  const userSlug    = params.userSlug ?? '';

  return (
    <div
      style={{
        height: "56px", // matching h-14
        borderBottom: "1px solid var(--border-subtle)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        paddingInline: "24px",
        flexShrink: 0,
        background: "var(--bg-shell)",
        fontFamily: "var(--font-mono), 'IBM Plex Mono', monospace"
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <span style={{ color: "#f59e0b", fontSize: "11px", fontWeight: 700, letterSpacing: "2px" }}>
          IMPLEMENTATION
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <span style={{ color: "#71717a", fontSize: "11px", letterSpacing: "0.5px", textTransform: 'capitalize' }}>
          {companySlug.replace(/-/g, ' ')}
        </span>
        <span style={{ color: "var(--border-strong)", fontSize: "10px" }}>│</span>
        <span style={{ color: "#52525b", fontSize: "11px", textTransform: 'capitalize' }}>
          {userSlug.replace(/-/g, ' ')}
        </span>
      </div>
    </div>
  );
}
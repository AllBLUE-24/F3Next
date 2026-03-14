/**
 * frontend/src/app/[companySlug]/[userSlug]/(OS)/layout.tsx
 */

import React from "react";
import type { ReactNode } from "react";
import { IBM_Plex_Mono } from "next/font/google";

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-mono",
  display: "swap",
});

interface Props {
  children: ReactNode;
  // 1. Update params to be a Promise
  params: Promise<{ companySlug: string; userSlug: string }>; 
}

// 2. Make the layout async
export default async function OSLayout({ children, params }: Props) {
  // 3. Await the params before using them
  const { companySlug, userSlug } = await params;

  return (
    <div
      className={`${mono.variable} os-root`}
      style={{
        fontFamily: "var(--font-mono), 'IBM Plex Mono', monospace",
        background: "#080a0e",
        color: "#c9d1d9",
        height: "100dvh",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          height: "36px",
          borderBottom: "1px solid #161b22",
          display: "flex",
          alignItems: "center",
          paddingInline: "20px",
          gap: "10px",
          flexShrink: 0,
          background: "#0d1117",
        }}
      >
        <span style={{ color: "#f0a500", fontSize: "11px", fontWeight: 600, letterSpacing: "2px" }}>
          ERP-OS
        </span>
        <span style={{ color: "#30363d", fontSize: "11px" }}>│</span>
        <span style={{ color: "#58a6ff", fontSize: "11px", letterSpacing: "0.5px" }}>
          {companySlug} {/* Updated */}
        </span>
        <span style={{ color: "#30363d", fontSize: "11px" }}>│</span>
        <span style={{ color: "#6e7681", fontSize: "11px" }}>
          {userSlug} {/* Updated */}
        </span>
        <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "6px" }}>
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              background: "#00d4aa",
              boxShadow: "0 0 6px #00d4aa",
              animation: "pulse 2s ease-in-out infinite",
            }}
          />
          <span style={{ color: "#6e7681", fontSize: "10px", letterSpacing: "1px" }}>LIVE</span>
        </span>
      </div>

      <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {children}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}
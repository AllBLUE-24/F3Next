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
        background: "var(--bg-void)",
        color: "#c9d1d9",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
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
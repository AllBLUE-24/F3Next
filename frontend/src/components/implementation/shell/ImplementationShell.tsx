'use client';

// src/components/implementation/shell/ImplementationShell.tsx

import { StepRail } from './StepRail';
import { IBM_Plex_Mono } from "next/font/google";
import { SupervisorPanel } from "@/components/implementation/supervisor/SupervisorPanel";
import { SupervisorAttentionBanner } from "@/components/implementation/supervisor/SupervisorAttentionBanner";

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-mono",
  display: "swap",
});

interface Props {
  children: React.ReactNode;
}

export function ImplementationShell({ children }: Props) {
  return (
    <div className={`flex flex-col h-full min-h-full w-full ${mono.variable}`} style={{ fontFamily: 'var(--font-inter), sans-serif' }}>
      
      {/* Full-width attention banner — appears above everything when user input needed */}
      <SupervisorAttentionBanner />

      <div className="flex flex-1 overflow-hidden">
        {/* Secondary Sidebar (Implementation Steps) */}
        <StepRail />
        
        {/* Main implementation content */}
        <main className="flex-1 min-w-0 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-6 py-8 lg:py-12">
            {children}
          </div>
        </main>

        {/* Right-side Supervisor panel */}
        <aside className="hidden xl:flex w-[360px] border-l border-[var(--border-subtle)] bg-[var(--bg-shell)]">
          <SupervisorPanel />
        </aside>
      </div>
      
    </div>
  );
}
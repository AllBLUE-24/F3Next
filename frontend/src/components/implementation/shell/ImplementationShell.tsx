'use client';

// src/components/implementation/shell/ImplementationShell.tsx

import { TopBar } from './TopBar';
import { StepRail } from './StepRail';

interface Props {
  children: React.ReactNode;
}

export function ImplementationShell({ children }: Props) {
  return (
    <div className="min-h-screen bg-[#09090B] flex flex-col" style={{ fontFamily: 'var(--font-syne), sans-serif' }}>
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <StepRail />
        {/* Main content */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-6 py-10 lg:py-16">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
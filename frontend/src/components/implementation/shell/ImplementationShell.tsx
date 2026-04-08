'use client';

// src/components/implementation/shell/ImplementationShell.tsx
// Full-screen shell — h-screen anchored, no overflow leaks.

import { TopBar } from './TopBar';

interface Props {
  children: React.ReactNode;
}

export function ImplementationShell({ children }: Props) {
  return (
    <div className="h-screen flex flex-col overflow-hidden bg-[#0E1117]">
      <TopBar />
      <main className="flex-1 min-h-0 overflow-hidden">
        {children}
      </main>
    </div>
  );
}
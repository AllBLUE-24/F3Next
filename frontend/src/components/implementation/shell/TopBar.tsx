'use client';
// PATH: src/components/implementation/shell/TopBar.tsx
// Thin 40px header — Electric Blue accent, no amber.

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Cpu } from 'lucide-react';
import { DeploymentPill } from './DeploymentPill';

export function TopBar() {
  const params = useParams<{ companySlug: string; userSlug: string }>();
  const companySlug = params.companySlug ?? '';
  const userSlug    = params.userSlug ?? '';

  return (
    <header
      className="flex-shrink-0 flex items-center justify-between px-4 select-none"
      style={{
        height: 40,
        borderBottom: '1px solid #21262D',
        background: '#161B22',
      }}
    >
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2 group">
        <div
          className="w-6 h-6 rounded flex items-center justify-center transition-colors"
          style={{ background: '#2F81F7' }}
        >
          <Cpu className="w-3 h-3 text-white" />
        </div>
        <span className="font-bold text-sm tracking-tight" style={{ color: '#E6EDF3' }}>
          F3<span style={{ color: '#2F81F7' }}>Next</span>
        </span>
      </Link>

      {/* Center: deployment */}
      <DeploymentPill />

      {/* Right: user */}
      <div className="flex items-center gap-2.5">
        <div className="text-right hidden sm:block">
          <p className="text-xs font-medium leading-none capitalize" style={{ color: '#E6EDF3' }}>
            {companySlug.replace(/-/g, ' ')}
          </p>
          <p className="text-[10px] mt-0.5 capitalize" style={{ color: '#484F58' }}>
            {userSlug.replace(/-/g, ' ')}
          </p>
        </div>
        <div
          className="w-6 h-6 rounded-full flex items-center justify-center"
          style={{ background: 'rgba(47,129,247,0.15)', border: '1px solid rgba(47,129,247,0.3)' }}
        >
          <span className="text-[10px] font-bold uppercase" style={{ color: '#2F81F7' }}>
            {userSlug.charAt(0)}
          </span>
        </div>
      </div>
    </header>
  );
}
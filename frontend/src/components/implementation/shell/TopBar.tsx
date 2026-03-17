'use client';
// PATH: src/components/implementation/shell/TopBar.tsx
// ✅ No context. Reads slug from URL via useParams() — safe in static layout.

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { Cpu } from 'lucide-react';
import { DeploymentPill } from './DeploymentPill';

export function TopBar() {
  const params = useParams<{ companySlug: string; userSlug: string }>();

  const companySlug = params.companySlug ?? '';
  const userSlug    = params.userSlug ?? '';

  return (
    <header className="h-14 flex-shrink-0 flex items-center justify-between px-6 border-b border-white/[0.06] bg-[#09090B]/80 backdrop-blur-md sticky top-0 z-40">
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2 group">
        <div className="w-7 h-7 bg-amber-500 rounded-md flex items-center justify-center group-hover:bg-amber-400 transition-colors">
          <Cpu className="w-3.5 h-3.5 text-black" />
        </div>
        <span className="font-black text-white text-base tracking-tight">
          F3<span className="text-amber-500">Next</span>
        </span>
      </Link>

      {/* Center: deployment status — also uses useParams internally */}
      <DeploymentPill />

      {/* Right: company + user — derived from URL, no context needed */}
      <div className="flex items-center gap-3">
        <div className="text-right hidden sm:block">
          <p className="text-xs font-semibold text-white leading-none capitalize">
            {companySlug.replace(/-/g, ' ')}
          </p>
          <p className="text-[10px] text-gray-600 mt-0.5 capitalize">
            {userSlug.replace(/-/g, ' ')}
          </p>
        </div>
        <div className="w-7 h-7 rounded-full bg-amber-500/20 border border-amber-500/30 flex items-center justify-center">
          <span className="text-[10px] font-bold text-amber-400 uppercase">
            {userSlug.charAt(0)}
          </span>
        </div>
      </div>
    </header>
  );
}
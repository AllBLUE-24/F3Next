'use client';

import React from 'react';

export default function HeroBackground() {
  return (
    <div className="absolute inset-0 -z-10 h-full w-full bg-[var(--bg-void)] overflow-hidden">

      {/* Fine dotted texture — depth without noise */}
      <div className="absolute inset-0 dot-grid opacity-[0.5]" />

      {/* Primary warm glow — centered behind hero text, slowly drifting */}
      <div className="absolute left-1/2 top-[32%] -translate-x-1/2 -translate-y-1/2 h-[520px] w-[820px] bg-amber-500/[0.05] blur-[180px] rounded-full animate-drift" />

      {/* Secondary cool glow — quiet intelligence undertone */}
      <div className="absolute left-[28%] top-[62%] -translate-x-1/2 -translate-y-1/2 h-[320px] w-[520px] bg-indigo-500/[0.035] blur-[140px] rounded-full" />

      {/* Radial vignette — darkens edges cleanly */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_72%_52%_at_50%_38%,transparent_0%,rgba(9,9,11,0.9)_100%)]" />

      {/* Bottom fade to next section */}
      <div className="absolute bottom-0 left-0 w-full h-56 bg-gradient-to-t from-[var(--bg-void)] to-transparent" />
    </div>
  );
}
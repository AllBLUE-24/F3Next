'use client';

import React from 'react';

export default function HeroBackground() {
  return (
    <div className="absolute inset-0 -z-10 h-full w-full bg-[#09090B] overflow-hidden">

      {/* Primary warm glow — centered behind hero text */}
      <div className="absolute left-1/2 top-[35%] -translate-x-1/2 -translate-y-1/2 h-[500px] w-[800px] bg-amber-500/[0.06] blur-[160px] rounded-full" />

      {/* Secondary cool glow — adds depth */}
      <div className="absolute left-[30%] top-[60%] -translate-x-1/2 -translate-y-1/2 h-[300px] w-[500px] bg-indigo-500/[0.04] blur-[120px] rounded-full" />

      {/* Radial vignette — darkens edges cleanly */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_50%_40%,transparent_0%,rgba(9,9,11,0.85)_100%)]" />

      {/* Bottom fade to next section */}
      <div className="absolute bottom-0 left-0 w-full h-48 bg-gradient-to-t from-[#09090B] to-transparent" />
    </div>
  );
}
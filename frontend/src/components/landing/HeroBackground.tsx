'use client';

import React from 'react';

export default function HeroBackground() {
  return (
    <div className="absolute inset-0 -z-10 h-full w-full bg-[#09090B] overflow-hidden">

      {/* Fine technical grid */}
      <div className="absolute h-full w-full bg-[linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:24px_24px]"></div>

      {/* Major grid overlay */}
      <div className="absolute h-full w-full bg-[linear-gradient(to_right,rgba(255,255,255,0.06)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.06)_1px,transparent_1px)] bg-[size:120px_120px]"></div>

      {/* Amber focal glow — hero center */}
      <div className="absolute left-1/2 top-[40%] -translate-x-1/2 -translate-y-1/2 h-[600px] w-[900px] bg-amber-500/8 blur-[140px] rounded-full"></div>

      {/* Blue secondary glow — depth */}
      <div className="absolute left-1/2 top-[50%] -translate-x-1/2 -translate-y-1/2 h-[400px] w-[600px] bg-blue-600/10 blur-[100px] rounded-full"></div>

      {/* Top-right orb */}
      <div className="absolute top-0 right-0 w-[480px] h-[480px] bg-amber-600/[0.07] rounded-full filter blur-3xl animate-blob"></div>

      {/* Bottom-left orb */}
      <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-blue-800/[0.07] rounded-full filter blur-3xl animate-blob animation-delay-2000"></div>

      {/* Horizontal scan line */}
      <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-amber-500/20 to-transparent"></div>

      {/* Radial vignette — darkens corners */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_40%,transparent_0%,rgba(9,9,11,0.8)_100%)]"></div>

      {/* Bottom fade to next section */}
      <div className="absolute bottom-0 left-0 w-full h-40 bg-gradient-to-t from-[#09090B] to-transparent"></div>
    </div>
  );
}
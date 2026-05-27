'use client';

import React from 'react';

export default function AuthBrandPanel() {
  return (
    <div className="relative hidden md:flex md:w-1/2 flex-col justify-between p-14 lg:p-16 overflow-hidden">

      {/* Gradient mesh background */}
      <div className="absolute inset-0 bg-[#0c0c10]" />
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-amber-500/[0.04] rounded-full blur-[160px] pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-amber-600/[0.03] rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-zinc-800/[0.15] rounded-full blur-[200px] pointer-events-none" />

      {/* Subtle border on left edge */}
      <div className="absolute inset-y-0 right-0 w-px bg-gradient-to-b from-transparent via-white/[0.06] to-transparent" />

      {/* Logo — top */}
      <div className="relative z-10">
        <span
          className="text-lg font-semibold text-white/90 tracking-tight"
          style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
        >
          F3<span className="text-amber-500">Next</span>
        </span>
      </div>

      {/* Center — single compelling statement */}
      <div className="relative z-10 my-auto max-w-sm space-y-8">
        {/* Stat */}
        <div className="space-y-2">
          <p
            className="text-5xl lg:text-6xl font-bold text-white/90 tracking-[-0.04em] leading-none"
            style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
          >
            10 min
          </p>
          <p className="text-[15px] text-zinc-500 leading-relaxed">
            Average time to deploy a fully-mapped operational system from messy spreadsheets.
          </p>
        </div>

        {/* Divider */}
        <div className="w-10 h-px bg-white/[0.08]" />

        {/* Quote */}
        <blockquote className="space-y-3">
          <p className="text-[14px] text-zinc-400 leading-relaxed font-normal italic">
            &ldquo;We went from Excel chaos to real-time stock visibility in one afternoon. No training, no consultants.&rdquo;
          </p>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-500/20 to-amber-600/10 border border-amber-500/20 flex items-center justify-center">
              <span className="text-[11px] font-semibold text-amber-500">GS</span>
            </div>
            <div>
              <p className="text-[12px] font-medium text-zinc-400">Operations Director</p>
              <p className="text-[11px] text-zinc-600">Green Surface Coatings</p>
            </div>
          </div>
        </blockquote>
      </div>

      {/* Bottom — subtle info */}
      <div className="relative z-10 text-[11px] text-zinc-700 font-medium">
        Built for Indian manufacturers
      </div>
    </div>
  );
}

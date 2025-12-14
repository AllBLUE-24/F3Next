'use client';

import React from 'react';

export default function HeroBackground() {
  return (
    <div className="absolute inset-0 -z-10 h-full w-full bg-white overflow-hidden">
      {/* 1. Technical Grid System */}
      {/* Minor Grid (Small squares) */}
      <div className="absolute h-full w-full bg-[linear-gradient(to_right,#cbd5e1_1px,transparent_1px),linear-gradient(to_bottom,#cbd5e1_1px,transparent_1px)] bg-[size:20px_20px] opacity-[0.25]"></div>
      
      {/* Major Grid (Large squares for depth) */}
      <div className="absolute h-full w-full bg-[linear-gradient(to_right,#94a3b8_1px,transparent_1px),linear-gradient(to_bottom,#94a3b8_1px,transparent_1px)] bg-[size:100px_100px] opacity-[0.15]"></div>
      
      {/* 2. Central Focus Glow (Behind the H1) */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-[500px] w-[800px] bg-indigo-50/80 blur-[120px] rounded-full mix-blend-multiply"></div>
      
      {/* 3. Animated Gradient Orbs (More visible now) */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-100/60 rounded-full mix-blend-multiply filter blur-3xl opacity-40 animate-blob"></div>
      <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-purple-100/60 rounded-full mix-blend-multiply filter blur-3xl opacity-40 animate-blob animation-delay-2000"></div>
      
      {/* 4. Bottom Fade (Seamless transition) */}
      <div className="absolute bottom-0 left-0 w-full h-32 bg-gradient-to-t from-white via-white/80 to-transparent"></div>
    </div>
  );
}
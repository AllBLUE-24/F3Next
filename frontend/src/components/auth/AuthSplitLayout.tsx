'use client';

import React from 'react';
import AuthBrandPanel from './AuthBrandPanel';

interface AuthSplitLayoutProps {
  children: React.ReactNode;
}

export default function AuthSplitLayout({ children }: AuthSplitLayoutProps) {
  return (
    <div className="flex min-h-screen w-full bg-[#09090B] text-white">
      {/* Left Panel: Minimal branding (desktop only) */}
      <AuthBrandPanel />

      {/* Right Panel: Form (full width on mobile, half on desktop) */}
      <div className="relative flex w-full md:w-1/2 flex-col justify-center items-center px-6 py-12 sm:px-12 lg:px-20 overflow-y-auto min-h-screen">

        {/* Very subtle ambient glow */}
        <div className="absolute top-1/4 right-1/3 w-72 h-72 rounded-full bg-amber-500/[0.02] blur-[120px] pointer-events-none" />

        {/* Form container */}
        <div className="relative z-10 w-full max-w-[380px] space-y-6">
          {children}
        </div>
      </div>
    </div>
  );
}

'use client';

import React from 'react';
import Link from 'next/link';
import { Check, Flame } from 'lucide-react';

export default function Pricing() {
  return (
    <section id="pricing" className="py-28 lg:py-32 bg-[#09090B]">
      <div className="max-w-5xl mx-auto px-6 lg:px-8">

        {/* Section Header */}
        <div className="text-center mb-16 lg:mb-20">
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-amber-500/80 mb-4">
            Pricing
          </p>
          <h2
            className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white tracking-[-0.03em] leading-tight"
            style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
          >
            Simple, honest <span className="text-amber-500">pricing</span>
          </h2>
          <p className="mt-5 text-base text-zinc-500 max-w-lg mx-auto leading-relaxed">
            No setup fees, no long-term lock-ins. Pick a tier that scales with your factory.
          </p>
        </div>

        {/* Pricing Grid */}
        <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">

          {/* STARTER */}
          <div className="relative bg-white/[0.01] border border-white/[0.05] rounded-2xl p-8 flex flex-col justify-between">
            <div className="space-y-6">
              <div>
                <span className="text-[12px] font-medium text-zinc-500">Starter</span>
                <div className="flex items-baseline mt-3 gap-1.5">
                  <span className="text-4xl font-bold text-white tracking-tight" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>₹999</span>
                  <span className="text-[13px] text-zinc-600 font-medium">/ month + GST</span>
                </div>
                <p className="text-[13px] text-zinc-500 mt-3 leading-relaxed">
                  For local workshops needing stock-level tracking and daily status updates.
                </p>
              </div>

              <div className="h-px bg-white/[0.04]" />

              <ul className="space-y-3 text-[13px] text-zinc-400">
                {[
                  'Up to 2 operational users',
                  'Core stock tracking',
                  'Spreadsheet data ingestion',
                  'Daily email briefings',
                  'Standard support (24hr)'
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2.5">
                    <Check className="w-4 h-4 text-zinc-600 shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-8">
              <Link
                href="/signup"
                className="block text-center bg-white/[0.04] text-zinc-300 border border-white/[0.06] hover:bg-white/[0.08] hover:text-white px-5 py-3 rounded-xl text-[13px] font-medium transition-all duration-200 cursor-pointer"
              >
                Start free trial
              </Link>
            </div>
          </div>

          {/* GROWTH */}
          <div className="relative bg-white/[0.01] border border-amber-500/15 rounded-2xl p-8 flex flex-col justify-between">
            {/* Accent line */}
            <div className="absolute top-0 inset-x-8 h-px bg-gradient-to-r from-transparent via-amber-500/50 to-transparent" />
            
            <div className="space-y-6">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-[12px] font-medium text-amber-500/80">Growth</span>
                  <div className="flex items-baseline mt-3 gap-1.5">
                    <span className="text-4xl font-bold text-white tracking-tight" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>₹2,499</span>
                    <span className="text-[13px] text-zinc-600 font-medium">/ month + GST</span>
                  </div>
                  <p className="text-[13px] text-zinc-500 mt-3 leading-relaxed">
                    For scaling factories needing multi-warehouse tracking and proactive automation.
                  </p>
                </div>
                <span className="inline-flex items-center gap-1 bg-amber-500/[0.08] border border-amber-500/15 px-2.5 py-1 rounded-full text-[10px] font-medium text-amber-500/90 shrink-0 mt-1">
                  <Flame className="w-3 h-3 shrink-0" />
                  Popular
                </span>
              </div>

              <div className="h-px bg-white/[0.04]" />

              <ul className="space-y-3 text-[13px] text-zinc-400">
                {[
                  'Unlimited operational users',
                  'Multi-warehouse & batch tracking',
                  'CSV, XLSX, PDF data ingestion',
                  'Proactive alerts & low stock warnings',
                  'Auto-drafted purchase orders',
                  'Direct founder support'
                ].map((item) => (
                  <li key={item} className="flex items-start gap-2.5">
                    <Check className="w-4 h-4 text-amber-500/70 shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-8">
              <Link
                href="/signup"
                className="block text-center bg-amber-500 text-black px-5 py-3 rounded-xl text-[13px] font-semibold transition-all duration-200 lift-hover shadow-lg shadow-amber-500/15 cursor-pointer"
              >
                Start free trial
              </Link>
            </div>
          </div>
        </div>

        {/* Guarantee */}
        <div className="mt-12 text-center">
          <p className="text-[13px] text-zinc-600 max-w-md mx-auto leading-relaxed">
            14-day free trial on all plans. If we can't configure your workspace in 10 minutes, you pay nothing.
          </p>
        </div>

      </div>
    </section>
  );
}

'use client';

import React from 'react';
import { X, Check } from 'lucide-react';

const rows = [
  {
    label: 'Setup Time',
    old: '3–6 Months',
    new: '< 48 Hours',
    oldBad: true,
  },
  {
    label: 'Upfront Cost',
    old: '₹5,00,000+',
    new: '₹0 (Free)',
    oldBad: true,
  },
  {
    label: 'Consultants',
    old: 'Mandatory',
    new: 'Not needed',
    oldBad: true,
  },
  {
    label: 'Data Migration',
    old: 'Manual / Costly',
    new: 'AI-Automated',
    oldBad: true,
  },
  {
    label: 'Employee Training',
    old: 'Weeks of sessions',
    new: 'Type a prompt',
    oldBad: true,
  },
  {
    label: 'ERP Operations',
    old: 'Trained staff only',
    new: 'AI-driven, anyone',
    oldBad: true,
  },
  {
    label: 'Success Rate',
    old: '< 30%',
    new: '95%+',
    oldBad: true,
  },
  {
    label: 'Changes & Adaption',
    old: 'Expensive & slow',
    new: 'AI-included',
    oldBad: true,
  },
];

export default function Comparison() {
  return (
    <section className="border-t border-white/[0.06] py-28 bg-[#09090B]" id="comparison">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">

        <div className="text-center mb-16">
          <span className="inline-block text-xs font-bold uppercase tracking-[0.2em] text-amber-500 mb-4">The Difference</span>
          <h2 className="text-3xl font-bold text-white tracking-tight sm:text-5xl">
            Why manufacturers are switching.
          </h2>
          <p className="mt-4 text-gray-500 text-lg">The old way vs. the autonomous way.</p>
        </div>

        {/* Table */}
        <div className="max-w-4xl mx-auto">
          {/* Header Row */}
          <div className="grid grid-cols-3 gap-4 mb-3 px-4">
            <div className="text-xs uppercase tracking-widest text-gray-600 font-bold"></div>
            <div className="text-center text-xs uppercase tracking-widest text-gray-600 font-bold">Traditional ERP</div>
            <div className="text-center">
              <span className="inline-block text-xs uppercase tracking-widest text-amber-500 font-bold bg-amber-500/10 border border-amber-500/20 px-3 py-1 rounded-full">
                F3Next AI
              </span>
            </div>
          </div>

          {/* Data Rows */}
          <div className="rounded-2xl border border-white/[0.07] overflow-hidden">
            {rows.map((row, i) => (
              <div
                key={i}
                className={`grid grid-cols-3 gap-4 items-center px-6 py-5 ${
                  i !== rows.length - 1 ? 'border-b border-white/[0.05]' : ''
                } ${i % 2 === 0 ? 'bg-white/[0.01]' : 'bg-transparent'} hover:bg-white/[0.03] transition-colors`}
              >
                {/* Label */}
                <span className="text-sm font-medium text-gray-400">{row.label}</span>

                {/* Old */}
                <div className="flex items-center justify-center gap-2">
                  <X className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
                  <span className="text-sm text-red-400/80 font-medium">{row.old}</span>
                </div>

                {/* New */}
                <div className="flex items-center justify-center gap-2">
                  <Check className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
                  <span className="text-sm text-green-400 font-bold">{row.new}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Bottom callout */}
          <div className="mt-8 grid md:grid-cols-3 gap-4">
            {[
              { value: '48hrs', label: 'To go live vs 6 months' },
              { value: '₹0', label: 'Upfront vs ₹5,00,000+' },
              { value: '95%+', label: 'Success rate vs industry <30%' },
            ].map((stat, i) => (
              <div
                key={i}
                className="text-center bg-white/[0.02] border border-white/[0.06] rounded-xl py-6 px-4"
              >
                <div className="text-3xl font-black text-amber-500 mb-1">{stat.value}</div>
                <div className="text-xs text-gray-500">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
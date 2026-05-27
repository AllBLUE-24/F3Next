'use client';

import React from 'react';
import { ClipboardList, Upload, Play, Shield } from 'lucide-react';

export default function Vision() {
  const steps = [
    {
      icon: ClipboardList,
      num: '01',
      title: 'Audit your factory',
      desc: 'Answer a few questions about your operations, bottlenecks, and category. We map your exact operational profile.',
      tag: '5 minutes',
    },
    {
      icon: Upload,
      num: '02',
      title: 'Upload your data',
      desc: 'Hand us old Tally files, messy spreadsheets, or raw PDFs. Our engine clean-maps columns and deploys your sandboxed ledger.',
      tag: 'Autonomous',
    },
    {
      icon: Play,
      num: '03',
      title: 'Run on autopilot',
      desc: 'Get daily alerts for low stock, project milestones, and pending receipts. Respond or create entries using plain-English prompts.',
      tag: 'No training',
    }
  ];

  return (
    <section id="how-it-works" className="py-28 lg:py-32 bg-[#09090B]">
      <div className="max-w-6xl mx-auto px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="text-center mb-16 lg:mb-20">
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-amber-500/80 mb-4">
            How it works
          </p>
          <h2
            className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white tracking-[-0.03em] leading-tight"
            style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
          >
            Three steps to <span className="text-amber-500">autopilot</span>
          </h2>
          <p className="mt-5 text-base text-zinc-500 max-w-lg mx-auto leading-relaxed">
            No expensive consultants, no lengthy implementation contracts. Go from Excel chaos to live operations in minutes.
          </p>
        </div>

        {/* Step Cards */}
        <div className="grid md:grid-cols-3 gap-6">
          {steps.map((step) => (
            <div
              key={step.num}
              className="group relative bg-white/[0.01] border border-white/[0.05] hover:border-white/[0.1] rounded-2xl p-8 flex flex-col transition-all duration-300"
            >
              {/* Step number */}
              <div className="text-[11px] font-medium text-zinc-600 mb-6">
                {step.num}
              </div>

              {/* Icon */}
              <div className="w-10 h-10 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mb-5 group-hover:border-amber-500/20 transition-colors duration-300">
                <step.icon className="w-4.5 h-4.5 text-zinc-500 group-hover:text-amber-500 transition-colors duration-300" />
              </div>

              {/* Content */}
              <h3 className="text-[16px] font-semibold text-white mb-3 tracking-tight">
                {step.title}
              </h3>
              <p className="text-[13px] text-zinc-500 leading-relaxed flex-1">
                {step.desc}
              </p>

              {/* Tag */}
              <div className="mt-6 pt-5 border-t border-white/[0.04]">
                <span className="text-[11px] font-medium text-zinc-600">
                  {step.tag}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Trust Banner */}
        <div className="mt-10 border border-white/[0.05] rounded-xl p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Shield className="w-4 h-4 text-emerald-400/70 shrink-0" />
            <div>
              <span className="text-[13px] font-medium text-zinc-300">Human-in-the-loop sandbox</span>
              <p className="text-[12px] text-zinc-600 mt-0.5">No changes go live without your explicit confirmation.</p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500/60 animate-pulse shrink-0" />
            <span className="text-[11px] font-medium text-emerald-400/60">Safety active</span>
          </div>
        </div>
        
      </div>
    </section>
  );
}
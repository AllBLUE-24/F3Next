'use client';

import React, { useState } from 'react';
import { CheckCircle, FileSpreadsheet, MessageSquare, FileText, Zap } from 'lucide-react';

export default function ChaosToClarity() {
  const [activeTab, setActiveTab] = useState<'chaos' | 'clarity'>('chaos');

  return (
    <section id="chaos-to-clarity" className="py-28 lg:py-32 bg-[#09090B]">
      <div className="max-w-6xl mx-auto px-6 lg:px-8">

        {/* Section Header */}
        <div className="text-center mb-16 lg:mb-20">
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-amber-500/80 mb-4">
            The Problem
          </p>
          <h2
            className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white tracking-[-0.03em] leading-tight"
            style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
          >
            From chaos to <span className="text-amber-500">clarity</span>
          </h2>
          <p className="mt-5 text-base text-zinc-500 max-w-lg mx-auto leading-relaxed">
            See how F3Next transforms your factory from manual tracking to autonomous operations.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex justify-center mb-14">
          <div className="inline-flex rounded-lg bg-white/[0.03] border border-white/[0.06] p-1 gap-1">
            <button
              onClick={() => setActiveTab('chaos')}
              className={`px-5 py-2 rounded-md text-[13px] font-medium transition-all duration-200 cursor-pointer ${
                activeTab === 'chaos'
                  ? 'bg-white/[0.08] text-white'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              Before
            </button>
            <button
              onClick={() => setActiveTab('clarity')}
              className={`px-5 py-2 rounded-md text-[13px] font-medium transition-all duration-200 cursor-pointer ${
                activeTab === 'clarity'
                  ? 'bg-amber-500 text-black'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              After
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="grid lg:grid-cols-2 gap-10 lg:gap-16 items-start">

          {activeTab === 'chaos' ? (
            <>
              {/* Left: Pain points */}
              <div className="space-y-5 fade-in-up">
                <h3 className="text-xl font-semibold text-white tracking-tight mb-6">
                  The daily friction of unstructured operations
                </h3>
                {[
                  {
                    icon: FileSpreadsheet,
                    title: 'Outdated stock ledgers',
                    desc: 'Manual Excel entries lag behind physical inventory. Errors compound daily.'
                  },
                  {
                    icon: MessageSquare,
                    title: 'WhatsApp coordination chaos',
                    desc: 'Batch numbers, approvals, and production notes buried in group chats.'
                  },
                  {
                    icon: FileText,
                    title: 'Month-end GST scrambles',
                    desc: 'Tax accountants request invoices. You spend nights hunting for physical slips.'
                  }
                ].map((item, idx) => (
                  <div key={idx} className="flex gap-4 p-4 rounded-xl border border-white/[0.04] bg-white/[0.01] hover:border-white/[0.08] transition-colors duration-200">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-red-500/[0.08]">
                      <item.icon className="h-4 w-4 text-red-400/80" />
                    </div>
                    <div>
                      <h4 className="text-[14px] font-medium text-zinc-200">{item.title}</h4>
                      <p className="text-[13px] text-zinc-500 mt-1 leading-relaxed">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Right: Mockup */}
              <div className="relative bg-zinc-950/50 border border-white/[0.04] rounded-2xl p-6 space-y-4 fade-in-up">
                <div className="text-[10px] font-medium text-red-400/70 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-500/60 animate-pulse shrink-0" />
                  Typical factory operations
                </div>

                <div className="bg-white/[0.02] border border-white/[0.04] p-4 rounded-xl space-y-2">
                  <div className="text-[10px] font-medium text-zinc-600 font-mono">STOCK_TRACKER_V3_FINAL.xlsx</div>
                  <div className="text-[13px] font-mono text-zinc-500 space-y-1.5">
                    <div>Row 142: Epoxy Primer #402 | Qty: <span className="text-red-400/80">#VALUE!</span></div>
                    <div>Row 143: Hardener PU-90 | Qty: <span className="text-red-400/80">ERR_STOCKOUT</span></div>
                  </div>
                </div>

                <div className="bg-white/[0.02] border border-white/[0.04] p-4 rounded-xl space-y-3">
                  <div className="text-[10px] font-medium text-zinc-600 font-mono">WHATSAPP — Factory Group</div>
                  <div className="space-y-2 text-[13px]">
                    <div className="bg-zinc-900/60 border border-white/[0.04] p-2.5 rounded-lg max-w-[85%]">
                      <div className="text-[10px] font-medium text-amber-500/70">Rajesh</div>
                      <div className="text-zinc-400 mt-0.5">Did anyone record the hardener dispatch?</div>
                    </div>
                    <div className="bg-zinc-800/40 border border-white/[0.04] p-2.5 rounded-lg max-w-[85%] ml-auto">
                      <div className="text-zinc-400">Check with Amit, he took it to warehouse 2.</div>
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <>
              {/* Left: Solutions */}
              <div className="space-y-5 fade-in-up">
                <h3 className="text-xl font-semibold text-white tracking-tight mb-6">
                  An invisible system that runs your operations
                </h3>
                {[
                  {
                    icon: CheckCircle,
                    title: 'Live operational briefings',
                    desc: 'Proactive alerts for cash flows, low stock, and batch dispatches — no login needed.'
                  },
                  {
                    icon: Zap,
                    title: 'Automated purchase orders',
                    desc: 'POs are pre-drafted the moment inventory crosses safety thresholds.'
                  },
                  {
                    icon: CheckCircle,
                    title: 'Tax ledger sync',
                    desc: 'Physical invoices are parsed and mapped directly to compliance ledgers.'
                  }
                ].map((item, idx) => (
                  <div key={idx} className="flex gap-4 p-4 rounded-xl border border-white/[0.04] bg-white/[0.01] hover:border-amber-500/[0.12] transition-colors duration-200">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-500/[0.08]">
                      <item.icon className="h-4 w-4 text-amber-500/80" />
                    </div>
                    <div>
                      <h4 className="text-[14px] font-medium text-zinc-200">{item.title}</h4>
                      <p className="text-[13px] text-zinc-500 mt-1 leading-relaxed">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Right: Dashboard mockup */}
              <div className="relative bg-zinc-950/50 border border-white/[0.04] rounded-2xl p-6 space-y-4 fade-in-up">
                <div className="text-[10px] font-medium text-amber-500/70 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500/60 animate-pulse shrink-0" />
                  F3Next — System Active
                </div>

                <div className="bg-white/[0.02] border border-white/[0.04] p-4 rounded-xl space-y-3">
                  <div className="text-[10px] font-medium text-zinc-600 font-mono">Dashboard</div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-zinc-900/40 border border-white/[0.04] p-3 rounded-lg">
                      <div className="text-[10px] text-zinc-600">Stock Health</div>
                      <div className="text-zinc-200 font-semibold text-[14px] mt-1">100% Tracked</div>
                    </div>
                    <div className="bg-zinc-900/40 border border-white/[0.04] p-3 rounded-lg">
                      <div className="text-[10px] text-zinc-600">Active Warnings</div>
                      <div className="text-amber-500 font-semibold text-[14px] mt-1">0 Gaps</div>
                    </div>
                  </div>
                </div>

                <div className="bg-white/[0.02] border border-white/[0.04] p-4 rounded-xl space-y-3">
                  <div className="text-[10px] font-medium text-zinc-600 font-mono">Auto-drafted Actions</div>
                  <div className="flex items-center justify-between bg-zinc-900/40 border border-white/[0.04] p-3 rounded-lg">
                    <div className="flex items-center gap-2.5">
                      <Zap className="w-3.5 h-3.5 text-amber-500/70 shrink-0" />
                      <span className="text-zinc-300 text-[13px]">Re-order: 50kg Resin from ABC</span>
                    </div>
                    <span className="text-[10px] font-medium text-emerald-400/80 bg-emerald-500/[0.08] px-2 py-0.5 rounded-full">Drafted</span>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

      </div>
    </section>
  );
}

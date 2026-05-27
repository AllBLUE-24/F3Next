'use client';

import React, { useState } from 'react';
import { TrendingUp, Package, FileText, AlertTriangle, CheckCircle, ArrowUpRight, ArrowDownRight } from 'lucide-react';

export default function HeroDashboardPreview() {
  const [view, setView] = useState<'before' | 'after'>('after');

  return (
    <div className="mt-16 lg:mt-20 max-w-5xl mx-auto px-4 fade-in-up">

      {/* Toggle */}
      <div className="flex justify-center mb-6">
        <div className="inline-flex rounded-full bg-white/[0.04] border border-white/[0.06] p-1 gap-0.5">
          <button
            onClick={() => setView('before')}
            className={`px-5 py-1.5 rounded-full text-[12px] font-medium transition-all duration-300 cursor-pointer ${
              view === 'before'
                ? 'bg-white/[0.1] text-white shadow-sm'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            Before F3Next
          </button>
          <button
            onClick={() => setView('after')}
            className={`px-5 py-1.5 rounded-full text-[12px] font-medium transition-all duration-300 cursor-pointer ${
              view === 'after'
                ? 'bg-amber-500 text-black shadow-sm'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            With F3Next
          </button>
        </div>
      </div>

      {/* Dashboard Frame */}
      <div className="relative rounded-2xl border border-white/[0.06] bg-[#0c0c10] overflow-hidden shadow-2xl shadow-black/40">
        {/* Subtle gradient top edge */}
        <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-white/[0.1] to-transparent" />

        {/* Window Chrome */}
        <div className="flex items-center gap-2 px-5 py-3 border-b border-white/[0.04]">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
            <div className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
            <div className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
          </div>
          <div className="flex-1 flex justify-center">
            <div className="flex items-center gap-2 bg-white/[0.03] rounded-md px-4 py-1 text-[10px] text-zinc-600 font-mono">
              {view === 'after' ? 'app.f3next.in/green-surface/dashboard' : 'Excel + WhatsApp'}
            </div>
          </div>
          <div className="w-14" /> {/* Balance spacer */}
        </div>

        {/* Dashboard Content */}
        <div className="p-5 lg:p-6 transition-all duration-500">
          {view === 'after' ? (
            /* ── AFTER: Clean F3Next Dashboard ── */
            <div className="space-y-4">
              {/* Top Stats Row */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                {[
                  { label: 'Monthly Revenue', value: '₹14.8L', change: '+16.7%', up: true, icon: TrendingUp },
                  { label: 'Stock Health', value: '98.2%', change: '+4.1%', up: true, icon: Package },
                  { label: 'Active Orders', value: '24', change: '+3', up: true, icon: FileText },
                  { label: 'Pending Alerts', value: '0', change: 'Clear', up: true, icon: CheckCircle },
                ].map((stat) => (
                  <div key={stat.label} className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-4 space-y-2 hover:border-white/[0.08] transition-colors duration-200">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-zinc-600 font-medium">{stat.label}</span>
                      <stat.icon className="w-3.5 h-3.5 text-zinc-700" />
                    </div>
                    <div className="flex items-end justify-between">
                      <span className="text-xl lg:text-2xl font-semibold text-white tracking-tight" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>
                        {stat.value}
                      </span>
                      <span className={`flex items-center gap-0.5 text-[10px] font-medium ${stat.up ? 'text-emerald-400' : 'text-red-400'}`}>
                        {stat.up ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                        {stat.change}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Bottom Row: Chart area + Recent Activity */}
              <div className="grid lg:grid-cols-5 gap-3">
                {/* Chart Placeholder */}
                <div className="lg:col-span-3 bg-white/[0.02] border border-white/[0.04] rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium text-zinc-400">Revenue Overview</span>
                    <div className="flex items-center gap-1 bg-white/[0.04] rounded-md px-2 py-0.5">
                      <span className="text-[9px] text-amber-500 font-medium">6M</span>
                    </div>
                  </div>
                  {/* Faux chart bars */}
                  <div className="flex items-end gap-2 h-24 px-2">
                    {[35, 42, 38, 56, 48, 65, 72, 60, 78, 85, 70, 92].map((h, i) => (
                      <div key={i} className="flex-1 rounded-sm transition-all duration-500" style={{
                        height: `${h}%`,
                        background: i >= 10 ? 'rgba(245, 158, 11, 0.5)' : i >= 8 ? 'rgba(245, 158, 11, 0.3)' : 'rgba(255, 255, 255, 0.06)',
                      }} />
                    ))}
                  </div>
                  <div className="flex justify-between text-[8px] text-zinc-700 font-mono px-2">
                    <span>Jan</span><span>Mar</span><span>Jun</span><span>Sep</span><span>Dec</span>
                  </div>
                </div>

                {/* Recent Activity */}
                <div className="lg:col-span-2 bg-white/[0.02] border border-white/[0.04] rounded-xl p-4 space-y-3">
                  <span className="text-[11px] font-medium text-zinc-400">Auto-Drafted Actions</span>
                  <div className="space-y-2">
                    {[
                      { text: 'PO drafted: 50kg Resin', status: 'Ready', color: 'text-amber-500 bg-amber-500/[0.08]' },
                      { text: 'Stock alert: Hardener low', status: 'Sent', color: 'text-emerald-400 bg-emerald-500/[0.08]' },
                      { text: 'Invoice #E402 synced', status: 'Done', color: 'text-emerald-400 bg-emerald-500/[0.08]' },
                    ].map((item, i) => (
                      <div key={i} className="flex items-center justify-between py-2 border-b border-white/[0.03] last:border-0">
                        <span className="text-[11px] text-zinc-400">{item.text}</span>
                        <span className={`text-[9px] font-medium px-2 py-0.5 rounded-full ${item.color}`}>{item.status}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* ── BEFORE: Messy Excel/WhatsApp state ── */
            <div className="space-y-4">
              {/* Top Stats Row — broken */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                {[
                  { label: 'Monthly Revenue', value: '???', note: 'Uncalculated', icon: TrendingUp },
                  { label: 'Stock Health', value: '#ERR', note: 'Outdated', icon: Package },
                  { label: 'Active Orders', value: '~15?', note: 'Approximate', icon: FileText },
                  { label: 'Pending Alerts', value: '7+', note: 'Unresolved', icon: AlertTriangle },
                ].map((stat) => (
                  <div key={stat.label} className="bg-red-500/[0.02] border border-red-500/[0.06] rounded-xl p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-zinc-600 font-medium">{stat.label}</span>
                      <stat.icon className="w-3.5 h-3.5 text-red-400/50" />
                    </div>
                    <div className="flex items-end justify-between">
                      <span className="text-xl lg:text-2xl font-semibold text-red-400/70 tracking-tight font-mono">
                        {stat.value}
                      </span>
                      <span className="text-[10px] font-medium text-red-400/50">
                        {stat.note}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Bottom Row: Messy spreadsheet + WhatsApp */}
              <div className="grid lg:grid-cols-5 gap-3">
                <div className="lg:col-span-3 bg-white/[0.01] border border-white/[0.04] rounded-xl p-4 space-y-3">
                  <span className="text-[11px] font-medium text-zinc-600 font-mono">STOCK_TRACKER_V3_FINAL(2).xlsx</span>
                  <div className="space-y-1.5 font-mono text-[11px]">
                    <div className="flex justify-between px-2 py-1.5 bg-white/[0.02] rounded border border-white/[0.03]">
                      <span className="text-zinc-500">Row 142: Epoxy Primer</span>
                      <span className="text-red-400/70">#VALUE!</span>
                    </div>
                    <div className="flex justify-between px-2 py-1.5 bg-white/[0.02] rounded border border-white/[0.03]">
                      <span className="text-zinc-500">Row 143: Hardener PU-90</span>
                      <span className="text-red-400/70">ERR_REF</span>
                    </div>
                    <div className="flex justify-between px-2 py-1.5 bg-white/[0.02] rounded border border-white/[0.03]">
                      <span className="text-zinc-500">Row 144: Catalyst XR</span>
                      <span className="text-zinc-700">??? (missing)</span>
                    </div>
                    <div className="flex justify-between px-2 py-1.5 bg-white/[0.02] rounded border border-white/[0.03]">
                      <span className="text-zinc-500">Row 145: Base Coat 200L</span>
                      <span className="text-red-400/70">#N/A</span>
                    </div>
                  </div>
                </div>

                <div className="lg:col-span-2 bg-white/[0.01] border border-white/[0.04] rounded-xl p-4 space-y-3">
                  <span className="text-[11px] font-medium text-zinc-600 font-mono">WhatsApp — Factory Group</span>
                  <div className="space-y-2">
                    <div className="bg-zinc-900/40 border border-white/[0.03] p-2.5 rounded-lg">
                      <div className="text-[9px] font-medium text-amber-500/60">Rajesh</div>
                      <div className="text-[11px] text-zinc-500 mt-0.5">Did anyone record the dispatch?</div>
                    </div>
                    <div className="bg-zinc-800/30 border border-white/[0.03] p-2.5 rounded-lg">
                      <div className="text-[9px] font-medium text-zinc-600">Amit</div>
                      <div className="text-[11px] text-zinc-500 mt-0.5">Check warehouse 2, I think it&apos;s there</div>
                    </div>
                    <div className="bg-zinc-900/40 border border-white/[0.03] p-2.5 rounded-lg">
                      <div className="text-[9px] font-medium text-red-400/60">Boss</div>
                      <div className="text-[11px] text-zinc-500 mt-0.5">GST filing is tomorrow. Where are the invoices??</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Bottom gradient fade for depth */}
        <div className="absolute bottom-0 inset-x-0 h-12 bg-gradient-to-t from-[#0c0c10] to-transparent pointer-events-none" />
      </div>
    </div>
  );
}

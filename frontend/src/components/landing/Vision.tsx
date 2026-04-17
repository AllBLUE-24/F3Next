'use client';

import React from 'react';
import { MessageSquareDot, Server, FileStack, Terminal, Factory, LayoutGrid, Cpu, TrendingDown } from 'lucide-react';

const steps = [
  {
    icon: MessageSquareDot,
    num: '01',
    title: 'Discover & Recommend',
    subtitle: 'AI Consultant',
    desc: 'Answer 5–7 questions about your company size, industry, and operational goals. Our AI scores your needs and recommends the exact ERP stack — no sales pitch, no upselling.',
    tag: '< 10 minutes',
    tagColor: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
    accent: 'border-blue-500/40',
  },
  {
    icon: Server,
    num: '02',
    title: 'Cloud Deployment',
    subtitle: 'Auto Setup',
    desc: 'We provision your ERPNext instance on a secure, dedicated cloud environment. Backups, SSL, access controls — all configured automatically. You just log in.',
    tag: 'Minutes',
    tagColor: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    accent: 'border-amber-500/40',
  },
  {
    icon: FileStack,
    num: '03',
    title: 'Intelligent Migration',
    subtitle: 'Upload Anything',
    desc: 'Upload old ERP data, Excel sheets, CSVs, or mixed formats. F3Next analyzes and maps your data, previews how it looks in the new system, flags contradictions, and waits for your approval before any changes go live.',
    tag: 'Human-in-the-loop',
    tagColor: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
    accent: 'border-purple-500/40',
  },
  {
    icon: Terminal,
    num: '04',
    title: 'Prompt-to-Action',
    subtitle: 'AI Operations',
    desc: 'Run your business by typing. "Raise PO for 50kg raw material from Vendor A." F3Next interprets the command, makes the ERP entry, routes the approval, and sends the email — all from one prompt.',
    tag: 'No training needed',
    tagColor: 'text-green-400 bg-green-500/10 border-green-500/20',
    accent: 'border-green-500/40',
  },
];

export default function Vision() {
  return (
    <section id="how-it-works" className="bg-[#09090B]">

      {/* ── HOW IT WORKS ── */}
      <div className="border-t border-white/[0.06] py-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">

          <div className="text-center mb-20">
            <span className="inline-block text-xs font-bold uppercase tracking-[0.2em] text-amber-500 mb-4">The System</span>
            <h2 className="text-3xl font-bold tracking-tight text-white sm:text-5xl">
              Four phases. Zero consultants.
            </h2>
            <p className="mt-4 text-gray-500 max-w-xl mx-auto text-lg">
              F3Next takes you from "we need an ERP" to "our team is running it" — fully AI-managed.
            </p>
          </div>

          {/* Step Cards */}
          <div className="grid md:grid-cols-2 gap-6">
            {steps.map((step) => (
              <div
                key={step.num}
                className={`group relative bg-white/[0.02] border border-white/[0.06] hover:border-white/[0.12] rounded-2xl p-8 transition-all duration-300 overflow-hidden`}
              >
                {/* Step number watermark */}
                <div className="absolute top-6 right-8 text-7xl font-black text-white/[0.03] select-none leading-none">
                  {step.num}
                </div>

                <div className="relative">
                  <div className="flex items-start gap-4 mb-5">
                    <div className="w-11 h-11 rounded-xl bg-white/[0.05] border border-white/[0.08] flex items-center justify-center flex-shrink-0">
                      <step.icon className="w-5 h-5 text-gray-300" />
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-gray-600 mb-0.5">{step.subtitle}</p>
                      <h3 className="text-lg font-bold text-white">{step.title}</h3>
                    </div>
                  </div>

                  <p className="text-gray-500 leading-relaxed text-sm mb-5">{step.desc}</p>

                  <span className={`inline-block text-xs font-semibold px-3 py-1 rounded-full border ${step.tagColor}`}>
                    {step.tag}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Prompt Demo Callout */}
          <div className="mt-10 bg-[#0D0D14] border border-white/[0.08] rounded-2xl p-8 overflow-hidden relative">
            <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(245,158,11,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(245,158,11,0.03)_1px,transparent_1px)] bg-[size:30px_30px]"></div>
            <div className="relative">
              <p className="text-xs uppercase tracking-widest text-amber-500 font-bold mb-4">Live Example — Phase 4 in Action</p>
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 font-mono text-green-400 text-sm mt-0.5">$</div>
                <div>
                  <p className="font-mono text-white text-sm leading-relaxed">
                    "Send purchase order to <span className="text-amber-400">ABC Corp</span> for{' '}
                    <span className="text-green-400">10 units of Item X</span> at ₹500/unit"
                  </p>
                  <div className="mt-4 pt-4 border-t border-white/[0.06] grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                      { label: 'ERP Entry Created', color: 'text-green-400' },
                      { label: 'PO Number Generated', color: 'text-green-400' },
                      { label: 'Email Sent to Vendor', color: 'text-green-400' },
                      { label: 'Inventory Updated', color: 'text-green-400' },
                    ].map((a) => (
                      <div key={a.label} className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-400"></div>
                        <span className={`text-xs ${a.color} font-medium`}>{a.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── WHO IS IT FOR ── */}
      <div className="border-t border-white/[0.06] py-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="lg:grid lg:grid-cols-2 gap-16 items-start">

            <div>
              <span className="inline-block text-xs font-bold uppercase tracking-[0.2em] text-amber-500 mb-4">Target Users</span>
              <h2 className="text-3xl font-bold text-white mb-10 leading-tight">
                Built for companies that can't afford to get ERP wrong.
              </h2>
              <div className="space-y-7">
                {[
                  {
                    icon: Factory,
                    title: 'Manufacturing MSMEs',
                    desc: 'Factories tracking scrap, waste, raw materials, and production costs — with no dedicated IT team.',
                  },
                  {
                    icon: LayoutGrid,
                    title: 'Inventory-Heavy Operations',
                    desc: 'Businesses asking "Where is my stock?" daily. Dead capital from poor inventory visibility.',
                  },
                  {
                    icon: Cpu,
                    title: 'Failed ERP Survivors',
                    desc: 'Teams burned by traditional ERPs that cost lakhs and went nowhere. We\'re built for the 95%+ success rate.',
                  },
                  {
                    icon: TrendingDown,
                    title: 'Cost-Conscious Founders',
                    desc: 'Leaders who refuse to pay consulting fees for a "standard" setup they could configure in a weekend.',
                  },
                ].map((item, i) => (
                  <div key={i} className="flex items-start gap-4">
                    <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center flex-shrink-0">
                      <item.icon className="w-4 h-4 text-amber-400" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-white text-sm mb-1">{item.title}</h4>
                      <p className="text-gray-500 text-sm leading-relaxed">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Trust Card */}
            <div className="mt-12 lg:mt-0 bg-white/[0.02] border border-white/[0.07] rounded-2xl p-8">
              <h3 className="text-lg font-bold text-white mb-2">Safety-First Architecture</h3>
              <p className="text-gray-500 text-sm mb-8 leading-relaxed">
                AI recommends and configures. But nothing irreversible happens without your explicit sign-off.
              </p>
              <div className="space-y-6">
                {[
                  {
                    title: 'Human-in-the-Loop',
                    desc: 'Every critical configuration decision is reviewed and approved by you before it\'s applied.',
                    color: 'bg-green-500',
                  },
                  {
                    title: 'Preview Before Import',
                    desc: 'See exactly how your migrated data will look inside ERPNext before any row is committed.',
                    color: 'bg-amber-500',
                  },
                  {
                    title: 'Contradiction Detection',
                    desc: 'Our AI flags conflicting or incomplete data in your uploads and explains what needs to change.',
                    color: 'bg-blue-500',
                  },
                  {
                    title: '95%+ Success Rate',
                    desc: 'Compared to industry average of under 30% for traditional ERP implementations.',
                    color: 'bg-purple-500',
                  },
                ].map((item, i) => (
                  <div key={i} className="flex gap-4">
                    <div className={`w-1 rounded-full min-h-[40px] ${item.color} flex-shrink-0`}></div>
                    <div>
                      <h4 className="text-sm font-semibold text-white mb-1">{item.title}</h4>
                      <p className="text-xs text-gray-500 leading-relaxed">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
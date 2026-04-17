'use client';

import React from 'react';
import { AlertCircle, MessageSquareDot, Server, FileStack, Terminal } from 'lucide-react';

export default function WhyUs() {
  return (
    <section id="problem" className="bg-[#09090B]">

      {/* ── THE PROBLEM ── */}
      <div className="py-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="text-center mb-16">
            <span className="inline-block text-xs font-bold uppercase tracking-[0.2em] text-amber-500 mb-4">The Problem</span>
            <h2 className="text-3xl font-bold tracking-tight text-white sm:text-5xl leading-tight">
              ERP shouldn't take<br />
              <span className="text-amber-500">6 months and ₹5 lakh</span> to start.
            </h2>
            <p className="mt-5 max-w-2xl text-lg text-gray-500 mx-auto leading-relaxed">
              Traditional ERP implementation is broken — expensive consultants, months of setup,
              and a 70%+ failure rate. Manufacturers pay the price.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              {
                title: 'Consultant Bloat',
                desc: '100+ irrelevant questions billed by the hour. Most of it you could answer in a 5-minute chat.',
              },
              {
                title: 'Massive Upfront Cost',
                desc: 'You pay ₹5,00,000+ before seeing a single screen. No refunds if it doesn\'t fit.',
              },
              {
                title: 'Late-Stage Errors',
                desc: 'Configuration mistakes surface only after all your data is uploaded — expensive to fix.',
              },
              {
                title: 'Change is Punished',
                desc: 'Every process change triggers new consulting cycles. You\'re locked in from day one.',
              },
            ].map((item, i) => (
              <div
                key={i}
                className="group bg-white/[0.02] border border-white/[0.06] hover:border-red-500/30 p-7 rounded-xl transition-all duration-300"
              >
                <div className="w-9 h-9 rounded-lg bg-red-500/10 flex items-center justify-center mb-5">
                  <AlertCircle className="w-5 h-5 text-red-400" />
                </div>
                <h3 className="font-semibold text-white mb-2">{item.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── WHAT IS F3NEXT ── */}
      <div className="border-t border-white/[0.06] py-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="lg:grid lg:grid-cols-2 lg:gap-20 items-start">

            {/* Left: Explanation */}
            <div className="mb-12 lg:mb-0">
              <span className="inline-block text-xs font-bold uppercase tracking-[0.2em] text-amber-500 mb-4">What is F3Next?</span>
              <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl mb-6 leading-tight">
                An AI system that implements <em>and</em> operates your ERP.
              </h2>
              <p className="text-gray-400 mb-6 leading-relaxed text-lg">
                F3Next handles the entire ERP journey — from recommending the right software to deploying it, migrating your data intelligently, and then running day-to-day operations through plain English commands.
              </p>
              <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-5 mb-8">
                <p className="text-amber-300 font-medium leading-relaxed">
                  Think of it as a senior ERP architect + a trained operator — working 24/7, never billing by the hour, and completely fluent in your business.
                </p>
              </div>
              <div className="bg-white/[0.03] border border-white/[0.08] rounded-xl p-5">
                <p className="text-xs uppercase tracking-widest text-gray-600 mb-3 font-semibold">Starting with</p>
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-white font-semibold">ERPNext</span>
                  <span className="text-gray-600 text-sm">— built for SMEs & manufacturers</span>
                </div>
                <p className="text-gray-600 text-xs mt-3">More ERP platforms coming soon. One system, many choices.</p>
              </div>
            </div>

            {/* Right: 4 Pillars */}
            <div className="space-y-4">
              {[
                {
                  icon: MessageSquareDot,
                  step: '01',
                  title: 'AI Consultant',
                  desc: 'Answers 5–7 smart questions. Scores your business across size, industry, and strategy. Recommends the exact ERP fit — no sales calls needed.',
                  color: 'text-blue-400',
                  bg: 'bg-blue-500/10',
                  border: 'border-blue-500/20',
                },
                {
                  icon: Server,
                  step: '02',
                  title: 'Automated Cloud Deployment',
                  desc: 'We spin up your ERPNext instance on secure cloud infrastructure. No IT team required. Done in minutes.',
                  color: 'text-amber-400',
                  bg: 'bg-amber-500/10',
                  border: 'border-amber-500/20',
                },
                {
                  icon: FileStack,
                  step: '03',
                  title: 'Intelligent Data Migration',
                  desc: 'Upload your old ERP exports, Excel sheets, or any data format. Our system analyzes, maps, validates, and flags contradictions — before anything touches your live instance.',
                  color: 'text-purple-400',
                  bg: 'bg-purple-500/10',
                  border: 'border-purple-500/20',
                },
                {
                  icon: Terminal,
                  step: '04',
                  title: 'Prompt-to-Action Operations',
                  desc: 'Type "Send ABC Corp purchase order for 10 units of Item X" — our AI processes the command, makes the ERP entry, and sends the email. No employee training needed.',
                  color: 'text-green-400',
                  bg: 'bg-green-500/10',
                  border: 'border-green-500/20',
                },
              ].map((item, i) => (
                <div
                  key={i}
                  className={`group flex gap-5 p-5 rounded-xl border ${item.border} bg-white/[0.02] hover:bg-white/[0.04] transition-all duration-300`}
                >
                  <div className={`flex-shrink-0 w-10 h-10 rounded-lg ${item.bg} flex items-center justify-center`}>
                    <item.icon className={`w-5 h-5 ${item.color}`} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-bold text-gray-700 uppercase tracking-widest">{item.step}</span>
                      <h4 className="text-sm font-bold text-white">{item.title}</h4>
                    </div>
                    <p className="text-sm text-gray-500 leading-relaxed">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
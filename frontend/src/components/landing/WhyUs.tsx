'use client';

import React from 'react';
import { AlertCircle, BrainCircuit, Layers, ShieldCheck, Zap } from 'lucide-react';

export default function WhyUs() {
  return (
    <section id="problem">
      {/* 1. THE PROBLEM SECTION */}
      <div className="py-24 bg-gray-50">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-base text-indigo-600 font-semibold tracking-wide uppercase">The Reality</h2>
            <p className="mt-2 text-3xl leading-8 font-bold tracking-tight text-gray-900 sm:text-4xl">
              ERP shouldn't be this hard.
            </p>
            <p className="mt-4 max-w-2xl text-lg text-gray-600 mx-auto">
              ERP projects fail not because of software — but because implementation is broken.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {[
              { title: "Consultant Bloat", desc: "Consultants ask 100+ questions, most irrelevant to your business." },
              { title: "Hidden Costs", desc: "You pay upfront fees before knowing what the system actually looks like." },
              { title: "Late Errors", desc: "Configuration mistakes often only show up after you've uploaded all your data." },
              { title: "Change Friction", desc: "Every small change costs more time, more money, and more meetings." },
            ].map((item, i) => (
              <div key={i} className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
                <AlertCircle className="w-8 h-8 text-red-400 mb-4" />
                <h3 className="font-semibold text-gray-900 mb-2">{item.title}</h3>
                <p className="text-sm text-gray-600 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 2. WHAT IS F3NEXT & DIFFERENTIATORS */}
      <div className="py-24 bg-white border-t border-gray-100">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="lg:grid lg:grid-cols-2 lg:gap-16 items-center">
            <div>
              <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl mb-6">
                What is F3Next?
              </h2>
              <p className="text-lg text-gray-600 mb-6 leading-relaxed">
                F3Next is an AI-driven ERP implementation system. It asks the right questions, understands your workflow, configures your ERP, and prepares everything — before you upload a single row of data.
              </p>
              <div className="bg-indigo-50 border-l-4 border-indigo-600 p-4 mb-8">
                <p className="text-indigo-900 font-medium">
                  Think of F3Next as a senior ERP architect that works 24/7 — and never bills by the hour.
                </p>
              </div>
            </div>
            
            <div className="grid gap-6">
               {[
                 { icon: BrainCircuit, title: "AI-First Decisions", desc: "Decisions backed by rules + AI confidence, not opinions." },
                 { icon: Layers, title: "Module-by-Module Growth", desc: "Start with inventory. Add procurement later. Don't pay for bloat." },
                 { icon: ShieldCheck, title: "Human-in-the-Loop", desc: "You review every critical decision before it’s applied." },
                 { icon: Zap, title: "Factory-Native", desc: "Designed specifically for manufacturing & inventory-heavy companies." }
               ].map((feat, idx) => (
                 <div key={idx} className="flex gap-4">
                   <div className="flex-shrink-0">
                     <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-gray-900 text-white">
                       <feat.icon className="h-5 w-5" />
                     </div>
                   </div>
                   <div>
                     <h4 className="text-base font-semibold text-gray-900">{feat.title}</h4>
                     <p className="text-sm text-gray-500 mt-1">{feat.desc}</p>
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
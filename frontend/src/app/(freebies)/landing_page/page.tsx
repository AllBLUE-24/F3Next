'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-white text-slate-900 font-sans">
      
      {/* --- NAVIGATION --- */}
      <nav className="fixed w-full bg-white/80 backdrop-blur-md z-50 border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20">
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold tracking-tight text-indigo-600">F3Next</span>
            </div>
            <div className="hidden md:flex items-center space-x-8">
              <Link href="#features" className="text-sm font-medium text-slate-600 hover:text-indigo-600">Why F3?</Link>
              <Link href="#how-it-works" className="text-sm font-medium text-slate-600 hover:text-indigo-600">How it Works</Link>
              <Link href="/login" className="text-sm font-medium text-slate-600 hover:text-indigo-600">Login</Link>
              <Link 
                href="/health_check" 
                className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-bold rounded-full hover:bg-indigo-700 transition-all shadow-lg hover:shadow-indigo-200"
              >
                Start Free Audit
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* --- HERO SECTION --- */}
      <section className="pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-xs font-bold uppercase tracking-wider mb-8">
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
            New: AI Forensic Engine v1.0
          </div>
          
          <h1 className="text-5xl lg:text-7xl font-extrabold tracking-tight text-slate-900 mb-6">
            Stop Manufacturing <br className="hidden lg:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-blue-500">
              Financial Leakage.
            </span>
          </h1>
          
          <p className="mt-4 max-w-2xl mx-auto text-xl text-slate-500 leading-relaxed">
            F3Next identifies dead capital, inventory blindspots, and manual inefficiencies in your factory. 
            Get a forensic health report in 2 minutes.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
            <button 
              onClick={() => router.push('/health_check')}
              className="px-8 py-4 bg-indigo-600 text-white text-lg font-bold rounded-lg shadow-xl hover:bg-indigo-700 hover:shadow-2xl hover:-translate-y-1 transition-all flex items-center justify-center"
            >
              Get Your Free Health Check
              <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path></svg>
            </button>
            <button className="px-8 py-4 bg-white text-slate-700 text-lg font-bold rounded-lg border border-slate-200 hover:bg-slate-50 transition-all">
              Watch Demo
            </button>
          </div>

          <p className="mt-6 text-sm text-slate-400">
            No credit card required · Free Forensic Report · Instant AI Analysis
          </p>
        </div>

        {/* Abstract Background Decoration */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full z-0 opacity-40 pointer-events-none">
          <div className="absolute top-20 left-10 w-72 h-72 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob"></div>
          <div className="absolute top-20 right-10 w-72 h-72 bg-indigo-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-2000"></div>
          <div className="absolute -bottom-8 left-1/2 w-72 h-72 bg-blue-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-4000"></div>
        </div>
      </section>

      {/* --- PROBLEM / SOLUTION GRID --- */}
      <section id="features" className="py-24 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-slate-900">Why factories lose money</h2>
            <p className="mt-4 text-lg text-slate-500">Most ERPs are just data entry tools. F3Next is a diagnostic intelligence.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* Card 1 */}
            <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center mb-6">
                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-3">Inventory Blindness</h3>
              <p className="text-slate-600 leading-relaxed">
                You don't know exactly what's on the floor right now. Dead stock eats 15-20% of working capital annually.
              </p>
            </div>

            {/* Card 2 */}
            <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center mb-6">
                <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-3">Cost Leakage</h3>
              <p className="text-slate-600 leading-relaxed">
                Manual BOMs and Excel costing sheets fail to capture price fluctuations, eroding your margins silently.
              </p>
            </div>

            {/* Card 3 */}
            <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-6">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-3">Dependency Risk</h3>
              <p className="text-slate-600 leading-relaxed">
                If your store manager leaves, does your intelligence leave with him? F3Next digitizes tribal knowledge.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* --- HOW IT WORKS (Timeline) --- */}
      <section id="how-it-works" className="py-24 bg-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-slate-900">How F3Next Works</h2>
          </div>

          <div className="relative">
            {/* Vertical Line */}
            <div className="absolute left-8 top-0 bottom-0 w-px bg-indigo-100 md:left-1/2"></div>

            {/* Step 1 */}
            <div className="relative z-10 mb-12 md:flex md:justify-between items-center group">
              <div className="flex items-center md:w-1/2 md:justify-end md:pr-12 mb-4 md:mb-0">
                <div className="bg-white p-6 rounded-xl shadow border border-slate-100 md:text-right w-full md:w-auto">
                  <h4 className="text-lg font-bold text-slate-900">1. Take the Health Check</h4>
                  <p className="text-slate-500 mt-2">Answer 10 diagnostic questions about your ops.</p>
                </div>
              </div>
              <div className="absolute left-8 -translate-x-1/2 md:left-1/2 flex items-center justify-center w-8 h-8 rounded-full bg-indigo-600 text-white font-bold border-4 border-white shadow">1</div>
              <div className="md:w-1/2"></div>
            </div>

            {/* Step 2 */}
            <div className="relative z-10 mb-12 md:flex md:justify-between items-center group">
              <div className="md:w-1/2"></div>
              <div className="absolute left-8 -translate-x-1/2 md:left-1/2 flex items-center justify-center w-8 h-8 rounded-full bg-white text-indigo-600 font-bold border-2 border-indigo-600 shadow">2</div>
              <div className="flex items-center md:w-1/2 md:justify-start md:pl-12">
                <div className="bg-white p-6 rounded-xl shadow border border-slate-100 w-full md:w-auto">
                  <h4 className="text-lg font-bold text-slate-900">2. Get Forensic Report</h4>
                  <p className="text-slate-500 mt-2">AI analyzes your risk profile and calculates losses.</p>
                </div>
              </div>
            </div>

            {/* Step 3 */}
            <div className="relative z-10 md:flex md:justify-between items-center group">
              <div className="flex items-center md:w-1/2 md:justify-end md:pr-12 mb-4 md:mb-0">
                <div className="bg-white p-6 rounded-xl shadow border border-slate-100 md:text-right w-full md:w-auto">
                  <h4 className="text-lg font-bold text-slate-900">3. Deploy Solution</h4>
                  <p className="text-slate-500 mt-2">One-click deploy the exact ERP module you need.</p>
                </div>
              </div>
              <div className="absolute left-8 -translate-x-1/2 md:left-1/2 flex items-center justify-center w-8 h-8 rounded-full bg-white text-indigo-600 font-bold border-2 border-indigo-600 shadow">3</div>
              <div className="md:w-1/2"></div>
            </div>
          </div>
        </div>
      </section>

      {/* --- CTA FOOTER --- */}
      <footer className="bg-slate-900 py-16 text-center text-white">
        <div className="max-w-4xl mx-auto px-4">
          <h2 className="text-3xl font-bold mb-6">Ready to stop the bleeding?</h2>
          <p className="text-slate-400 mb-8 text-lg">
            Join 500+ manufacturers optimizing their floor with F3Next.
          </p>
          <button 
            onClick={() => router.push('/health_check')}
            className="px-10 py-4 bg-indigo-600 text-white font-bold rounded-lg hover:bg-indigo-500 transition-colors shadow-lg shadow-indigo-900/50"
          >
            Start Your Transformation &rarr;
          </button>
          <p className="mt-12 text-xs text-slate-600">
            © 2025 F3Next Inc. All rights reserved.
          </p>
        </div>
      </footer>

    </div>
  );
}
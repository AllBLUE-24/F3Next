'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FileText, Clock, ShieldCheck, ArrowRight, Activity, ChevronRight } from 'lucide-react';

export default function HealthCheckLanding() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-white text-slate-900 font-sans">
      
      {/* --- NAVIGATION (Minimalist for Tool) --- */}
      <nav className="absolute top-0 w-full z-50 border-b border-white/10 bg-slate-950/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo Redirects to Main Home */}
            <Link href="/" className="flex items-center gap-2 group">
              <div className="bg-indigo-600 p-1.5 rounded-lg group-hover:bg-indigo-500 transition-colors">
                 <Activity className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold tracking-tight text-white">F3Next</span>
            </Link>
            
            <div className="flex items-center gap-4">
              <span className="hidden md:inline text-xs font-mono text-indigo-300 uppercase tracking-widest">Free Forensic Tool v1.0</span>
              
            </div>
          </div>
        </div>
      </nav>

      {/* --- HERO SECTION (Dark Mode + Visible Grid) --- */}
      <section className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden bg-slate-950">
        
        {/* 1. VISIBLE BACKGROUND */}
        <div className="absolute inset-0 z-0">
            {/* Grid Pattern */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]"></div>
            {/* Top Glow */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-indigo-600/20 blur-[120px] rounded-full pointer-events-none"></div>
            {/* Bottom Accent */}
            <div className="absolute bottom-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent"></div>
        </div>

        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
          
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-900/40 border border-indigo-500/30 text-indigo-300 text-xs font-bold uppercase tracking-wider mb-8 backdrop-blur-md shadow-lg shadow-indigo-900/20">
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse"></span>
            Free Audit Tool
          </div>
          
          {/* Headline */}
          <h1 className="text-4xl lg:text-6xl font-extrabold tracking-tight text-white mb-6 leading-tight">
            What is your factory's <br/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">
              Operational Health Score?
            </span>
          </h1>
          
          {/* Subhead */}
          <p className="mt-6 max-w-2xl mx-auto text-xl text-slate-400 leading-relaxed">
            Most manufacturers are running at 60% efficiency without knowing it.
            Answer 10 questions to identify hidden bottlenecks and get a 
            <span className="text-white font-semibold"> custom forensic report.</span>
          </p>

          {/* Metrics Strip */}
          <div className="mt-8 flex flex-wrap justify-center gap-6 text-sm text-slate-400 font-medium">
             <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-indigo-400" /> 2 Minutes
             </div>
             <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-400" /> PDF Report
             </div>
             <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-indigo-400" /> No Credit Card
             </div>
          </div>

          {/* CTA Area */}
          <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center items-center">
            <button 
              onClick={() => router.push('/health_check')}
              className="group relative inline-flex items-center justify-center px-8 py-4 text-lg font-bold text-white transition-all duration-200 bg-indigo-600 rounded-full hover:bg-indigo-500 hover:scale-105 shadow-[0_0_40px_-10px_rgba(79,70,229,0.5)] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-600 focus:ring-offset-slate-900"
            >
              Start Free Audit
              <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
            </button>
            <p className="text-xs text-slate-500 sm:hidden">Takes less than 2 minutes</p>
          </div>
        </div>
      </section>

      {/* --- PREVIEW SECTION (What you get) --- */}
      <section className="py-24 bg-slate-50 border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          
          <div className="grid md:grid-cols-2 gap-12 items-center">
            {/* Left: Text */}
            <div>
                <h2 className="text-3xl font-bold text-slate-900 mb-6">Don't guess. <br/> Get the data.</h2>
                <p className="text-lg text-slate-600 mb-8 leading-relaxed">
                    This isn't a sales call request. It's an automated diagnostic engine. 
                    We compare your answers against 500+ successful manufacturing workflows to calculate your risk score.
                </p>
                
                <div className="space-y-6">
                    <div className="flex gap-4">
                        <div className="w-10 h-10 rounded-full bg-white border border-slate-200 flex items-center justify-center text-indigo-600 font-bold shadow-sm shrink-0">1</div>
                        <div>
                            <h3 className="font-bold text-slate-900">Answer 10 Questions</h3>
                            <p className="text-sm text-slate-500 mt-1">Simple Yes/No questions about inventory, procurement, and sales.</p>
                        </div>
                    </div>
                    <div className="flex gap-4">
                         <div className="w-10 h-10 rounded-full bg-white border border-slate-200 flex items-center justify-center text-indigo-600 font-bold shadow-sm shrink-0">2</div>
                        <div>
                            <h3 className="font-bold text-slate-900">AI Analysis</h3>
                            <p className="text-sm text-slate-500 mt-1">Our engine identifies gaps in your process vs. industry standards.</p>
                        </div>
                    </div>
                    <div className="flex gap-4">
                         <div className="w-10 h-10 rounded-full bg-white border border-slate-200 flex items-center justify-center text-indigo-600 font-bold shadow-sm shrink-0">3</div>
                        <div>
                            <h3 className="font-bold text-slate-900">Instant Report</h3>
                            <p className="text-sm text-slate-500 mt-1">Get a Health Score (0-100) and a list of urgent fixes.</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Right: The Mockup Card */}
            <div className="relative">
                <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 to-cyan-500 rounded-2xl blur opacity-20"></div>
                <div className="relative bg-white rounded-xl shadow-2xl border border-slate-100 overflow-hidden">
                    <div className="bg-slate-50 px-6 py-4 border-b border-slate-100 flex justify-between items-center">
                        <div className="flex gap-2">
                            <div className="w-3 h-3 rounded-full bg-red-400"></div>
                            <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                            <div className="w-3 h-3 rounded-full bg-green-400"></div>
                        </div>
                        <div className="text-xs font-mono text-slate-400">CONFIDENTIAL REPORT</div>
                    </div>
                    <div className="p-8">
                        <div className="flex justify-between items-start mb-8">
                            <div>
                                <h4 className="text-slate-500 text-sm uppercase tracking-wide">Overall Health Score</h4>
                                <div className="text-5xl font-extrabold text-indigo-600 mt-2">72<span className="text-lg text-slate-400 font-normal">/100</span></div>
                            </div>
                            <div className="bg-red-50 text-red-700 px-3 py-1 rounded-full text-xs font-bold border border-red-100">
                                High Risk Detected
                            </div>
                        </div>
                        
                        <div className="space-y-4">
                            <div>
                                <div className="flex justify-between text-sm font-medium mb-1">
                                    <span className="text-slate-700">Inventory Visibility</span>
                                    <span className="text-red-500">Critical</span>
                                </div>
                                <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                                    <div className="h-full bg-red-500 w-[30%]"></div>
                                </div>
                            </div>
                            <div>
                                <div className="flex justify-between text-sm font-medium mb-1">
                                    <span className="text-slate-700">Procurement Efficiency</span>
                                    <span className="text-yellow-500">Moderate</span>
                                </div>
                                <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                                    <div className="h-full bg-yellow-400 w-[65%]"></div>
                                </div>
                            </div>
                        </div>
                        
                        <div className="mt-8 pt-6 border-t border-slate-100">
                            <p className="text-xs text-slate-400 mb-2">Recommendation:</p>
                            <p className="text-sm text-slate-700 font-medium">
                                "Immediate implementation of Batch Tracking is recommended to prevent further capital leakage..."
                            </p>
                        </div>
                    </div>
                </div>
            </div>

          </div>
        </div>
      </section>

      {/* --- SIMPLE FOOTER --- */}
      <footer className="bg-white py-12 border-t border-slate-100">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <h2 className="text-2xl font-bold text-slate-900 mb-6">Stop flying blind.</h2>
          <button 
             onClick={() => router.push('/health_check')}
             className="px-8 py-3 bg-slate-900 text-white font-bold rounded-lg hover:bg-slate-800 transition-colors"
          >
            Start Assessment
          </button>
          <div className="mt-8 flex justify-center gap-6 text-sm text-slate-400">
            <Link href="/" className="hover:text-slate-600">Home</Link>
            <Link href="/" className="hover:text-slate-600">Privacy Policy</Link>
            <span>© 2025 F3Next Inc.</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
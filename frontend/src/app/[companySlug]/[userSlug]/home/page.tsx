"use client";

import { use } from "react";
import Link from "next/link";
import { Bot, Terminal, UploadCloud, ArrowRight, Sparkles } from "lucide-react";

interface PageProps {
  params: Promise<{ companySlug: string; userSlug: string }>;
}

export default function HomePage({ params }: PageProps) {
  const { companySlug, userSlug } = use(params);
  const base = `/${companySlug}/${userSlug}`;

  return (
    <div className="space-y-10 fade-in-up">
      
      {/* Header */}
      <div className="space-y-3">
        <div className="inline-flex items-center gap-2 rounded-full border border-[var(--border-subtle)] bg-[var(--bg-card)] px-3 py-1 mb-2">
          <Sparkles className="w-3 h-3 text-amber-500" />
          <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Mission Control</span>
        </div>
        <h1 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight">
          Welcome back.
        </h1>
        <p className="text-base text-zinc-500 max-w-xl leading-relaxed">
          Select a module to continue building and operating your ERP.
        </p>
      </div>

      {/* Modules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* Discovery Agent - HIGHLIGHTED */}
        <Link 
          href={`${base}/discovery`}
          className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-amber-500/20 bg-amber-500/[0.04] p-7 transition-all duration-200 hover:border-amber-500/40 hover:bg-amber-500/[0.07] hover:shadow-xl hover:shadow-amber-500/5 md:col-span-1"
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(245,158,11,0.06),transparent_50%)]" />
          <div className="relative z-10">
            <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-amber-500 text-black shadow-lg shadow-amber-500/20">
              <Bot className="h-5 w-5" />
            </div>
            <div className="inline-flex items-center rounded-lg border border-amber-500/20 bg-amber-500/8 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-400 mb-3">
              Step 1 · Entry Point
            </div>
            <h2 className="text-xl font-bold text-white mb-2">Discovery Agent</h2>
            <p className="text-zinc-500 text-sm leading-relaxed">
              AI consultant that gathers requirements and recommends the perfect ERP configuration.
            </p>
          </div>
          <div className="relative z-10 mt-6 flex items-center text-sm font-bold text-amber-400 group-hover:text-amber-300 transition-colors">
            Start Discovery <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
          </div>
        </Link>

        {/* Intelligence Suite (IS / Upload) */}
        <Link 
          href={`${base}/upload`}
          className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-7 transition-all duration-200 hover:border-[var(--border-default)] hover:bg-[var(--bg-elevated)]"
        >
          <div className="relative z-10">
            <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--bg-elevated)] text-zinc-400 border border-[var(--border-default)] group-hover:text-white group-hover:border-zinc-600 transition-all">
              <UploadCloud className="h-5 w-5" />
            </div>
            <div className="inline-flex items-center rounded-lg border border-[var(--border-subtle)] bg-white/[0.03] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-3">
              Step 2 · Data Migration
            </div>
            <h2 className="text-xl font-bold text-white mb-2">Intelligence Suite</h2>
            <p className="text-zinc-500 text-sm leading-relaxed">
              Upload legacy data. The AI maps, validates, and migrates into new schemas automatically.
            </p>
          </div>
          <div className="relative z-10 mt-6 flex items-center text-sm font-bold text-zinc-400 group-hover:text-white transition-colors">
            Upload Data <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
          </div>
        </Link>

        {/* OS Command */}
        <Link 
          href={`${base}/command`}
          className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-card)] p-7 transition-all duration-200 hover:border-[var(--border-default)] hover:bg-[var(--bg-elevated)]"
        >
          <div className="relative z-10">
            <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--bg-elevated)] text-zinc-400 border border-[var(--border-default)] group-hover:text-white group-hover:border-zinc-600 transition-all">
              <Terminal className="h-5 w-5" />
            </div>
            <div className="inline-flex items-center rounded-lg border border-[var(--border-subtle)] bg-white/[0.03] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-3">
              Step 3 · Operations
            </div>
            <h2 className="text-xl font-bold text-white mb-2">Operating System</h2>
            <p className="text-zinc-500 text-sm leading-relaxed">
              Run your ERP entirely through plain English commands. No navigation needed.
            </p>
          </div>
          <div className="relative z-10 mt-6 flex items-center text-sm font-bold text-zinc-400 group-hover:text-white transition-colors">
            Open Terminal <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
          </div>
        </Link>

      </div>
    </div>
  );
}
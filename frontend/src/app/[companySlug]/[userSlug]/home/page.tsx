"use client";

import { use } from "react";
import Link from "next/link";
import { Bot, Terminal, UploadCloud, ArrowRight } from "lucide-react";

interface PageProps {
  params: Promise<{ companySlug: string; userSlug: string }>;
}

export default function HomePage({ params }: PageProps) {
  const { companySlug, userSlug } = use(params);

  return (
    <div className="space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out">
      
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-4xl md:text-5xl font-black text-white tracking-tight">
          Welcome back.
        </h1>
        <p className="text-lg text-zinc-400 max-w-2xl leading-relaxed">
          Select a module to continue building and operating your ERP. The Discovery Agent is the recommended entry point for new workflows.
        </p>
      </div>

      {/* Modules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Discovery Agent - HIGHLIGHTED */}
        <Link 
          href={`/${companySlug}/${userSlug}/discovery`}
          className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-amber-500/30 bg-amber-500/5 p-8 transition-all hover:border-amber-500/60 hover:bg-amber-500/10 hover:shadow-2xl hover:shadow-amber-500/20 md:col-span-1"
        >
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(245,158,11,0.1),transparent_50%)]" />
          <div className="relative z-10">
            <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-xl bg-amber-500 text-black shadow-lg shadow-amber-500/30">
              <Bot className="h-7 w-7" />
            </div>
            <div className="inline-flex items-center rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-amber-400 mb-4">
              Step 1 · Entry Point
            </div>
            <h2 className="text-2xl font-bold text-white mb-3">Discovery Agent</h2>
            <p className="text-zinc-400 text-sm leading-relaxed">
              AI consultant that gathers requirements, maps your processes, and recommends the perfect ERP architecture in minutes.
            </p>
          </div>
          <div className="relative z-10 mt-8 flex items-center text-sm font-bold text-amber-400">
            Start Discovery <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
          </div>
        </Link>

        {/* Intelligence Suite (IS / Upload) */}
        <Link 
          href={`/${companySlug}/${userSlug}/upload`}
          className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-8 transition-all hover:border-white/20 hover:bg-white/10"
        >
          <div className="relative z-10">
            <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-xl bg-zinc-800 text-zinc-300 border border-white/10 group-hover:text-white transition-colors">
              <UploadCloud className="h-7 w-7" />
            </div>
            <div className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-zinc-400 mb-4">
              Step 2 · Data Migration
            </div>
            <h2 className="text-2xl font-bold text-white mb-3">Intelligence Suite</h2>
            <p className="text-zinc-400 text-sm leading-relaxed">
              Upload legacy data in any format. The AI automatically maps, validates, and migrates it into the new schemas.
            </p>
          </div>
          <div className="relative z-10 mt-8 flex items-center text-sm font-bold text-zinc-300 group-hover:text-white">
            Upload Data <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
          </div>
        </Link>

        {/* OS Command */}
        <Link 
          href={`/${companySlug}/${userSlug}/command`}
          className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-8 transition-all hover:border-white/20 hover:bg-white/10"
        >
          <div className="relative z-10">
            <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-xl bg-zinc-800 text-zinc-300 border border-white/10 group-hover:text-white transition-colors">
              <Terminal className="h-7 w-7" />
            </div>
            <div className="inline-flex items-center rounded-full border border-white/10 bg-white/5 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-zinc-400 mb-4">
              Step 3 · Operations
            </div>
            <h2 className="text-2xl font-bold text-white mb-3">Operating System</h2>
            <p className="text-zinc-400 text-sm leading-relaxed">
              Operate your ERP entirely through plain English commands. No navigation, no training required.
            </p>
          </div>
          <div className="relative z-10 mt-8 flex items-center text-sm font-bold text-zinc-300 group-hover:text-white">
            Open Terminal <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
          </div>
        </Link>

      </div>
    </div>
  );
}
'use client';

import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useRouter } from 'next/navigation';
import EarlyAccess from './early-access'; 

export default function ReportPage() {
  const router = useRouter();
  const [report, setReport] = useState<string>('');
  
  const [meta, setMeta] = useState({ 
    name: 'Valued Client', 
    company: 'Your Organization', 
    role: 'Executive', 
    date: new Date().toLocaleDateString() 
  });
  
  const [annualBleed, setAnnualBleed] = useState('Calculating...');
  const [projectId, setProjectId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedReport = localStorage.getItem('f3_last_report');
    const storedMeta = localStorage.getItem('f3_user_metadata');
    const storedBleed = localStorage.getItem('f3_annual_bleed'); 
    const storedProjId = localStorage.getItem('f3_project_id');

    if (storedReport) {
      setReport(storedReport);
      setProjectId(storedProjId);
      if (storedBleed) setAnnualBleed(storedBleed);
      
      if (storedMeta) {
        try {
          setMeta(JSON.parse(storedMeta));
        } catch (e) { console.error(e); }
      }
      setLoading(false);
    } else {
      setReport("## Analysis Pending\n\nPlease return to the dashboard to complete your assessment.");
      setLoading(false);
    }
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center h-screen bg-slate-50 text-indigo-600">
      <div className="animate-pulse flex flex-col items-center">
        <div className="h-12 w-12 border-4 border-current border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="font-medium tracking-wide text-sm uppercase">Generating Forensic Analysis...</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F8FAFC] font-sans text-slate-900 pb-24 print:bg-white">
      
      {/* --- 1. STICKY GLASS NAVBAR --- */}
      <nav className="fixed top-0 w-full z-50 bg-white/80 backdrop-blur-md border-b border-slate-200/80 transition-all duration-300 print:hidden">
         <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
            <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold shadow-md shadow-indigo-200">F3</div>
                <span className="font-bold text-slate-800 text-lg tracking-tight">Intelligence</span>
            </div>
            
            <div className="flex items-center gap-4">
                <div className="hidden sm:block text-xs font-medium text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
                    ID: <span className="font-mono text-slate-700">{projectId?.slice(0,8)}</span>
                </div>
                <button 
                  onClick={() => window.print()} 
                  className="text-sm font-bold text-slate-600 hover:text-indigo-600 flex items-center gap-2 transition-colors bg-white border border-slate-200 px-4 py-2 rounded-lg hover:border-indigo-200 hover:shadow-sm"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"></path></svg>
                    Print Report
                </button>
            </div>
         </div>
      </nav>

      {/* Spacer for fixed nav */}
      <div className="h-16"></div>

      {/* --- 2. REPORT HEADER (Dark Gradient) --- */}
      <div className="bg-gradient-to-b from-[#0B1120] to-[#1e293b] text-white pt-12 pb-32 relative overflow-hidden print:hidden">
         {/* Background Effects */}
         <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-indigo-500/20 rounded-full blur-[120px] -mr-40 -mt-40 pointer-events-none animate-pulse-slow"></div>
         
         <div className="max-w-5xl mx-auto px-6 relative z-10">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-8">
                <div>
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 text-[11px] font-bold uppercase tracking-wider mb-4 shadow-lg shadow-green-900/20">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></span>
                        Forensic Audit Complete
                    </div>
                    <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight mb-2 text-white drop-shadow-sm">
                        {meta.company}
                    </h1>
                    <div className="flex flex-wrap items-center gap-4 text-slate-400 text-sm mt-4">
                        <div className="flex items-center gap-2 bg-white/5 px-3 py-1.5 rounded-lg border border-white/10">
                            <span className="text-slate-500 text-xs uppercase font-bold">Prepared For</span>
                            <span className="text-white font-medium">{meta.name}</span>
                        </div>
                        <div className="flex items-center gap-2 bg-white/5 px-3 py-1.5 rounded-lg border border-white/10">
                            <span className="text-slate-500 text-xs uppercase font-bold">Role</span>
                            <span className="text-white font-medium">{meta.role}</span>
                        </div>
                    </div>
                </div>

                {/* The "Bleed" Stat - Floating Card */}
                <div className="bg-white/10 backdrop-blur-md border border-white/10 p-6 rounded-2xl min-w-[260px] shadow-2xl transform transition hover:scale-105 duration-300">
                    <p className="text-xs font-bold text-indigo-200 uppercase tracking-widest mb-2">Total Annual Leakage</p>
                    <p className="text-4xl font-black text-white tracking-tight drop-shadow-md">₹{annualBleed}</p>
                    <div className="mt-3 h-1 w-full bg-white/10 rounded-full overflow-hidden">
                        <div className="h-full bg-red-500 w-3/4 animate-pulse"></div>
                    </div>
                    <p className="text-[10px] text-red-300 mt-2 font-medium text-right uppercase tracking-wide">Critical Level</p>
                </div>
            </div>
         </div>
      </div>

      <main className="max-w-5xl mx-auto px-6 -mt-20 relative z-20">
        
        {/* --- 3. THE REPORT CONTENT --- */}
        <div className="bg-white rounded-xl shadow-xl shadow-slate-200/50 border border-slate-100 p-10 md:p-14 min-h-[600px] print:shadow-none print:border-none">
            <article className="prose prose-lg prose-slate max-w-none prose-headings:font-bold prose-headings:tracking-tight prose-p:leading-relaxed prose-li:leading-relaxed">
                <ReactMarkdown
                    components={{
                        h1: ({node, ...props}) => (
                            <div className="flex items-baseline gap-4 mt-12 mb-6 border-b border-slate-100 pb-4">
                                <h1 className="text-3xl font-bold text-slate-900 m-0" {...props} />
                            </div>
                        ),
                        h2: ({node, ...props}) => (
                            <h2 className="text-xl font-bold text-indigo-900 mt-10 mb-4 flex items-center gap-3" {...props}>
                                <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 text-lg">#</span>
                                {props.children}
                            </h2>
                        ),
                        ul: ({node, ...props}) => <ul className="space-y-3 my-6 pl-0 list-none" {...props} />,
                        li: ({node, ...props}) => (
                            <li className="flex items-start gap-3 pl-2 group transition-all hover:translate-x-1 duration-200" {...props}>
                                <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 group-hover:bg-indigo-600 transition-colors"></div>
                                <span className="text-slate-600 group-hover:text-slate-900 transition-colors">{props.children}</span>
                            </li>
                        ),
                        p: ({node, ...props}) => <p className="mb-6 text-slate-600 text-[17px] leading-8" {...props} />,
                        strong: ({node, ...props}) => <strong className="font-semibold text-slate-900 bg-yellow-50 px-1 rounded border-b-2 border-yellow-200" {...props} />,
                        blockquote: ({node, ...props}) => (
                            <div className="bg-indigo-50/50 border-l-4 border-indigo-500 p-6 my-8 rounded-r-lg italic text-slate-700 relative">
                                <span className="absolute top-2 left-2 text-4xl text-indigo-200 font-serif opacity-50">"</span>
                                {props.children}
                            </div>
                        )
                    }}
                >
                    {report}
                </ReactMarkdown>
            </article>

            {/* Footer */}
            <div className="mt-24 pt-8 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400 uppercase tracking-widest print:hidden">
                <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-green-400"></span>
                    Generated by F3Next Intelligence Engine v1.0.0
                </div>
                <span>Ref: {projectId?.slice(0,8)}</span>
            </div>
        </div>

        {/* --- 4. THE EARLY ACCESS (Bottom Section) --- */}
        <div className="print:hidden pb-10">
            <EarlyAccess 
                annualBleed={annualBleed} 
                projectId={projectId} 
                onSuccess={() => {
                    alert("Welcome to the Private Cohort! We will be in touch shortly.");
                    router.push('/dashboard');
                }}
            />
        </div>

      </main>
    </div>
  );
}
'use client';

import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useRouter } from 'next/navigation';
import EarlyAccess from './early-access'; 
import { Printer, Download, Share2, AlertTriangle, TrendingDown, FileText } from 'lucide-react';

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
    const storedProjId = localStorage.getItem('f3_project_id');
    const storedBleed = localStorage.getItem('f3_annual_bleed');
    const storedMeta = localStorage.getItem('f3_user_metadata');
    const storedReport = localStorage.getItem('f3_last_report');

    setProjectId(storedProjId);
    if (storedBleed) setAnnualBleed(storedBleed);
    
    if (storedMeta) {
      try {
        setMeta(JSON.parse(storedMeta));
      } catch (e) { console.error(e); }
    }

    // Polling function to check if the Agent is done
    const checkReportStatus = async () => {
      if (!storedProjId) {
        // Fallback if no project ID is found
        if (storedReport) {
            setReport(storedReport);
            setLoading(false);
        } else {
            setReport("# Report Pending\n\nWe could not find your assessment data. Please return to the dashboard.");
            setLoading(false);
        }
        return true; 
      }
      
      try {
        const apiUrl = (typeof window !== "undefined" ? "" : "http://backend_api:8000");
        const res = await fetch(`${apiUrl}/health_check/status/${storedProjId}`);
        const data = await res.json();

        if (data.is_ready) {
          setReport(data.report_content);
          
          if (data.annual_bleed) {
            setAnnualBleed(data.annual_bleed); 
            localStorage.setItem('f3_annual_bleed', data.annual_bleed);
        }
          setLoading(false);
          localStorage.setItem('f3_last_report', data.report_content);
          return true; // Stop the interval
        }
      } catch (err) {
        console.error("Audit Fetch Error:", err);
      }
      return false;
    };

    // Check every 3 seconds
    const pollInterval = setInterval(async () => {
      const isDone = await checkReportStatus();
      if (isDone) clearInterval(pollInterval);
    }, 3000);

    // Immediate first check
    checkReportStatus();

    return () => clearInterval(pollInterval);
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center h-screen bg-slate-50 text-indigo-900 font-serif">
      <div className="flex flex-col items-center gap-4">
        <div className="h-16 w-16 border-4 border-indigo-900 border-t-transparent rounded-full animate-spin"></div>
        <p className="tracking-widest text-sm uppercase font-semibold">Generating Forensic Audit...</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F0F2F5] font-sans text-slate-900 pb-24 print:bg-white print:pb-0">
      
      {/* --- 1. ACTION BAR (Screen Only) --- */}
      <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-slate-200 px-6 h-16 flex items-center justify-between shadow-sm print:hidden">
         <div className="flex items-center gap-3">
             <div className="w-8 h-8 bg-indigo-900 rounded flex items-center justify-center text-white font-serif font-bold">F3</div>
             <span className="font-semibold text-slate-700">Audit Report <span className="text-slate-400 font-normal">/ {meta.company}</span></span>
         </div>
         <div className="flex items-center gap-3">
             <button onClick={() => window.print()} className="p-2 text-slate-500 hover:text-indigo-900 hover:bg-indigo-50 rounded-full transition" title="Print Report">
                 <Printer className="w-5 h-5" />
             </button>
             <button className="hidden sm:flex items-center gap-2 px-4 py-2 bg-indigo-900 text-white text-sm font-medium rounded-lg hover:bg-indigo-800 transition shadow-lg shadow-indigo-900/20">
                 <Download className="w-4 h-4" /> Download PDF
             </button>
         </div>
      </nav>

      <main className="max-w-[210mm] mx-auto mt-8 print:mt-0 print:max-w-none">
        
        {/* --- 2. THE PAPER (The Artifact) --- */}
        <div className="bg-white shadow-2xl print:shadow-none min-h-[297mm] relative overflow-hidden">
            
            {/* Decorative Top Bar */}
            <div className="h-2 w-full bg-gradient-to-r from-indigo-900 via-indigo-700 to-indigo-900"></div>

            {/* Watermark (Background) */}
            <div className="absolute inset-0 pointer-events-none opacity-[0.02] flex items-center justify-center overflow-hidden">
                <div className="transform -rotate-45 text-[15rem] font-black text-slate-900 whitespace-nowrap">CONFIDENTIAL</div>
            </div>

            {/* --- REPORT HEADER --- */}
            <header className="px-12 pt-12 pb-8 border-b border-slate-100 relative">
                <div className="flex justify-between items-start">
                    <div>
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-[0.2em] mb-2">Operational Forensic Audit</p>
                        <h1 className="text-4xl font-serif font-bold text-slate-900 mb-2">{meta.company}</h1>
                        <p className="text-slate-500 text-sm">Prepared for <span className="font-semibold text-slate-700">{meta.name}</span> • {meta.date}</p>
                    </div>
                    <div className="text-right hidden sm:block">
                        <div className="inline-block bg-slate-50 border border-slate-100 px-4 py-2 rounded-lg">
                            <p className="text-[10px] text-slate-400 uppercase font-bold text-left mb-1">Audit Reference</p>
                            <p className="font-mono text-lg text-slate-700 font-medium tracking-tight">#{projectId?.slice(0,8).toUpperCase()}</p>
                        </div>
                    </div>
                </div>

                {/* --- KEY METRIC: ANNUAL BLEED --- */}
                <div className="mt-8 bg-red-50 border border-red-100 rounded-xl p-6 flex flex-col sm:flex-row items-center justify-between gap-6 print:bg-white print:border-2 print:border-red-500">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-red-100 text-red-600 rounded-full flex items-center justify-center shrink-0">
                            <AlertTriangle className="w-6 h-6" />
                        </div>
                        <div>
                            <h3 className="text-red-900 font-bold text-lg">Capital Leakage Detected</h3>
                            <p className="text-red-700/80 text-sm">Estimated annual operational waste based on current workflow.</p>
                        </div>
                    </div>
                    <div className="text-right">
                         <div className="text-3xl sm:text-4xl font-black text-red-600 tabular-nums tracking-tight">
                            ₹{annualBleed}
                         </div>
                         <div className="text-[10px] font-bold text-red-400 uppercase tracking-widest mt-1">
                            Annual Impact
                         </div>
                    </div>
                </div>
            </header>

            {/* --- REPORT BODY --- */}
            <article className="px-12 py-12">
                <div className="prose prose-slate max-w-none prose-lg">
                    <ReactMarkdown
                        components={{
                            h1: ({node, ...props}) => (
                                <div className="break-inside-avoid-page mt-8 mb-6">
                                    <h1 className="text-2xl font-serif font-bold text-slate-900 border-b-2 border-slate-900 pb-2 inline-block" {...props} />
                                </div>
                            ),
                            h2: ({node, ...props}) => (
                                <div className="break-inside-avoid-page mt-8 mb-4">
                                    <h2 className="text-xl font-bold text-indigo-900 flex items-center gap-2" {...props}>
                                        <span className="w-1.5 h-6 bg-indigo-500 rounded-full inline-block mr-2"></span>
                                        {props.children}
                                    </h2>
                                </div>
                            ),
                            p: ({node, ...props}) => <p className="text-slate-700 text-[16px] leading-relaxed mb-6 text-justify" {...props} />,
                            ul: ({node, ...props}) => <ul className="space-y-2 my-6 bg-slate-50/50 p-6 rounded-lg border border-slate-100" {...props} />,
                            li: ({node, ...props}) => (
                                <li className="flex items-start gap-3 text-slate-700 text-[16px]">
                                    <span className="mt-2 w-1.5 h-1.5 bg-indigo-600 rounded-full shrink-0"></span>
                                    <span>{props.children}</span>
                                </li>
                            ),
                            strong: ({node, ...props}) => <strong className="font-bold text-slate-900 bg-yellow-100/50 px-1 rounded" {...props} />,
                            blockquote: ({node, ...props}) => (
                                <div className="break-inside-avoid-page my-8 pl-6 border-l-4 border-indigo-900 italic text-slate-600 bg-slate-50 py-4 pr-4 rounded-r-lg">
                                    {props.children}
                                </div>
                            )
                        }}
                    >
                        {report}
                    </ReactMarkdown>
                </div>
            </article>

            {/* --- FOOTER (On Paper) --- */}
            <footer className="px-12 py-8 mt-auto border-t border-slate-100 flex justify-between items-end">
                <div>
                     <div className="flex items-center gap-2 mb-2">
                         <div className="w-6 h-6 bg-slate-900 text-white flex items-center justify-center text-xs font-bold rounded">F3</div>
                         <span className="font-bold text-slate-900 text-sm">F3Next Intelligence</span>
                     </div>
                     <p className="text-[10px] text-slate-400 max-w-sm leading-tight">
                        This document contains proprietary analysis generated by the F3Next AI Engine. 
                        CONFIDENTIALITY NOTICE: The contents of this document are intended solely for the addressee.
                     </p>
                </div>
                <div className="text-right">
                    <img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=https://f3next.in" alt="QR" className="w-16 h-16 opacity-80 mix-blend-multiply mb-2 ml-auto" />
                    <p className="text-[10px] text-slate-400 uppercase tracking-widest">Verify Authenticity</p>
                </div>
            </footer>
        </div>

        {/* --- 3. EARLY ACCESS PROMPT (Below the Report) --- */}
        <div className="mt-12 mb-20 print:hidden">
             <div className="flex items-center gap-4 mb-6 px-4">
                <div className="h-px bg-slate-300 flex-grow"></div>
                <span className="text-slate-400 text-xs font-bold uppercase tracking-widest">Next Steps</span>
                <div className="h-px bg-slate-300 flex-grow"></div>
             </div>
             
             <EarlyAccess 
                annualBleed={annualBleed} 
                projectId={projectId} 
                onSuccess={() => {
                    alert("Welcome to the Private Cohort! We will be in touch shortly.");
                    router.push('/private_cohort');
                }}
            />
        </div>

      </main>
    </div>
  );
}
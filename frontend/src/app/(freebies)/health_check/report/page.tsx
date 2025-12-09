'use client';

import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useRouter } from 'next/navigation';

export default function ReportPage() {
  const router = useRouter();
  const [report, setReport] = useState<string>('');
  
  // Default state prevents "hydration mismatch" errors
  const [meta, setMeta] = useState({ 
    name: 'Valued Client', 
    company: 'Your Organization', 
    role: 'Executive', 
    date: new Date().toLocaleDateString() 
  });
  
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Retrieve Report & Metadata from LocalStorage
    const storedReport = localStorage.getItem('f3_last_report');
    const storedMeta = localStorage.getItem('f3_user_metadata');

    if (storedReport) {
      setReport(storedReport);
      
      if (storedMeta) {
        try {
          const parsed = JSON.parse(storedMeta);
          setMeta(parsed);
        } catch (e) {
          console.error("Failed to parse user metadata", e);
        }
      }
      setLoading(false);
    } else {
      setReport("## No Report Found\n\nPlease go back and complete the assessment.");
      setLoading(false);
    }
  }, []);

  const handlePrint = () => {
    window.print();
  };

  if (loading) return (
    <div className="flex items-center justify-center h-screen bg-slate-50">
      <div className="flex flex-col items-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600 mb-4"></div>
        <p className="text-gray-500 font-medium">Retrieving Analysis...</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans print:bg-white">
      
      {/* --- TOP NAVIGATION --- */}
      <nav className="bg-white border-b border-slate-200 sticky top-0 z-50 print:hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold tracking-tight text-indigo-600">F3Next</span>
              <span className="h-6 w-px bg-slate-200 mx-1"></span>
              <span className="text-sm font-medium text-slate-500 uppercase tracking-wider">Confidential Diagnosis</span>
            </div>
            <div className="flex items-center gap-4">
               <button 
                 onClick={handlePrint}
                 className="text-sm font-medium text-slate-600 hover:text-indigo-600 transition-colors flex items-center"
               >
                 <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"></path></svg>
                 Print / PDF
               </button>
               <button 
                 onClick={() => router.push('/health-check')}
                 className="text-sm font-medium text-slate-400 hover:text-slate-600"
               >
                 Close
               </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-10 px-4 sm:px-6 lg:px-8 print:py-0 print:px-0">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* --- LEFT COLUMN: The Report Document (8 cols) --- */}
          <div className="lg:col-span-8">
            
            {/* Document Header */}
            <div className="bg-white rounded-t-xl shadow-sm border border-slate-200 p-8 border-b-0 print:shadow-none print:border-none">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs font-bold text-indigo-600 uppercase tracking-widest mb-2">Prepared For</p>
                  {/* DYNAMIC COMPANY NAME */}
                  <h1 className="text-3xl font-extrabold text-slate-900">{meta.company}</h1>
                  <div className="flex items-center mt-2 text-slate-500 text-sm">
                    {/* DYNAMIC USER NAME & ROLE */}
                    <span className="font-medium text-slate-700 mr-2">{meta.name}</span>
                    <span>•</span>
                    <span className="ml-2">{meta.role}</span>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Date</p>
                  <p className="text-sm font-medium text-slate-700">{meta.date}</p>
                  <div className="mt-2 inline-flex items-center px-3 py-1 rounded-full bg-red-50 border border-red-100 text-red-700 text-xs font-bold uppercase tracking-wide">
                    <span className="w-2 h-2 bg-red-500 rounded-full mr-2 animate-pulse"></span>
                    Critical Attention
                  </div>
                </div>
              </div>
            </div>

            {/* Markdown Content Area */}
            <div className="bg-white rounded-b-xl shadow-lg border border-slate-200 p-10 min-h-[600px] print:shadow-none print:border-none print:p-0">
              <article className="prose prose-slate max-w-none prose-headings:font-bold prose-headings:text-slate-900 prose-p:text-slate-600 prose-p:leading-relaxed prose-strong:text-indigo-700 prose-strong:font-bold prose-li:text-slate-600">
                <ReactMarkdown
                  components={{
                    h1: ({node, ...props}) => <h1 className="text-2xl border-b pb-4 mb-6" {...props} />,
                    h2: ({node, ...props}) => (
                      <div className="mt-10 mb-4 flex items-center">
                        <span className="bg-indigo-100 text-indigo-600 w-8 h-8 rounded-lg flex items-center justify-center mr-3 text-lg font-bold">#</span>
                        <h2 className="text-xl m-0" {...props} />
                      </div>
                    ),
                    ul: ({node, ...props}) => <ul className="bg-slate-50 p-6 rounded-lg border border-slate-100 list-none space-y-4 my-6" {...props} />,
                    li: ({node, ...props}) => (
                      <li className="flex items-start pl-0" {...props}>
                        <svg className="w-5 h-5 text-indigo-500 mr-3 mt-1 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        <span className="flex-1">{props.children}</span>
                      </li>
                    ),
                    p: ({node, ...props}) => <p className="mb-4 text-base" {...props} />,
                    strong: ({node, ...props}) => <strong className="bg-yellow-50 text-yellow-800 px-1 py-0.5 rounded border border-yellow-100 font-semibold" {...props} />
                  }}
                >
                  {report}
                </ReactMarkdown>
              </article>

              {/* Signature Footer */}
              <div className="mt-16 pt-8 border-t border-slate-100 flex items-center justify-between opacity-60">
                <div className="flex items-center">
                   <div className="w-8 h-8 bg-slate-200 rounded-full flex items-center justify-center text-xs font-bold text-slate-500">AI</div>
                   <span className="ml-3 text-sm text-slate-400">Generated by F3Next Intelligence Engine v1.0</span>
                </div>
                <div className="h-8 w-24 bg-slate-100 rounded"></div> 
              </div>
            </div>
          </div>

          {/* --- RIGHT COLUMN: Sticky Sidebar Actions (4 cols) --- */}
          <div className="lg:col-span-4 space-y-6 print:hidden">
            
            {/* The "Fix It" Card */}
            <div className="bg-indigo-600 rounded-xl shadow-xl p-6 text-white transform transition hover:scale-[1.02] duration-200 cursor-pointer">
              <h3 className="text-lg font-bold mb-2">Ready to fix this?</h3>
              <p className="text-indigo-100 text-sm mb-6">
                Based on this audit, your factory is losing money daily. Deploy your F3 instance now.
              </p>
              <button 
                onClick={() => router.push('/pricing')}
                className="w-full bg-white text-indigo-600 font-bold py-3 px-4 rounded-lg shadow-sm hover:bg-indigo-50 transition-colors flex justify-center items-center"
              >
                Deploy Solution
                <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path></svg>
              </button>
            </div>

            {/* UPDATED: Executive Summary Card */}
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide mb-4 border-b border-slate-100 pb-2">Audit Summary</h3>
              
              <div className="space-y-4">
                {/* 1. User Name */}
                <div>
                  <p className="text-xs text-slate-500">Prepared For</p>
                  <p className="font-semibold text-slate-900">{meta.name}</p>
                </div>

                {/* 2. Role */}
                <div>
                  <p className="text-xs text-slate-500">Role</p>
                  <p className="font-semibold text-slate-900">{meta.role}</p>
                </div>

                {/* 3. Company Name */}
                <div>
                  <p className="text-xs text-slate-500">Organization</p>
                  <p className="font-semibold text-slate-900">{meta.company}</p>
                </div>

                {/* 4. Risk (Static for now, dynamic later) */}
                <div>
                  <p className="text-xs text-slate-500">Primary Risk</p>
                  <p className="text-sm font-bold text-red-600">Financial Leakage</p>
                </div>
              </div>
            </div>

            {/* Trust Signal */}
            <div className="text-center">
              <p className="text-xs text-slate-400">
                <span className="inline-block w-2 h-2 bg-green-400 rounded-full mr-1"></span>
                Securely encrypted & private.
              </p>
            </div>

          </div>
        </div>
      </main>
    </div>
  );
}
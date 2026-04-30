'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { createClient } from '@/utils/supabase/client';
import QuestionsList, { QUESTIONS_DATA } from './questions';
import { ChevronRight, FileBarChart, Loader2, ArrowRight } from 'lucide-react';
import { getBaseApiUrl } from '@/lib/config';

export const dynamic = "force-dynamic";

function HealthCheckContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const supabase = createClient();
  
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);

  const [formData, setFormData] = useState({
    fullName: '',
    companyName: '',
    role: ''
  });

  useEffect(() => {
    const savedAnswers = localStorage.getItem('f3_temp_answers');
    if (savedAnswers) {
      setAnswers(JSON.parse(savedAnswers));
    }

    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session?.user && savedAnswers && searchParams.get('return') === 'true') {
        setShowModal(true);
      }
    });

    return () => {
      subscription?.unsubscribe();
    };
  }, [searchParams, supabase]);

  const handleSelect = (key: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [key]: value }));
  };

  const handleAnalyzeClick = () => {
    if (Object.keys(answers).length < QUESTIONS_DATA.length) {
      alert("Please answer all 10 questions to get an accurate diagnosis.");
      return;
    }

    if (!user) {
      localStorage.setItem('f3_temp_answers', JSON.stringify(answers));
      router.push('/login?redirect=/health_check'); 
    } else {
      setShowModal(true);
    }
  };

  const handleFinalSubmit = async () => {
    if (!user) return;
    setLoading(true);

    const payload = {
      supabase_uid: user.id,
      user_email: user.email || "",
      full_name: formData.fullName,
      company_name: formData.companyName,
      role: formData.role,
      answers: answers
    };

    try {
      const apiUrl = getBaseApiUrl();
      const response = await fetch(`${apiUrl}/health_check/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const data = await response.json();
        
        localStorage.setItem('f3_last_report', data.report);
        localStorage.setItem('f3_project_id', data.project_id);
        
        if (data.user_meta) {
            const metaToSave = {
                name: data.user_meta.name,
                company: data.user_meta.company,
                role: data.user_meta.role,
                date: new Date().toLocaleDateString()
            };
            localStorage.setItem('f3_user_metadata', JSON.stringify(metaToSave));

            if (data.annual_bleed) {
              localStorage.setItem('f3_annual_bleed', data.annual_bleed);
            }
        } else {
             const fallbackMeta = {
                name: formData.fullName,
                company: formData.companyName,
                role: formData.role,
                date: new Date().toLocaleDateString()
            };
            localStorage.setItem('f3_user_metadata', JSON.stringify(fallbackMeta));
        }
        
        localStorage.removeItem('f3_temp_answers');
        router.push('/health_check/report');
      } else {
        const err = await response.json();
        alert(`Submission Failed: ${err.detail || "Unknown Error"}`);
      }
    } catch (error) {
      console.error(error);
      alert("Network Error: Is Backend running?");
    } finally {
      setLoading(false);
    }
  };

  const progress = Math.round((Object.keys(answers).length / QUESTIONS_DATA.length) * 100);

  return (
    <div className="min-h-screen bg-[var(--bg-void)] font-sans text-[var(--text-primary)] fade-in-up">
      
      {/* Sub-header with progress */}
      <div className="border-b border-[var(--border-subtle)] bg-[var(--bg-shell)] sticky top-0 z-30">
        <div className="max-w-4xl mx-auto px-4 h-12 flex items-center justify-between">
           <div className="flex items-center gap-3">
             <div className="bg-amber-500/15 border border-amber-500/25 p-1.5 rounded-lg">
                <FileBarChart className="w-3.5 h-3.5 text-amber-400" />
             </div>
             <span className="font-bold text-sm text-zinc-300 tracking-tight">Diagnostic Mode</span>
           </div>
           <div className="text-xs font-medium text-zinc-600">
             {Object.keys(answers).length} / {QUESTIONS_DATA.length} Answered
           </div>
        </div>
        <div className="h-0.5 w-full bg-[var(--bg-card)]">
            <div 
              className="h-full bg-amber-500 transition-all duration-500 ease-out shadow-[0_0_8px_rgba(245,158,11,0.3)]" 
              style={{ width: `${progress}%` }}
            ></div>
        </div>
      </div>

      <main className="max-w-3xl mx-auto px-4 py-10 pb-32">
        
        <div className="text-center mb-10">
            <h1 className="text-2xl font-bold text-white mb-3">Factory Operations Audit</h1>
            <p className="text-zinc-500 text-sm max-w-lg mx-auto leading-relaxed">
                Select the option that best describes your current process. 
                Be honest — accuracy is key for a valid forensic report.
            </p>
        </div>

        <div className="space-y-6">
            <QuestionsList answers={answers} handleSelect={handleSelect} />
        </div>

        {/* Fixed bottom bar */}
        <div className="fixed bottom-0 left-0 w-full bg-[var(--bg-shell)] border-t border-[var(--border-subtle)] p-4 z-20 backdrop-blur-md">
            <div className="max-w-3xl mx-auto flex justify-between items-center">
                <div className="text-xs text-zinc-600 hidden sm:block">
                    {progress === 100 ? "Ready to analyze" : "Complete all questions"}
                </div>
                <button
                    onClick={handleAnalyzeClick}
                    disabled={Object.keys(answers).length < QUESTIONS_DATA.length}
                    className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all transform active:scale-95
                    ${Object.keys(answers).length < QUESTIONS_DATA.length 
                        ? 'bg-[var(--bg-card)] text-zinc-600 cursor-not-allowed border border-[var(--border-subtle)]' 
                        : 'bg-amber-500 text-black hover:bg-amber-400 shadow-lg shadow-amber-500/10'}`}
                >
                    Generate Report <ArrowRight className="w-4 h-4" />
                </button>
            </div>
        </div>

      </main>

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="surface-card max-w-md w-full overflow-hidden fade-in-up" style={{ borderRadius: 'var(--radius-xl)' }}>
            
            {/* Modal header */}
            <div className="bg-amber-500 p-6 text-center">
                <FileBarChart className="w-8 h-8 mx-auto mb-2 text-amber-900" />
                <h2 className="text-lg font-bold text-black">Analysis Complete</h2>
                <p className="text-amber-900/80 text-sm">We&apos;ve identified key bottlenecks. Who should we address this report to?</p>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1.5">Full Name</label>
                <input 
                  type="text"
                  placeholder="e.g. Parth Patel"
                  autoFocus
                  className="w-full border border-[var(--border-default)] rounded-xl p-3 focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500/40 outline-none text-zinc-200 bg-[var(--bg-void)] text-sm transition-all"
                  value={formData.fullName}
                  onChange={(e) => setFormData({...formData, fullName: e.target.value})}
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1.5">Company Name</label>
                <input 
                  type="text"
                  placeholder="e.g. Cleaneasy Engineers"
                  className="w-full border border-[var(--border-default)] rounded-xl p-3 focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500/40 outline-none text-zinc-200 bg-[var(--bg-void)] text-sm transition-all"
                  value={formData.companyName}
                  onChange={(e) => setFormData({...formData, companyName: e.target.value})}
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-wider mb-1.5">Your Role</label>
                <select 
                  className="w-full border border-[var(--border-default)] rounded-xl p-3 bg-[var(--bg-void)] focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500/40 outline-none text-zinc-200 text-sm transition-all"
                  value={formData.role}
                  onChange={(e) => setFormData({...formData, role: e.target.value})}
                >
                  <option value="">Select Role...</option>
                  <option value="Owner/Founder">Owner / Founder</option>
                  <option value="Plant Head">Plant Head / Manager</option>
                  <option value="Operations">Operations Manager</option>
                  <option value="Finance">Finance / Accounts</option>
                  <option value="IT/Tech">IT / Tech Lead</option>
                </select>
              </div>

              <div className="pt-3">
                <button 
                    onClick={handleFinalSubmit}
                    disabled={loading || !formData.fullName || !formData.companyName || !formData.role}
                    className="w-full py-3 bg-amber-500 text-black font-bold rounded-xl hover:bg-amber-400 transition-all shadow-lg shadow-amber-500/10 flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed text-sm"
                >
                    {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin"/> Processing...</> : "View Forensic Report"}
                </button>
                <button 
                   onClick={() => setShowModal(false)}
                   className="mt-3 w-full text-center text-xs text-zinc-600 hover:text-zinc-400 transition-colors"
                >
                  Go Back
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function HealthCheckPage() {
  return (
    <Suspense fallback={
        <div className="min-h-[60vh] flex flex-col items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin mb-3 text-amber-500" />
            <span className="font-medium text-zinc-600 text-sm">Initializing Audit Engine...</span>
        </div>
    }>
      <HealthCheckContent />
    </Suspense>
  );
}
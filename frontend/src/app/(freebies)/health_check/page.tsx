'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { auth } from '@/lib/firebase'; 
import { onAuthStateChanged, User } from 'firebase/auth';
import QuestionsList, { QUESTIONS_DATA } from './questions';
import { ChevronRight, FileBarChart, Loader2, ArrowRight } from 'lucide-react';

export const dynamic = "force-dynamic";

function HealthCheckContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [user, setUser] = useState<User | null>(null);
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

    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      if (currentUser && savedAnswers && searchParams.get('return') === 'true') {
        setShowModal(true);
      }
    });

    return () => unsubscribe();
  }, [searchParams]);

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
      firebase_uid: user.uid,
      user_email: user.email || "",
      full_name: formData.fullName,
      company_name: formData.companyName,
      role: formData.role,
      answers: answers
    };

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_AWS_APP_RUNNER_URL}/health_check/submit`, {
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
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
      
      {/* --- HEADER --- */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-4xl mx-auto px-4 h-16 flex items-center justify-between">
           <div className="flex items-center gap-3">
             <div className="bg-indigo-600 p-1.5 rounded text-white">
                <FileBarChart className="w-4 h-4" />
             </div>
             <span className="font-bold text-slate-800 tracking-tight">Diagnostic Mode</span>
           </div>
           <div className="text-sm font-medium text-slate-500">
             {Object.keys(answers).length} / {QUESTIONS_DATA.length} Answered
           </div>
        </div>
        {/* Progress Bar */}
        <div className="h-1 w-full bg-slate-100">
            <div 
              className="h-full bg-indigo-600 transition-all duration-500 ease-out shadow-[0_0_10px_rgba(79,70,229,0.5)]" 
              style={{ width: `${progress}%` }}
            ></div>
        </div>
      </header>

      {/* --- MAIN CONTENT --- */}
      <main className="max-w-3xl mx-auto px-4 py-12 pb-32">
        
        <div className="text-center mb-12">
            <h1 className="text-3xl font-bold text-slate-900 mb-3">Factory Operations Audit</h1>
            <p className="text-slate-500 max-w-lg mx-auto">
                Select the option that best describes your current process. 
                Be honest—accuracy is key for a valid forensic report.
            </p>
        </div>

        {/* Questions List Component (Ensure this component is also styled well, usually passed as props or styled internally) */}
        <div className="space-y-6">
            <QuestionsList answers={answers} handleSelect={handleSelect} />
        </div>

        {/* --- BOTTOM ACTION BAR --- */}
        <div className="fixed bottom-0 left-0 w-full bg-white border-t border-slate-200 p-4 z-20 shadow-[-10px_0_30px_rgba(0,0,0,0.05)]">
            <div className="max-w-3xl mx-auto flex justify-between items-center">
                <div className="text-xs text-slate-400 hidden sm:block">
                    {progress === 100 ? "Ready to analyze" : "Complete all questions"}
                </div>
                <button
                    onClick={handleAnalyzeClick}
                    disabled={Object.keys(answers).length < QUESTIONS_DATA.length}
                    className={`flex items-center gap-2 px-8 py-3 rounded-lg font-bold transition-all transform active:scale-95
                    ${Object.keys(answers).length < QUESTIONS_DATA.length 
                        ? 'bg-slate-100 text-slate-400 cursor-not-allowed' 
                        : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-lg shadow-indigo-200'}`}
                >
                    Generate Report <ArrowRight className="w-4 h-4" />
                </button>
            </div>
        </div>

      </main>

      {/* --- MODAL --- */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full overflow-hidden animate-in zoom-in-95 duration-200">
            
            <div className="bg-indigo-600 p-6 text-white text-center">
                <FileBarChart className="w-10 h-10 mx-auto mb-3 text-indigo-200" />
                <h2 className="text-xl font-bold">Analysis Complete</h2>
                <p className="text-indigo-100 text-sm opacity-90">We've identified key bottlenecks. Who should we address this report to?</p>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Full Name</label>
                <input 
                  type="text"
                  placeholder="e.g. Parth Patel"
                  autoFocus
                  className="w-full border border-slate-200 rounded-lg p-3 focus:ring-2 focus:ring-indigo-500 outline-none text-slate-900 bg-slate-50"
                  value={formData.fullName}
                  onChange={(e) => setFormData({...formData, fullName: e.target.value})}
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Company Name</label>
                <input 
                  type="text"
                  placeholder="e.g. Cleaneasy Engineers"
                  className="w-full border border-slate-200 rounded-lg p-3 focus:ring-2 focus:ring-indigo-500 outline-none text-slate-900 bg-slate-50"
                  value={formData.companyName}
                  onChange={(e) => setFormData({...formData, companyName: e.target.value})}
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Your Role</label>
                <select 
                  className="w-full border border-slate-200 rounded-lg p-3 bg-slate-50 focus:ring-2 focus:ring-indigo-500 outline-none text-slate-900"
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

              <div className="pt-4">
                <button 
                    onClick={handleFinalSubmit}
                    disabled={loading || !formData.fullName || !formData.companyName || !formData.role}
                    className="w-full py-3.5 bg-indigo-600 text-white font-bold rounded-lg hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100 flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {loading ? <><Loader2 className="w-5 h-5 mr-2 animate-spin"/> Processing...</> : "View Forensic Report"}
                </button>
                <button 
                   onClick={() => setShowModal(false)}
                   className="mt-3 w-full text-center text-sm text-slate-400 hover:text-slate-600"
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
        <div className="min-h-screen flex flex-col items-center justify-center bg-white text-indigo-600">
            <Loader2 className="w-8 h-8 animate-spin mb-4" />
            <span className="font-medium text-slate-500">Initializing Audit Engine...</span>
        </div>
    }>
      <HealthCheckContent />
    </Suspense>
  );
}
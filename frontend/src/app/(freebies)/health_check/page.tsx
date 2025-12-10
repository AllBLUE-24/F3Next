'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { auth } from '@/lib/firebase'; 
import { onAuthStateChanged, User } from 'firebase/auth';

import QuestionsList, { QUESTIONS_DATA } from './questions';

export default function HealthCheckPage() {
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
      router.push('/login?redirect=/health_check'); // <--- Updated to underscore
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
      const response = await fetch('http://127.0.0.1:8000/health_check/submit', {
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
        router.push('/health_check/report'); // <--- Updated to underscore
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
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-extrabold text-gray-900">Factory Health Check</h1>
          <p className="mt-2 text-gray-600">
            {Object.keys(answers).length}/{QUESTIONS_DATA.length} Questions Answered
          </p>
        </div>

        <div className="sticky top-0 z-10 bg-gray-50 pt-2 pb-6">
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div 
              className="bg-indigo-600 h-2.5 rounded-full transition-all duration-300 ease-out" 
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>

        <QuestionsList answers={answers} handleSelect={handleSelect} />

        <div className="mt-10 flex justify-end pb-20">
          <button
            onClick={handleAnalyzeClick}
            className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-4 px-8 rounded-lg shadow-lg text-lg transition-transform transform hover:scale-105"
          >
            Generate Forensic Report &rarr;
          </button>
        </div>
      </div>

      {/* --- MODAL --- */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 animate-fadeIn">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Almost Done!</h2>
            <p className="text-gray-500 mb-6">
              To generate a personalized report for your factory, we need a few details.
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                <input 
                  type="text"
                  placeholder="e.g. Parth Patel"
                  /* 🔴 FIX: Added text-gray-900 bg-white */
                  className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 text-gray-900 bg-white"
                  value={formData.fullName}
                  onChange={(e) => setFormData({...formData, fullName: e.target.value})}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Company / Factory Name</label>
                <input 
                  type="text"
                  placeholder="e.g. Cleaneasy engineers"
                  /* 🔴 FIX: Added text-gray-900 bg-white */
                  className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 text-gray-900 bg-white"
                  value={formData.companyName}
                  onChange={(e) => setFormData({...formData, companyName: e.target.value})}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Your Role</label>
                <select 
                  /* 🔴 FIX: Added text-gray-900 bg-white */
                  className="w-full border border-gray-300 rounded-lg p-2.5 bg-white focus:ring-2 focus:ring-indigo-500 text-gray-900"
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
            </div>

            <div className="mt-8">
              <button 
                onClick={handleFinalSubmit}
                disabled={loading || !formData.fullName || !formData.companyName || !formData.role}
                className={`w-full py-3 rounded-lg font-bold text-white text-lg shadow-md transition-colors 
                  ${(loading || !formData.fullName) ? 'bg-indigo-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'}`}
              >
                {loading ? "Analyzing..." : "Get My Analysis"}
              </button>
            </div>
            
            <button 
               onClick={() => setShowModal(false)}
               className="mt-4 w-full text-center text-sm text-gray-500 hover:text-gray-700"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { auth } from '@/lib/firebase'; 
import { onAuthStateChanged, User } from 'firebase/auth';

// --- DATA: The 10 Questions ---
const questions = [
  {
    key: 'q1_business_model', // Keys match your DB expectation if needed, or just business_model
    question: '1. What is your exact business model?',
    options: [
      'Make-to-Order (Job Work / Custom fabrication)',
      'Make-to-Stock (Own Brand / Standard Products)',
      'Assembly Only (Buying parts, assembling)',
      'Trading & Distribution',
    ],
  },
  {
    key: 'q2_annual_turnover',
    question: '2. What is your approximate Annual Turnover?',
    options: ['₹50L - ₹2 Cr', '₹2 Cr - ₹10 Cr', '₹10 Cr - ₹50 Cr', '₹50 Cr+'],
  },
  {
    key: 'q3_cost_calculation_method',
    question: '3. How do you calculate the "Final Cost" of your product?',
    options: [
      'Mental Math (Rough estimate based on material)',
      'Excel Sheet (Updated sometimes)',
      'Tally (Purchase cost only)',
      'ERP / Real-time (Automated)',
    ],
  },
  {
    key: 'q4_inventory_value',
    question: '4. What is the approximate value of Inventory sitting in your factory right now?',
    options: [
      '< ₹10 Lakhs',
      '₹10 Lakhs - ₹50 Lakhs',
      '₹50 Lakhs - ₹2 Crores',
      'I honestly don\'t know (No live record)',
    ],
  },
  {
    key: 'q5_bom_management',
    question: '5. How do you handle "Bill of Materials" (BOM)?',
    options: [
      'We don\'t have formal BOMs',
      'We have Excel BOMs, but production often changes',
      'We use strict BOMs with revisions',
    ],
  },
  {
    key: 'q6_line_stoppages_freq',
    question: '6. How often do you face "Line Stoppages" because a material was missing?',
    options: ['Never', 'Once or twice a month', 'Weekly occurrence'],
  },
  {
    key: 'q7_invoice_vs_payment_tracking',
    question: '7. Who creates the Invoices vs. Who tracks the Payment?',
    options: [
      'I do both (Owner)',
      'Accountant does both',
      'Sales team invoices, Accounts team tracks',
    ],
  },
  {
    key: 'q8_return_rate',
    question: '8. How many "Returns" or "Rejections" do you get from customers?',
    options: ['< 1% (Rare)', '2-5% (Manageable)', '> 5% (Serious issue)'],
  },
  {
    key: 'q9_store_manager_dependency',
    question: '9. If your Store Manager leaves tomorrow, what happens?',
    options: [
      'Nothing, data is in the system',
      'Minor headache, but we have Excel backups',
      'Disaster. He knows where everything is kept',
    ],
  },
  {
    key: 'q10_dream_fix',
    question: '10. What is your "Dream Fix"?',
    options: [
      'I want to know my stock levels on my phone',
      'I want to stop leakage/theft',
      'I want accurate production costing',
      'I want to reduce manual data entry',
    ],
  },
];

export default function HealthCheckPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // State
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);

  // Form Data State
  const [formData, setFormData] = useState({
    fullName: '',
    companyName: '',
    role: ''
  });

  // 1. Initialize: Check Auth & Restore Answers
  useEffect(() => {
    // A. Check if we saved answers before login
    const savedAnswers = localStorage.getItem('f3_temp_answers');
    if (savedAnswers) {
      setAnswers(JSON.parse(savedAnswers));
    }

    // B. Check Auth Status
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      
      // If user just came back from login AND has answers, auto-open modal
      if (currentUser && savedAnswers && searchParams.get('return') === 'true') {
        setShowModal(true);
      }
    });

    return () => unsubscribe();
  }, [searchParams]);

  // Handle Radio Selection
  const handleSelect = (key: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [key]: value }));
  };

  // 2. The "Analyze" Button Click
  const handleAnalyzeClick = () => {
    // Basic Validation
    if (Object.keys(answers).length < questions.length) {
      alert("Please answer all 10 questions to get an accurate diagnosis.");
      return;
    }

    if (!user) {
      // FLOW: Not Logged In -> Save Data -> Go to Login
      localStorage.setItem('f3_temp_answers', JSON.stringify(answers));
      // Redirect to login with a return flag
      router.push('/login?redirect=/health_check?return=true'); 
    } else {
      // FLOW: Logged In -> Open Details Modal
      setShowModal(true);
    }
  };

  // 3. Final Submit to Backend
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
      // ⚠️ Make sure this matches your Backend URL
      const response = await fetch('http://localhost:8000/health_check/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const data = await response.json();
        
        // Save the Report & Project ID for the next page
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
      } else {
          // Fallback: If backend didn't send it, use what we have in the form
          const fallbackMeta = {
              name: formData.fullName,
              company: formData.companyName,
              role: formData.role,
              date: new Date().toLocaleDateString()
          };
          localStorage.setItem('f3_user_metadata', JSON.stringify(fallbackMeta));
      }

        // Clear temp data
        localStorage.removeItem('f3_temp_answers');

        // Go to Report Page
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

  // Calculate Progress
  const progress = Math.round((Object.keys(answers).length / questions.length) * 100);

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-3xl mx-auto">
        
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-extrabold text-gray-900">Factory Health Check</h1>
          <p className="mt-2 text-gray-600">
            {Object.keys(answers).length}/{questions.length} Questions Answered
          </p>
        </div>

        {/* Sticky Progress Bar */}
        <div className="sticky top-0 z-10 bg-gray-50 pt-2 pb-6">
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div 
              className="bg-indigo-600 h-2.5 rounded-full transition-all duration-300 ease-out" 
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>

        {/* Questions List */}
        <div className="space-y-6">
          {questions.map((q) => (
            <div key={q.key} className="bg-white shadow-sm rounded-lg p-6 border border-gray-100">
              <h3 className="text-lg font-medium text-gray-900 mb-4">{q.question}</h3>
              <div className="space-y-2">
                {q.options.map((option) => (
                  <label
                    key={option}
                    className={`flex items-center p-3 rounded-md cursor-pointer border transition-colors ${
                      answers[q.key] === option
                        ? 'bg-indigo-50 border-indigo-500 ring-1 ring-indigo-500'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name={q.key}
                      value={option}
                      checked={answers[q.key] === option}
                      onChange={() => handleSelect(q.key, option)}
                      className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                    />
                    <span className="ml-3 block text-sm font-medium text-gray-700">
                      {option}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Action Button */}
        <div className="mt-10 flex justify-end pb-20">
          <button
            onClick={handleAnalyzeClick}
            className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-4 px-8 rounded-lg shadow-lg text-lg transition-transform transform hover:scale-105"
          >
            Generate Forensic Report &rarr;
          </button>
        </div>
      </div>

      {/* --- MODAL: User Details --- */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 animate-fadeIn">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Almost Done!</h2>
            <p className="text-gray-500 mb-6">
              To generate a personalized report for your factory, we need a few details.
            </p>

            <div className="space-y-4">
              {/* Full Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
                <input 
                  type="text"
                  placeholder="e.g. Parth Patel"
                  className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  value={formData.fullName}
                  onChange={(e) => setFormData({...formData, fullName: e.target.value})}
                />
              </div>

              {/* Company Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Company / Factory Name</label>
                <input 
                  type="text"
                  placeholder="e.g. AllBLUE Manufacturing"
                  className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  value={formData.companyName}
                  onChange={(e) => setFormData({...formData, companyName: e.target.value})}
                />
              </div>

              {/* Role */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Your Role</label>
                <select 
                  className="w-full border border-gray-300 rounded-lg p-2.5 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
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
                {loading ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Analyzing with AI...
                  </span>
                ) : "Get My Analysis"}
              </button>
            </div>
            
            <p className="text-xs text-center text-gray-400 mt-4">
              Your data is secure and used only to generate this report.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
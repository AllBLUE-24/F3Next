'use client';

import React, { useState } from 'react';

interface EarlyAccessProps {
  annualBleed: string;
  projectId: string | null;
  onSuccess: () => void;
}

export default function EarlyAccess({ annualBleed, projectId, onSuccess }: EarlyAccessProps) {
  const [showModal, setShowModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    phone: '',
    whatsapp: '',
    failureReason: '',
    comment: ''
  });

  const handleSecureSpot = async () => {
    if (!projectId) return;
    try {
const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      fetch(`${apiUrl}/health_check/capture-interest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, status: 'interested' })
      });
    } catch (e) { console.error(e); }
    setShowModal(true);
  };

  const handleFinalListMe = async () => {
    if (!projectId) return;
    setIsSubmitting(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/health_check/capture-interest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          status: 'listed',
          phone: formData.phone,
          whatsapp: formData.whatsapp,
          failure_reason: formData.failureReason,
          comment: formData.comment
        })
      });

      if (response.ok) {
        onSuccess();
      } else {
        alert("Please try again.");
      }
    } catch (e) {
      alert("Network Error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      {/* --- THE OFFER SECTION (Alive & Hoverable) --- */}
      <div className="mt-16 group relative overflow-hidden rounded-2xl shadow-2xl bg-gradient-to-br from-[#0f172a] to-[#1e1b4b] text-white border border-indigo-900/50 transition-all duration-500 hover:-translate-y-2 hover:shadow-indigo-900/20">
        
        {/* Alive Background Gradients */}
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-indigo-600 rounded-full blur-[150px] opacity-20 -mr-40 -mt-40 pointer-events-none group-hover:opacity-30 transition-opacity duration-700"></div>
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-purple-600 rounded-full blur-[150px] opacity-10 -ml-20 -mb-20 pointer-events-none group-hover:opacity-20 transition-opacity duration-700"></div>

        <div className="relative z-10 p-10 md:p-16">
            
            {/* 1. Headline */}
            <div className="text-center max-w-3xl mx-auto mb-16">
                <div className="inline-block bg-indigo-500/20 border border-indigo-400/30 rounded-full px-4 py-1.5 text-xs font-bold text-indigo-200 uppercase tracking-widest mb-6 shadow-lg shadow-indigo-900/50">
                    Private Founders Cohort
                </div>
                <h2 className="text-4xl md:text-5xl font-bold mb-6 tracking-tight leading-tight drop-shadow-xl">
                    Stop the <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-400 to-orange-400">₹{annualBleed}</span> Leakage.
                </h2>
                <p className="text-lg text-indigo-200/80 leading-relaxed">
                    Based on your audit, your factory is bleeding capital daily. 
                    Most ERPs take 6 months to deploy. We deploy your custom instance in <strong>under 48 hours</strong>.
                </p>
            </div>

            {/* 2. The Comparison Table */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
                
                {/* Traditional ERP */}
                <div className="bg-white/5 border border-white/10 rounded-xl p-8 backdrop-blur-sm transition-colors hover:bg-white/10">
                    <h3 className="text-slate-400 font-bold uppercase tracking-wider text-sm mb-6 border-b border-white/10 pb-2">Traditional ERPs</h3>
                    <ul className="space-y-4 text-slate-300">
                        <li className="flex items-center gap-3">
                            <span className="text-red-500 text-xl font-bold">✕</span> High Upfront Cost (₹5L+)
                        </li>
                        <li className="flex items-center gap-3">
                            <span className="text-red-500 text-xl font-bold">✕</span> 3-6 Months Implementation
                        </li>
                        <li className="flex items-center gap-3">
                            <span className="text-red-500 text-xl font-bold">✕</span> Expensive AMC (Yearly Fees)
                        </li>
                    </ul>
                </div>

                {/* F3Next */}
                <div className="bg-gradient-to-b from-indigo-600/30 to-indigo-900/10 border border-indigo-500/50 rounded-xl p-8 relative overflow-hidden shadow-xl shadow-indigo-900/30 transform transition hover:scale-[1.02] duration-300">
                    <div className="absolute top-0 right-0 bg-indigo-500 text-white text-[10px] font-bold px-3 py-1 rounded-bl-lg shadow-md">EARLY BIRD</div>
                    <h3 className="text-white font-bold uppercase tracking-wider text-sm mb-6 border-b border-indigo-500/30 pb-2">F3Next Early Access</h3>
                    <ul className="space-y-4 text-white font-medium">
                        <li className="flex items-center gap-3">
                            <span className="text-green-400 text-xl font-bold">✓</span> <span className="text-green-300">Zero</span> Upfront Cost
                        </li>
                        <li className="flex items-center gap-3">
                            <span className="text-green-400 text-xl font-bold">✓</span> <span className="text-white border-b border-indigo-400/50"> {"<"} 48-Hour</span> Deployment
                        </li>
                        <li className="flex items-center gap-3">
                            <span className="text-green-400 text-xl font-bold">✓</span> Just <strong>₹4,999/mo</strong> (Locked for Life)
                        </li>
                    </ul>
                </div>
            </div>

            {/* 3. CTA */}
            <div className="mt-16 text-center">
                <button 
                    onClick={handleSecureSpot}
                    className="group relative inline-flex items-center justify-center px-10 py-5 font-bold text-white transition-all duration-300 bg-indigo-600 text-lg rounded-full hover:bg-indigo-500 hover:shadow-[0_0_40px_rgba(99,102,241,0.5)] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-600 transform active:scale-95"
                >
                    Secure My Spot for ₹4,999/mo
                    <svg className="w-5 h-5 ml-3 -mr-1 transition-transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7l5 5m0 0l-5 5m5-5H6"></path></svg>
                </button>
                <p className="mt-4 text-sm text-indigo-300/60 animate-pulse">
                    No credit card required. Cancel anytime.
                </p>
            </div>

        </div>
      </div>

      {/* --- THE MODAL (Refined Text) --- */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-900/90 backdrop-blur-md flex items-center justify-center p-4 z-50 animate-in fade-in zoom-in duration-300">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden border border-slate-200">
            
            <div className="bg-gradient-to-r from-indigo-600 to-indigo-700 p-6 text-center relative">
                <button onClick={() => setShowModal(false)} className="absolute top-4 right-4 text-indigo-200 hover:text-white transition-colors text-xl">✕</button>
                <div className="w-12 h-12 bg-white text-indigo-600 rounded-full flex items-center justify-center mx-auto mb-3 text-xl font-bold shadow-lg">🚀</div>
                <h3 className="text-xl font-bold text-white">Almost There...</h3>
                <p className="text-indigo-100 text-sm opacity-90">Complete these details to lock your ₹4,999 pricing.</p>
            </div>

            <div className="p-8 space-y-5">
                {/* Silver Bullet */}
                <div>
                    <label className="block text-sm font-bold text-slate-700 mb-2">
                        What feature failed you in other software? <span className="text-red-500">*</span>
                    </label>
                    <textarea 
                        className="w-full p-3 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-slate-900 placeholder:text-slate-400 text-sm min-h-[80px]"
                        placeholder="e.g. Tally couldn't track batch numbers..."
                        value={formData.failureReason}
                        onChange={e => setFormData({...formData, failureReason: e.target.value})}
                    ></textarea>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Phone <span className="text-red-500">*</span></label>
                        <input 
                            type="tel" 
                            className="w-full p-3 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-slate-900"
                            placeholder="+91..."
                            value={formData.phone}
                            onChange={e => setFormData({...formData, phone: e.target.value})}
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-bold text-slate-500 uppercase mb-1">WhatsApp <span className="text-red-500">*</span></label>
                        <input 
                            type="tel" 
                            className="w-full p-3 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-slate-900"
                            placeholder="+91..."
                            value={formData.whatsapp}
                            onChange={e => setFormData({...formData, whatsapp: e.target.value})}
                        />
                    </div>
                </div>

                {/* Comment (Restored) */}
                <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Any specific requirements?</label>
                    <input 
                        type="text" 
                        className="w-full p-3 bg-slate-50 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-slate-900 placeholder:text-slate-400"
                        placeholder="Optional"
                        value={formData.comment}
                        onChange={e => setFormData({...formData, comment: e.target.value})}
                    />
                </div>

                <button 
                    onClick={handleFinalListMe}
                    disabled={!formData.phone || !formData.failureReason || isSubmitting}
                    className="w-full py-4 bg-indigo-600 text-white font-bold rounded-lg hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-200 disabled:opacity-50 disabled:cursor-not-allowed mt-2"
                >
                    {isSubmitting ? "Activating..." : "Complete Activation"}
                </button>
                <p className="text-center text-xs text-slate-400">Your data is secure. No spam.</p>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
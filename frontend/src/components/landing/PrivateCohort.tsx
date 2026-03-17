'use client';

import React, { useState } from 'react';
import { ArrowRight, Check, X, Loader2 } from 'lucide-react';

export default function PrivateCohort() {
  const [showModal, setShowModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [step, setStep] = useState<'form' | 'success'>('form');

  const [formData, setFormData] = useState({
    phone: '',
    whatsapp: '',
    failureReason: '',
    comment: '',
  });

  const projectId = 'landing-page-cohort';

  const handleFinalListMe = async () => {
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
          comment: formData.comment,
        }),
      });
      if (!response.ok) console.error('API Error');
    } catch (e) {
      console.error('Network Error', e);
    } finally {
      setIsSubmitting(false);
      setStep('success');
    }
  };

  const stats = [
    { label: 'Deployment', before: '6 Months', after: '48 Hours' },
    { label: 'Setup Cost', before: '₹5,00,000+', after: '₹0' },
    { label: 'Monthly SaaS', before: '₹25,000+', after: '₹4,999' },
    { label: 'Training Time', before: 'Weeks', after: 'None' },
  ];

  return (
    <section className="border-t border-white/[0.06] py-28 bg-[#09090B]" id="cohort">
      <div className="max-w-6xl mx-auto px-6">

        <div className="text-center mb-12">
          <span className="inline-block text-xs font-bold uppercase tracking-[0.2em] text-amber-500 mb-4">Limited Access</span>
          <h2 className="text-3xl font-bold text-white sm:text-5xl mb-4">
            Founders Cohort — Lock ₹4,999/mo for life.
          </h2>
          <p className="text-gray-500 text-lg max-w-xl mx-auto">
            First 50 manufacturers get enterprise-grade ERP at a startup price. No credit card. No catch.
          </p>
        </div>

        {/* Main Card */}
        <div className="relative overflow-hidden rounded-2xl border border-white/[0.08] bg-[#0D0D14]">

          {/* Grid bg inside card */}
          <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.015)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.015)_1px,transparent_1px)] bg-[size:30px_30px] pointer-events-none"></div>

          {/* Amber glow top-right */}
          <div className="absolute top-0 right-0 w-80 h-80 bg-amber-500/5 blur-3xl rounded-full pointer-events-none"></div>

          <div className="relative grid md:grid-cols-2 gap-0">

            {/* Left: Pitch */}
            <div className="p-10 md:p-14 flex flex-col justify-center border-b md:border-b-0 md:border-r border-white/[0.06]">
              <div className="inline-flex items-center gap-2 text-amber-400 text-xs font-mono uppercase tracking-widest mb-6">
                <span className="w-2 h-2 bg-amber-500 rounded-full animate-pulse"></span>
                Private Founders Cohort — 50 Spots
              </div>

              <h3 className="text-3xl font-black text-white mb-5 leading-tight">
                Get the full AI-ERP suite<br />
                at <span className="text-amber-500">₹4,999/month</span> — forever.
              </h3>

              <p className="text-gray-500 mb-8 leading-relaxed text-sm">
                Includes AI consultant, cloud deployment, intelligent data migration, and prompt-to-action operations. 
                Early members are grandfathered in at this rate — even as the product scales.
              </p>

              <ul className="space-y-2 mb-10">
                {[
                  'AI-powered ERP recommendation',
                  'ERPNext cloud deployment (48hr)',
                  'Intelligent data migration',
                  'Prompt-to-action ERP operations',
                  'Zero upfront cost',
                  'Direct founder support',
                ].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-sm text-gray-400">
                    <Check className="w-4 h-4 text-amber-500 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => setShowModal(true)}
                className="inline-flex items-center justify-center bg-amber-500 text-black px-7 py-3.5 rounded-xl font-bold hover:bg-amber-400 transition-colors w-fit group shadow-lg shadow-amber-500/20"
              >
                Secure My Spot
                <ArrowRight className="ml-2 w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
              <p className="text-xs text-gray-700 mt-3">No credit card required.</p>
            </div>

            {/* Right: Stats */}
            <div className="p-10 md:p-14 flex flex-col justify-center">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-gray-600 mb-8">Before & After</p>
              <div className="space-y-6">
                {stats.map((stat, i) => (
                  <div key={i} className="flex justify-between items-center pb-5 border-b border-white/[0.05] last:border-0 last:pb-0">
                    <span className="text-gray-500 text-sm">{stat.label}</span>
                    <div className="text-right">
                      <span className="block text-xs text-red-500/70 line-through mb-0.5">{stat.before}</span>
                      <span className="block text-sm font-bold text-green-400">{stat.after}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-10 pt-8 border-t border-white/[0.06]">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Spots remaining</span>
                  <span className="text-amber-400 font-bold">47 / 50</span>
                </div>
                <div className="mt-2 h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
                  <div className="h-full bg-amber-500 rounded-full" style={{ width: '94%' }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── MODAL ── */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-[#0D0D14] border border-white/[0.1] rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">

            <div className="flex justify-between items-center p-6 border-b border-white/[0.08]">
              <h3 className="font-bold text-white">
                {step === 'success' ? '🎉 Spot Secured!' : 'Secure Your Spot'}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-gray-600 hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6">
              {step === 'success' ? (
                <div className="text-center py-8">
                  <div className="w-16 h-16 bg-amber-500/10 border border-amber-500/20 rounded-full flex items-center justify-center mx-auto mb-5">
                    <Check className="w-8 h-8 text-amber-500" />
                  </div>
                  <h4 className="text-xl font-bold text-white mb-2">You're on the list.</h4>
                  <p className="text-gray-500 text-sm mb-8 leading-relaxed">
                    We've recorded your interest. Our team will reach out via WhatsApp to confirm your factory details and finalize your spot.
                  </p>
                  <button
                    onClick={() => setShowModal(false)}
                    className="w-full py-3 bg-amber-500 text-black rounded-xl font-bold hover:bg-amber-400 transition-colors"
                  >
                    Close
                  </button>
                </div>
              ) : (
                <div className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-gray-400 mb-2">
                      What's your biggest ERP pain right now? <span className="text-amber-500">*</span>
                    </label>
                    <textarea
                      autoFocus
                      className="w-full p-3.5 bg-white/[0.03] border border-white/[0.1] rounded-xl focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none text-sm text-white placeholder:text-gray-600 transition resize-none"
                      rows={3}
                      placeholder="e.g. Our ERP is too expensive, no one knows how to use it..."
                      value={formData.failureReason}
                      onChange={(e) => setFormData({ ...formData, failureReason: e.target.value })}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-400 mb-2">
                        Phone <span className="text-amber-500">*</span>
                      </label>
                      <input
                        type="tel"
                        className="w-full p-3.5 bg-white/[0.03] border border-white/[0.1] rounded-xl focus:ring-1 focus:ring-amber-500 outline-none text-sm text-white placeholder:text-gray-600"
                        placeholder="+91..."
                        value={formData.phone}
                        onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-400 mb-2">
                        WhatsApp <span className="text-amber-500">*</span>
                      </label>
                      <input
                        type="tel"
                        className="w-full p-3.5 bg-white/[0.03] border border-white/[0.1] rounded-xl focus:ring-1 focus:ring-amber-500 outline-none text-sm text-white placeholder:text-gray-600"
                        placeholder="+91..."
                        value={formData.whatsapp}
                        onChange={(e) => setFormData({ ...formData, whatsapp: e.target.value })}
                      />
                    </div>
                  </div>

                  <button
                    onClick={handleFinalListMe}
                    disabled={!formData.phone || !formData.failureReason || isSubmitting}
                    className="w-full py-3.5 bg-amber-500 text-black font-bold rounded-xl hover:bg-amber-400 transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center mt-2"
                  >
                    {isSubmitting ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      'Lock in ₹4,999/mo for Life'
                    )}
                  </button>
                  <p className="text-xs text-center text-gray-600">No credit card. No commitment.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
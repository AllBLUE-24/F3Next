'use client';

import React, { useState } from 'react';
import { ArrowRight, Check, X, Loader2 } from 'lucide-react';
import { getBaseApiUrl } from '@/lib/config';

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
      const apiUrl = getBaseApiUrl();
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

  return (
    <section className="py-28 lg:py-32 bg-[#09090B]" id="cohort">
      <div className="max-w-5xl mx-auto px-6 lg:px-8">

        {/* Section Header */}
        <div className="text-center mb-16 lg:mb-20">
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-amber-500/80 mb-4">
            Early Access
          </p>
          <h2
            className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white tracking-[-0.03em] leading-tight"
            style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
          >
            Join the early access <span className="text-amber-500">cohort</span>
          </h2>
          <p className="mt-5 text-base text-zinc-500 max-w-lg mx-auto leading-relaxed">
            Be among the first manufacturers to experience autonomous operations. Get priority onboarding and direct founder support.
          </p>
        </div>

        {/* Main Card */}
        <div className="relative overflow-hidden rounded-2xl border border-white/[0.06] bg-white/[0.01]">

          {/* Subtle top glow */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/[0.04] blur-[100px] rounded-full pointer-events-none" />

          <div className="relative grid md:grid-cols-2 gap-0">

            {/* Left: Pitch */}
            <div className="p-10 md:p-12 flex flex-col justify-center border-b md:border-b-0 md:border-r border-white/[0.04]">
              <h3
                className="text-2xl font-bold text-white mb-4 leading-tight tracking-tight"
                style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
              >
                Get your operations running<br />
                <span className="text-amber-500">before everyone else.</span>
              </h3>

              <p className="text-zinc-500 mb-8 leading-relaxed text-[14px]">
                Includes AI-powered setup, cloud deployment, intelligent data migration, and prompt-to-action operations.
              </p>

              <ul className="space-y-2.5 mb-10">
                {[
                  'AI-powered ERP recommendation',
                  'Cloud deployment in minutes',
                  'Intelligent data migration',
                  'Zero upfront cost',
                  'Direct founder support',
                ].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-[13px] text-zinc-400">
                    <Check className="w-4 h-4 text-amber-500/70 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => setShowModal(true)}
                className="group inline-flex items-center justify-center bg-amber-500 text-black px-6 py-3 rounded-xl font-semibold text-[14px] hover:bg-amber-400 transition-all duration-200 w-fit lift-hover shadow-lg shadow-amber-500/15 cursor-pointer"
              >
                Join Early Access
                <ArrowRight className="ml-2 w-4 h-4 group-hover:translate-x-0.5 transition-transform duration-200" />
              </button>
              <p className="text-[12px] text-zinc-700 mt-3">No credit card required.</p>
            </div>

            {/* Right: Comparison Table */}
            <div className="p-10 md:p-12 flex flex-col justify-center">
              <p className="text-[11px] font-medium uppercase tracking-[0.15em] text-zinc-600 mb-8">
                What changes with F3Next
              </p>
              <div className="space-y-0">
                {[
                  { label: 'Setup Time', before: '3–6 Months', after: 'Minutes' },
                  { label: 'Upfront Cost', before: '₹5,00,000+', after: '₹0' },
                  { label: 'Employee Training', before: 'Weeks', after: 'None' },
                  { label: 'ERP Operations', before: 'Trained staff', after: 'Anyone — just type' },
                ].map((stat, i) => (
                  <div key={i} className="flex justify-between items-center py-4 border-b border-white/[0.04] last:border-0">
                    <span className="text-zinc-500 text-[13px]">{stat.label}</span>
                    <div className="text-right">
                      <span className="block text-[12px] text-zinc-700 line-through mb-0.5">{stat.before}</span>
                      <span className="block text-[13px] font-medium text-emerald-400/80">{stat.after}</span>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-8 pt-6 border-t border-white/[0.04]">
                <p className="text-[12px] text-zinc-600 leading-relaxed">
                  We onboard 10 factories per cohort to maintain exceptional support quality.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── MODAL ── */}
      {showModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#111114] border border-white/[0.08] rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">

            <div className="flex justify-between items-center p-6 border-b border-white/[0.06]">
              <h3 className="font-semibold text-white text-[15px]">
                {step === 'success' ? 'You\'re on the list!' : 'Join Early Access'}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-zinc-600 hover:text-white transition-colors cursor-pointer">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6">
              {step === 'success' ? (
                <div className="text-center py-6">
                  <div className="w-14 h-14 bg-amber-500/[0.08] border border-amber-500/15 rounded-full flex items-center justify-center mx-auto mb-5">
                    <Check className="w-6 h-6 text-amber-500" />
                  </div>
                  <h4 className="text-lg font-semibold text-white mb-2">You're on the list.</h4>
                  <p className="text-zinc-500 text-[13px] mb-8 leading-relaxed">
                    We've recorded your interest. Our team will reach out via WhatsApp to get you onboarded.
                  </p>
                  <button
                    onClick={() => setShowModal(false)}
                    className="w-full py-3 bg-amber-500 text-black rounded-xl font-semibold text-[13px] hover:bg-amber-400 transition-colors cursor-pointer"
                  >
                    Close
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <label className="block text-[13px] font-medium text-zinc-400 mb-2">
                      What's your biggest ERP pain? <span className="text-amber-500">*</span>
                    </label>
                    <textarea
                      autoFocus
                      className="w-full p-3.5 bg-white/[0.03] border border-white/[0.08] rounded-xl focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none text-[13px] text-white placeholder:text-zinc-700 transition resize-none"
                      rows={3}
                      placeholder="e.g. Our ERP is too expensive, no one knows how to use it..."
                      value={formData.failureReason}
                      onChange={(e) => setFormData({ ...formData, failureReason: e.target.value })}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[13px] font-medium text-zinc-400 mb-2">
                        Phone <span className="text-amber-500">*</span>
                      </label>
                      <input
                        type="tel"
                        className="w-full p-3 bg-white/[0.03] border border-white/[0.08] rounded-xl focus:ring-1 focus:ring-amber-500 outline-none text-[13px] text-white placeholder:text-zinc-700"
                        placeholder="+91..."
                        value={formData.phone}
                        onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      />
                    </div>
                    <div>
                      <label className="block text-[13px] font-medium text-zinc-400 mb-2">
                        WhatsApp <span className="text-amber-500">*</span>
                      </label>
                      <input
                        type="tel"
                        className="w-full p-3 bg-white/[0.03] border border-white/[0.08] rounded-xl focus:ring-1 focus:ring-amber-500 outline-none text-[13px] text-white placeholder:text-zinc-700"
                        placeholder="+91..."
                        value={formData.whatsapp}
                        onChange={(e) => setFormData({ ...formData, whatsapp: e.target.value })}
                      />
                    </div>
                  </div>

                  <button
                    onClick={handleFinalListMe}
                    disabled={!formData.phone || !formData.failureReason || isSubmitting}
                    className="w-full py-3 bg-amber-500 text-black font-semibold text-[13px] rounded-xl hover:bg-amber-400 transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center mt-1 cursor-pointer"
                  >
                    {isSubmitting ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      'Join Early Access'
                    )}
                  </button>
                  <p className="text-[11px] text-center text-zinc-700">No credit card. No commitment.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
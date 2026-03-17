'use client';

import React from 'react';
import Link from 'next/link';
import { Phone, ArrowRight } from 'lucide-react';

export default function Contact() {
  return (
    <section className="bg-[#09090B]" id="contact">

      {/* ── PRICING TEASER ── */}
      <div className="border-t border-white/[0.06] py-20">
        <div className="max-w-4xl mx-auto text-center px-4">
          <span className="inline-block text-xs font-bold uppercase tracking-[0.2em] text-amber-500 mb-4">Pricing</span>
          <h2 className="text-3xl font-bold text-white mb-4">Simple, module-based pricing.</h2>
          <p className="text-gray-500 text-lg mb-8 max-w-xl mx-auto leading-relaxed">
            Start with what you need. Add modules as you grow. No consultants, no setup fees, no surprises.
          </p>
          <Link
            href="#cohort"
            className="inline-flex items-center text-amber-500 font-semibold hover:text-amber-400 transition-colors gap-2 group"
          >
            Get a personalized estimate via the ERP Discovery
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>
      </div>

      {/* ── FINAL CTA STRIP ── */}
      <div className="border-t border-white/[0.06] py-20 relative overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(245,158,11,0.04)_1px,transparent_1px),linear-gradient(to_bottom,rgba(245,158,11,0.04)_1px,transparent_1px)] bg-[size:40px_40px]"></div>
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[200px] bg-amber-500/10 blur-3xl rounded-full pointer-events-none"></div>
        <div className="relative max-w-4xl mx-auto text-center px-4">
          <h2 className="text-3xl font-black text-white mb-3 sm:text-4xl">
            Stop planning ERP.<br />Start <span className="text-amber-500">running</span> it.
          </h2>
          <p className="text-gray-500 mb-10 text-lg">
            Answer 5 questions. Get your ERP recommendation and pricing in under 10 minutes. No commitment.
          </p>
          <Link
            href="/landing_page"
            className="inline-block bg-amber-500 text-black px-10 py-4 rounded-xl font-black text-lg hover:bg-amber-400 transition-colors shadow-2xl shadow-amber-500/20"
          >
            Start Free ERP Discovery →
          </Link>
          <p className="text-gray-700 text-xs mt-4">Zero upfront cost. No credit card required.</p>
        </div>
      </div>

      {/* ── CONTACT ── */}
      <div className="border-t border-white/[0.06] py-24">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl font-bold text-white mb-3">Still have questions?</h2>
          <p className="text-gray-500 mb-10">
            Our engineering team is happy to chat about deployment architecture, data migration, or custom requirements.
          </p>

          {/* Contact info */}
          <div className="flex justify-center mb-10">
            <a
              href="tel:+919370983966"
              className="flex items-center gap-3 text-gray-400 hover:text-white transition-colors bg-white/[0.03] border border-white/[0.07] rounded-xl px-6 py-4"
            >
              <Phone className="w-5 h-5 text-amber-500" />
              <div className="text-left">
                <span className="block text-sm font-semibold text-white">+91 93709 83966</span>
                <span className="block text-xs text-gray-600">Available on WhatsApp</span>
              </div>
            </a>
          </div>

          {/* Form */}
          <div className="bg-white/[0.02] border border-white/[0.07] rounded-2xl p-8">
            <form
              className="space-y-4 text-left"
              action="mailto:support@f3next.in"
              method="post"
              encType="text/plain"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">Name</label>
                  <input
                    type="text"
                    name="name"
                    placeholder="Your name"
                    className="w-full px-4 py-3 bg-white/[0.03] border border-white/[0.08] rounded-xl focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none text-white placeholder-gray-700 text-sm transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-500 mb-1.5">Work Email</label>
                  <input
                    type="email"
                    name="email"
                    placeholder="you@company.com"
                    className="w-full px-4 py-3 bg-white/[0.03] border border-white/[0.08] rounded-xl focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none text-white placeholder-gray-700 text-sm transition"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1.5">Message</label>
                <textarea
                  name="message"
                  rows={4}
                  placeholder="Tell us about your current setup and what you're looking for..."
                  className="w-full px-4 py-3 bg-white/[0.03] border border-white/[0.08] rounded-xl focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none text-white placeholder-gray-700 text-sm transition resize-none"
                ></textarea>
              </div>
              <button
                type="submit"
                className="w-full bg-white text-black py-3.5 rounded-xl font-bold hover:bg-gray-100 transition-colors text-sm"
              >
                Send Message
              </button>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}
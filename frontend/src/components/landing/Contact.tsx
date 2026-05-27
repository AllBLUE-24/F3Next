'use client';

import React from 'react';
import Link from 'next/link';
import { Phone, Mail, ArrowRight } from 'lucide-react';

export default function Contact() {
  return (
    <section className="bg-[#09090B]" id="contact">

      {/* ── FINAL CTA ── */}
      <div className="py-24 lg:py-32 relative overflow-hidden">
        {/* Subtle background glow */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[200px] bg-amber-500/[0.06] blur-[120px] rounded-full pointer-events-none" />

        <div className="relative max-w-3xl mx-auto text-center px-6">
          <h2
            className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white tracking-[-0.03em] leading-tight"
            style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
          >
            Stop planning.<br />
            Start <span className="text-amber-500">running</span>.
          </h2>
          <p className="text-zinc-500 mt-5 mb-10 text-base leading-relaxed max-w-md mx-auto">
            Answer 5 questions. Get your ERP recommendation in under 10 minutes. No commitment.
          </p>
          <Link
            href="/onboarding"
            className="group inline-flex items-center gap-2.5 bg-amber-500 text-black px-8 py-3.5 rounded-xl font-semibold text-[14px] hover:bg-amber-400 transition-all duration-200 lift-hover shadow-xl shadow-amber-500/15"
          >
            Start Free Discovery
            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform duration-200" />
          </Link>
          <p className="text-zinc-700 text-[12px] mt-4">Zero upfront cost. No credit card required.</p>
        </div>
      </div>

      {/* ── CONTACT ── */}
      <div className="border-t border-white/[0.04] py-20 lg:py-24">
        <div className="max-w-2xl mx-auto px-6 text-center">
          <h2
            className="text-xl font-semibold text-white mb-3 tracking-tight"
            style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
          >
            Still have questions?
          </h2>
          <p className="text-zinc-500 text-[14px] mb-10 leading-relaxed">
            Our team is happy to discuss deployment architecture, data migration, or custom requirements.
          </p>

          {/* Contact cards */}
          <div className="flex flex-col sm:flex-row justify-center gap-4 mb-10">
            <a
              href="tel:+919370983966"
              className="flex items-center gap-3 text-zinc-400 hover:text-white transition-colors duration-200 bg-white/[0.02] border border-white/[0.05] hover:border-white/[0.1] rounded-xl px-5 py-4"
            >
              <Phone className="w-4 h-4 text-amber-500/70" />
              <div className="text-left">
                <span className="block text-[13px] font-medium text-zinc-300">+91 93709 83966</span>
                <span className="block text-[11px] text-zinc-600">Available on WhatsApp</span>
              </div>
            </a>
            <a
              href="mailto:parth.kulkarni2412@gmail.com"
              className="flex items-center gap-3 text-zinc-400 hover:text-white transition-colors duration-200 bg-white/[0.02] border border-white/[0.05] hover:border-white/[0.1] rounded-xl px-5 py-4"
            >
              <Mail className="w-4 h-4 text-amber-500/70" />
              <div className="text-left">
                <span className="block text-[13px] font-medium text-zinc-300">parth.kulkarni2412@gmail.com</span>
                <span className="block text-[11px] text-zinc-600">Reach out anytime</span>
              </div>
            </a>
          </div>

          {/* Social Links */}
          <div className="flex justify-center gap-5 mb-12">
            <a
              href="https://www.linkedin.com/in/parth-kulkarni-f3/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[13px] text-zinc-600 hover:text-zinc-300 transition-colors duration-200"
            >
              LinkedIn
            </a>
            <a
              href="https://github.com/AllBLUE-24/F3Next"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[13px] text-zinc-600 hover:text-zinc-300 transition-colors duration-200"
            >
              GitHub
            </a>
          </div>

          {/* Contact Form */}
          <div className="bg-white/[0.01] border border-white/[0.05] rounded-2xl p-8">
            <form
              className="space-y-4 text-left"
              action="mailto:parth.kulkarni2412@gmail.com"
              method="post"
              encType="text/plain"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[12px] font-medium text-zinc-600 mb-1.5">Name</label>
                  <input
                    type="text"
                    name="name"
                    placeholder="Your name"
                    className="w-full px-4 py-3 bg-white/[0.03] border border-white/[0.06] rounded-xl focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none text-white placeholder-zinc-700 text-[13px] transition"
                  />
                </div>
                <div>
                  <label className="block text-[12px] font-medium text-zinc-600 mb-1.5">Email</label>
                  <input
                    type="email"
                    name="email"
                    placeholder="you@company.com"
                    className="w-full px-4 py-3 bg-white/[0.03] border border-white/[0.06] rounded-xl focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none text-white placeholder-zinc-700 text-[13px] transition"
                  />
                </div>
              </div>
              <div>
                <label className="block text-[12px] font-medium text-zinc-600 mb-1.5">Message</label>
                <textarea
                  name="message"
                  rows={4}
                  placeholder="Tell us about your setup..."
                  className="w-full px-4 py-3 bg-white/[0.03] border border-white/[0.06] rounded-xl focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none text-white placeholder-zinc-700 text-[13px] transition resize-none"
                />
              </div>
              <button
                type="submit"
                className="w-full bg-white/[0.06] text-zinc-300 hover:text-white hover:bg-white/[0.1] py-3 rounded-xl font-medium text-[13px] transition-all duration-200 border border-white/[0.06] cursor-pointer"
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
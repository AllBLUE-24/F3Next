'use client';

import React from 'react';
import Link from 'next/link';
import { Phone, Mail, ArrowRight } from 'lucide-react';

export default function Contact() {
  return (
    <section className="bg-[#09090B]" id="contact">

      {/* ── FINAL CTA STRIP ── */}
      <div className="border-t border-white/[0.06] py-20 relative overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(245,158,11,0.04)_1px,transparent_1px),linear-gradient(to_bottom,rgba(245,158,11,0.04)_1px,transparent_1px)] bg-[size:40px_40px]"></div>
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[200px] bg-amber-500/10 blur-3xl rounded-full pointer-events-none"></div>
        <div className="relative max-w-4xl mx-auto text-center px-4">
          <h2 className="text-3xl font-black text-white mb-3 sm:text-4xl">
            Stop planning ERP.<br />Start <span className="text-amber-500">running</span> it.
          </h2>
          <p className="text-gray-500 mb-10 text-lg">
            Answer 5 questions. Get your ERP recommendation in under 10 minutes. No commitment.
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
          <div className="flex flex-col sm:flex-row justify-center gap-4 mb-10">
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
            <a
              href="mailto:parth.kulkarni2412@gmail.com"
              className="flex items-center gap-3 text-gray-400 hover:text-white transition-colors bg-white/[0.03] border border-white/[0.07] rounded-xl px-6 py-4"
            >
              <Mail className="w-5 h-5 text-amber-500" />
              <div className="text-left">
                <span className="block text-sm font-semibold text-white">parth.kulkarni2412@gmail.com</span>
                <span className="block text-xs text-gray-600">Reach out anytime</span>
              </div>
            </a>
          </div>

          {/* Social Links */}
          <div className="flex justify-center gap-6 mb-10">
            <a
              href="https://www.linkedin.com/in/parth-kulkarni-f3/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors bg-white/[0.03] border border-white/[0.07] rounded-xl px-5 py-3"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
              LinkedIn
            </a>
            <a
              href="https://github.com/AllBLUE-24/F3Next"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors bg-white/[0.03] border border-white/[0.07] rounded-xl px-5 py-3"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>
              GitHub
            </a>
          </div>

          {/* Form */}
          <div className="bg-white/[0.02] border border-white/[0.07] rounded-2xl p-8">
            <form
              className="space-y-4 text-left"
              action="mailto:parth.kulkarni2412@gmail.com"
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
import Link from 'next/link';
import Header from '@/components/landing/Header';
import HeroDashboardPreview from '@/components/landing/HeroDashboardPreview';
import Vision from '@/components/landing/Vision';
import Pricing from '@/components/landing/Pricing';
import Contact from '@/components/landing/Contact';
import PrivateCohort from '@/components/landing/PrivateCohort';
import HeroBackground from '@/components/landing/HeroBackground';
import { ArrowRight, Shield, Zap, Clock } from 'lucide-react';

export const metadata = {
  title: "F3Next — Headless Operational Systems for Manufacturers",
  description: "Stop running your ₹5Cr factory on messy Excel spreadsheets and chaotic WhatsApp chats. Deploys custom sandboxed databases in minutes with zero employee training.",
};

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-[#09090B] text-white selection:bg-amber-500/20 selection:text-amber-200" style={{ fontFamily: 'var(--font-inter), sans-serif' }}>
      <Header />

      {/* ── HERO ── */}
      <div className="relative pt-32 pb-8 lg:pt-44 lg:pb-16 overflow-hidden">
        <HeroBackground />

        <div className="mx-auto max-w-6xl px-6 lg:px-8 relative z-10">

          {/* Pill badge */}
          <div className="flex justify-center mb-10 fade-in-up">
            <div className="inline-flex items-center gap-2.5 rounded-full border border-white/[0.08] bg-white/[0.03] px-4 py-1.5 text-[11px] font-medium tracking-wide text-zinc-400 backdrop-blur-sm">
              <span className="flex h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
              Building for Indian manufacturers
            </div>
          </div>

          {/* Headline */}
          <div className="text-center max-w-4xl mx-auto fade-in-up">
            <h1
              className="text-4xl sm:text-6xl lg:text-7xl font-bold tracking-[-0.035em] leading-[1.08] text-white"
              style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
            >
              Stop running your factory on{' '}
              <span className="text-amber-500">Excel&nbsp;and&nbsp;WhatsApp.</span>
            </h1>

            <p className="mt-7 text-base sm:text-lg leading-relaxed text-zinc-400 max-w-2xl mx-auto font-normal">
              F3Next deploys secure database systems for your daily inventory, purchase orders, and dispatches — without hiring consultants or training your staff.
            </p>

            {/* Trust signals */}
            <div className="mt-6 flex justify-center items-center gap-8 text-[12px] text-zinc-500 font-medium">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-zinc-600" />
                Deploys in minutes
              </span>
              <span className="hidden sm:flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-zinc-600" />
                Zero training needed
              </span>
              <span className="flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-zinc-600" />
                Starts at ₹999/mo
              </span>
            </div>
          </div>

          {/* CTAs */}
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4 fade-in-up">
            <Link
              href="/signup"
              className="group inline-flex items-center gap-2.5 rounded-xl bg-amber-500 px-7 py-3.5 text-[14px] font-semibold text-black hover:bg-amber-400 transition-all duration-200 shadow-xl shadow-amber-500/15 lift-hover cursor-pointer"
            >
              Get Started Free
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform duration-200 shrink-0" />
            </Link>

            <Link
              href="#how-it-works"
              className="inline-flex items-center gap-2 rounded-xl px-7 py-3.5 text-[14px] font-medium text-zinc-400 border border-white/[0.08] hover:border-white/[0.15] hover:text-white transition-all duration-200 cursor-pointer"
            >
              See how it works
            </Link>
          </div>

          {/* Dashboard Preview — the hero visual, like vtiger/T3 Code */}
          <HeroDashboardPreview />

        </div>
      </div>

      {/* ── SECTIONS ── */}
      <Vision />
      <Pricing />
      <PrivateCohort />
      <Contact />

      {/* ── FOOTER ── */}
      <footer className="border-t border-white/[0.06] bg-[#09090B]">
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="flex flex-col md:flex-row justify-between items-start gap-12">

            {/* Brand */}
            <div className="space-y-3">
              <span className="text-lg font-semibold text-white tracking-tight" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>
                F3<span className="text-amber-500">Next</span>
              </span>
              <p className="text-[13px] text-zinc-600 max-w-xs leading-relaxed">
                Headless operational systems built for Indian manufacturers.
              </p>
            </div>

            {/* Navigation */}
            <div className="flex flex-wrap gap-x-10 gap-y-3 text-[13px] text-zinc-600">
              <Link href="#how-it-works" className="hover:text-zinc-300 transition-colors duration-200">How it Works</Link>
              <Link href="#pricing" className="hover:text-zinc-300 transition-colors duration-200">Pricing</Link>
              <Link href="#cohort" className="hover:text-zinc-300 transition-colors duration-200">Early Access</Link>
            </div>

            {/* Social */}
            <div className="flex items-center gap-5 text-[13px] text-zinc-600">
              <a href="https://www.linkedin.com/in/parth-kulkarni-f3/" target="_blank" rel="noopener noreferrer" className="hover:text-zinc-300 transition-colors duration-200">LinkedIn</a>
              <a href="https://github.com/AllBLUE-24/F3Next" target="_blank" rel="noopener noreferrer" className="hover:text-zinc-300 transition-colors duration-200">GitHub</a>
              <a href="mailto:parth.kulkarni2412@gmail.com" className="hover:text-zinc-300 transition-colors duration-200">Email</a>
            </div>
          </div>

          <div className="mt-12 pt-8 border-t border-white/[0.04] text-[12px] text-zinc-700">
            © 2026 F3Next. Built for Indian manufacturers.
          </div>
        </div>
      </footer>
    </main>
  );
}
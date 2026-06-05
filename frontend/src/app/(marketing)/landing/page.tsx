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
  title: "F3Next — The Intelligence Layer for Your Business",
  description: "Run your business by simply talking to it. F3Next turns messy spreadsheets and daily updates into a live, intelligent ERP — set up, run, and watched over for you. No consultants, no training.",
};

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-[var(--bg-void)] text-white selection:bg-amber-500/20 selection:text-amber-200 font-sans">
      <Header />

      {/* ── HERO ── */}
      <div className="relative pt-36 pb-8 lg:pt-48 lg:pb-16 overflow-hidden">
        <HeroBackground />

        <div className="mx-auto max-w-6xl px-6 lg:px-8 relative z-10">

          {/* Pill badge */}
          <div className="flex justify-center mb-9 fade-in-up">
            <div className="brand-pill">
              <span className="live-dot" />
              The intelligence layer for your business
            </div>
          </div>

          {/* Headline */}
          <div className="text-center max-w-4xl mx-auto fade-in-up">
            <h1 className="font-display text-[2.75rem] leading-[1.05] sm:text-6xl lg:text-[4.75rem] font-bold">
              <span className="text-sheen">Run your business</span>
              <br />
              <span className="text-sheen">by simply </span>
              <span className="text-amber-500">talking to it.</span>
            </h1>

            <p className="mt-7 text-base sm:text-lg leading-relaxed text-[var(--text-secondary)] max-w-2xl mx-auto font-normal">
              F3Next turns your messy spreadsheets and daily updates into a live, intelligent ERP — set up, run, and watched over for you. No consultants, no training, no software to learn.
            </p>

            {/* Trust signals */}
            <div className="mt-7 flex flex-wrap justify-center items-center gap-x-8 gap-y-3 text-[12px] text-[var(--text-muted)] font-medium">
              <span className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-amber-500/70" />
                Live in minutes
              </span>
              <span className="flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-500/70" />
                Zero training needed
              </span>
              <span className="flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-amber-500/70" />
                Your data, sandboxed &amp; private
              </span>
            </div>
          </div>

          {/* CTAs */}
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4 fade-in-up">
            <Link
              href="/signup"
              className="btn-primary focus-ring group cursor-pointer px-7 py-3.5 text-[14px]"
            >
              Get Started Free
              <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform duration-200 shrink-0" />
            </Link>

            <Link
              href="#how-it-works"
              className="btn-ghost focus-ring cursor-pointer px-7 py-3.5 text-[14px]"
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
      <footer className="border-t border-[var(--border-subtle)] bg-[var(--bg-void)]">
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="flex flex-col md:flex-row justify-between items-start gap-12">

            {/* Brand */}
            <div className="space-y-3">
              <span className="font-display text-lg font-semibold text-white">
                F3<span className="text-amber-500">Next</span>
              </span>
              <p className="text-[13px] text-zinc-600 max-w-xs leading-relaxed">
                The intelligence layer for your business. Built for Indian manufacturers.
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
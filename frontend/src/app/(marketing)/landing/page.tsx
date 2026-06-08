import Link from 'next/link';
import { HeroSection } from '@/components/blocks/hero-section-5';
import Vision from '@/components/landing/Vision';
import Pricing from '@/components/landing/Pricing';
import Contact from '@/components/landing/Contact';
import PrivateCohort from '@/components/landing/PrivateCohort';

export const metadata = {
  title: "F3Next — The Intelligence Layer for Your Business",
  description: "Run your business by simply talking to it. F3Next turns messy spreadsheets and daily updates into a live, intelligent ERP — set up, run, and watched over for you. No consultants, no training.",
};

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-void text-primary selection:bg-amber-500/20 selection:text-amber-200 font-sans">
      <HeroSection />

      {/* ── SECTIONS ── */}
      <Vision />
      <Pricing />
      <PrivateCohort />
      <Contact />

      {/* ── FOOTER ── */}
      <footer className="border-t border-subtle bg-void">
        <div className="max-w-7xl mx-auto px-6 py-16">
          <div className="flex flex-col md:flex-row justify-between items-start gap-12">

            {/* Brand */}
            <div className="space-y-3">
              <span className="font-display text-lg font-semibold text-primary">
                F3<span className="text-amber-500">Next</span>
              </span>
              <p className="text-[13px] text-secondary max-w-xs leading-relaxed">
                The intelligence layer for your business. Built for Indian manufacturers.
              </p>
            </div>

            {/* Navigation */}
            <div className="flex flex-wrap gap-x-10 gap-y-3 text-[13px] text-secondary">
              <Link href="#how-it-works" className="hover:text-primary transition-colors duration-200">How it Works</Link>
              <Link href="#pricing" className="hover:text-primary transition-colors duration-200">Pricing</Link>
              <Link href="#cohort" className="hover:text-primary transition-colors duration-200">Early Access</Link>
            </div>

            {/* Social */}
            <div className="flex items-center gap-5 text-[13px] text-secondary">
              <a href="https://www.linkedin.com/in/parth-kulkarni-f3/" target="_blank" rel="noopener noreferrer" className="hover:text-primary transition-colors duration-200">LinkedIn</a>
              <a href="https://github.com/AllBLUE-24/F3Next" target="_blank" rel="noopener noreferrer" className="hover:text-primary transition-colors duration-200">GitHub</a>
              <a href="mailto:parth.kulkarni2412@gmail.com" className="hover:text-primary transition-colors duration-200">Email</a>
            </div>
          </div>

          <div className="mt-12 pt-8 border-t border-white/[0.04] text-[12px] text-secondary">
            © 2026 F3Next. Built for Indian manufacturers.
          </div>
        </div>
      </footer>
    </div>
  );
}
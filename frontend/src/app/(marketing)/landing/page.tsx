import Link from 'next/link';
import Header from '@/components/landing/Header';
import Comparison from '@/components/landing/Comparison';
import WhyUs from '@/components/landing/WhyUs';
import Vision from '@/components/landing/Vision';
import Contact from '@/components/landing/Contact';
import PrivateCohort from '@/components/landing/PrivateCohort';
import HeroBackground from '@/components/landing/HeroBackground';
import { ArrowRight, Cpu, Terminal, MessageSquareDot, Server, FileStack } from 'lucide-react';

export const metadata = {
  title: "F3Next — AI-Powered ERP for Manufacturers",
};

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-[#09090B] text-white selection:bg-amber-500/20 selection:text-amber-200" style={{ fontFamily: 'var(--font-syne), sans-serif' }}>
      <Header />

      {/* ── HERO ── */}
      <div className="relative pt-28 pb-20 lg:pt-40 lg:pb-32 overflow-hidden">
        <HeroBackground />

        <div className="mx-auto max-w-7xl px-6 lg:px-8 relative z-10">

          {/* Badge */}
          <div className="flex justify-center mb-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/20 bg-amber-500/5 px-4 py-1.5 text-xs font-bold uppercase tracking-[0.15em] text-amber-400 backdrop-blur-sm">
              <span className="flex h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse"></span>
              Now accepting Tier 2 & 3 Manufacturers · India
            </div>
          </div>

          {/* Headline */}
          <div className="text-center max-w-5xl mx-auto">
            <h1 className="text-5xl font-black tracking-tight sm:text-7xl lg:text-8xl leading-[0.95] mb-6">
              <span className="block text-white">Your ERP.</span>
              <span className="block text-white">Deployed in</span>
              <span className="block text-amber-500">48 Hours.</span>
            </h1>

            <p className="mt-8 text-lg leading-relaxed text-gray-400 max-w-2xl mx-auto">
              F3Next is an AI system that recommends, deploys, migrates your data into, and then
              <strong className="text-gray-200 font-semibold"> operates your ERP through plain English commands</strong>.
              No consultants. No training. No upfront cost.
            </p>
          </div>

          {/* CTAs */}
          <div className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/landing_page"
              className="group inline-flex items-center gap-2 rounded-xl bg-amber-500 px-8 py-4 text-sm font-black text-black hover:bg-amber-400 transition-colors shadow-2xl shadow-amber-500/20"
            >
              Start Free ERP Discovery
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>

            <Link
              href="#cohort"
              className="inline-flex items-center gap-2 rounded-xl px-8 py-4 text-sm font-bold text-gray-400 bg-white/[0.04] border border-white/[0.08] hover:bg-white/[0.07] hover:text-white transition-all"
            >
              Join Private Cohort — ₹4,999/mo
            </Link>
          </div>

          {/* Social proof line */}
          <p className="mt-8 text-center text-xs text-gray-700 font-medium tracking-wide uppercase">
            Trusted by manufacturers in Pune · Nashik · Aurangabad
          </p>

          {/* ── 4-Step Flow Strip ── */}
          <div className="mt-20 relative">
            {/* Connecting line */}
            <div className="hidden md:block absolute top-9 left-[12%] right-[12%] h-px bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                {
                  icon: MessageSquareDot,
                  step: '01',
                  title: 'AI Recommends ERP',
                  desc: '5 questions → best-fit ERP',
                  color: 'text-blue-400',
                  border: 'border-blue-500/20 hover:border-blue-500/40',
                },
                {
                  icon: Server,
                  step: '02',
                  title: 'Cloud Deployed',
                  desc: 'Secure instance in 48hrs',
                  color: 'text-amber-400',
                  border: 'border-amber-500/20 hover:border-amber-500/40',
                },
                {
                  icon: FileStack,
                  step: '03',
                  title: 'Data Migrated',
                  desc: 'Upload any format, AI maps it',
                  color: 'text-purple-400',
                  border: 'border-purple-500/20 hover:border-purple-500/40',
                },
                {
                  icon: Terminal,
                  step: '04',
                  title: 'Prompt to Run',
                  desc: 'Type commands, ERP executes',
                  color: 'text-green-400',
                  border: 'border-green-500/20 hover:border-green-500/40',
                },
              ].map((item) => (
                <div
                  key={item.step}
                  className={`group relative bg-white/[0.02] border ${item.border} rounded-2xl p-5 transition-all duration-300 text-center`}
                >
                  <div className="flex justify-center mb-3">
                    <div className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
                      <item.icon className={`w-5 h-5 ${item.color}`} />
                    </div>
                  </div>
                  <p className="text-[10px] font-bold text-gray-700 uppercase tracking-widest mb-1">{item.step}</p>
                  <h3 className="text-xs font-bold text-white mb-1 leading-snug">{item.title}</h3>
                  <p className="text-[11px] text-gray-600 leading-snug">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>

          {/* ── Live Prompt Demo ── */}
          <div className="mt-10 bg-[#0D0D14] border border-white/[0.06] rounded-2xl p-6 md:p-8 overflow-hidden relative">
            <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(245,158,11,0.02)_1px,transparent_1px),linear-gradient(to_bottom,rgba(245,158,11,0.02)_1px,transparent_1px)] bg-[size:24px_24px]"></div>
            <div className="relative flex flex-col md:flex-row md:items-center gap-6">
              <div className="flex-1">
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-500 mb-3">Phase 4 in action</p>
                <div className="flex items-start gap-3 font-mono">
                  <span className="text-green-400 text-sm mt-0.5 flex-shrink-0">›</span>
                  <p className="text-sm text-white leading-relaxed">
                    <span className="text-gray-500">"</span>
                    Send purchase order to{' '}
                    <span className="text-amber-400">ABC Corp</span>{' '}
                    for{' '}
                    <span className="text-green-400">10 units of Item X</span>
                    <span className="text-gray-500">"</span>
                  </p>
                </div>
              </div>
              <div className="flex-shrink-0 h-px md:h-12 md:w-px bg-white/[0.06]"></div>
              <div className="grid grid-cols-2 gap-x-8 gap-y-2 flex-shrink-0">
                {[
                  'ERP Entry Created',
                  'PO Number Generated',
                  'Email Sent to Vendor',
                  'Inventory Updated',
                ].map((action) => (
                  <div key={action} className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0"></div>
                    <span className="text-xs text-green-400 font-medium">{action}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* ── PAGE SECTIONS ── */}
      <WhyUs />
      <Vision />
      <Comparison />
      <PrivateCohort />
      <Contact />

      {/* ── FOOTER ── */}
      <footer className="border-t border-white/[0.06] bg-[#09090B] py-12">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-amber-500 rounded-md flex items-center justify-center">
              <Cpu className="h-3.5 w-3.5 text-black" />
            </div>
            <span className="font-black text-white text-lg tracking-tight">
              F3<span className="text-amber-500">Next</span>
            </span>
          </div>

          <div className="flex items-center gap-8 text-xs text-gray-600">
            <Link href="#problem" className="hover:text-gray-400 transition-colors">Why F3Next</Link>
            <Link href="#how-it-works" className="hover:text-gray-400 transition-colors">How it Works</Link>
            <Link href="#comparison" className="hover:text-gray-400 transition-colors">Comparison</Link>
            <Link href="#cohort" className="hover:text-gray-400 transition-colors">Early Access</Link>
          </div>

          <div className="text-xs text-gray-700">
            © 2025 F3Next. Built for Indian manufacturers.
          </div>
        </div>
      </footer>
    </main>
  );
}
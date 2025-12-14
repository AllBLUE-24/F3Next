'use client';

import Link from 'next/link';
import Header from '@/components/landing/Header';
import Comparison from '@/components/landing/Comparison';
import WhyUs from '@/components/landing/WhyUs';
import Vision from '@/components/landing/Vision';
import Contact from '@/components/landing/Contact';
import PrivateCohort from '@/components/landing/PrivateCohort';
import HeroBackground from '@/components/landing/HeroBackground'; // Import Background
import { ArrowRight, Terminal } from 'lucide-react';

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-white font-sans text-gray-900 selection:bg-indigo-100">
      <Header />

      {/* HERO SECTION */}
      <div className="relative pt-24 pb-16 lg:pt-32 lg:pb-24">
        
        {/* Render the Background Component */}
        <HeroBackground />
        
        <div className="mx-auto max-w-7xl px-6 lg:px-8 text-center relative z-10">
          <div className="inline-flex items-center rounded-full border border-indigo-100 bg-indigo-50/50 px-3 py-1 text-sm font-medium text-indigo-700 mb-8 shadow-sm backdrop-blur-sm">
            <span className="flex h-2 w-2 rounded-full bg-indigo-600 mr-2 animate-pulse"></span>
            Accepting Tier 2 & 3 Manufacturers
          </div>
          
          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl mb-6 max-w-4xl mx-auto leading-tight">
            Automate your Factory.<br />
            <span className="text-gray-400">Without the Consultants.</span>
          </h1>
          
          <p className="mt-6 text-lg leading-8 text-gray-600 max-w-2xl mx-auto">
            F3Next configures your ERP based on how your factory actually runs. 
            No expensive implementation partners. No multi-month delays.
          </p>
          
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            {/* Primary Action -> Health Check */}
            <Link 
              href="/landing_page" 
              className="rounded-lg bg-indigo-600 px-8 py-3.5 text-sm font-semibold text-white shadow-lg shadow-indigo-200 hover:bg-indigo-500 hover:-translate-y-0.5 transition-all duration-200 flex items-center justify-center gap-2"
            >
              Start Free Health Check <ArrowRight className="w-4 h-4" />
            </Link>
            
            {/* Secondary Action -> Cohort Scroll */}
            <Link 
              href="#cohort" 
              className="rounded-lg px-8 py-3.5 text-sm font-semibold text-gray-700 bg-white ring-1 ring-inset ring-gray-200 hover:bg-gray-50 hover:text-gray-900 shadow-sm transition-all"
            >
              Join Private Cohort
            </Link>
          </div>

          <div className="mt-12 text-sm text-gray-400 font-medium">
            Trusted by modern manufacturers in Pune, Nashik, and Aurangabad.
          </div>
        </div>
      </div>

      {/* PRIVATE COHORT SECTION */}
      <PrivateCohort />

      {/* SECTIONS */}
      <Comparison />
      <WhyUs />
      <Vision />
      <Contact />

      <footer className="bg-gray-50 text-gray-600 py-12 border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2">
            <Terminal className="h-5 w-5 text-gray-400" />
            <span className="font-semibold text-gray-900">F3Next</span>
          </div>
          <p className="text-sm">© 2025 F3Next Inc. Manufacturing Intelligence.</p>
        </div>
      </footer>
    </main>
  );
}
'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Menu, X } from 'lucide-react';

export default function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
      scrolled
        ? 'bg-[#09090B]/95 backdrop-blur-md border-b border-white/[0.06] shadow-xl shadow-black/20'
        : 'bg-transparent'
    }`}>
      <nav className="flex items-center justify-between p-4 lg:px-10 max-w-7xl mx-auto" aria-label="Global">

        {/* Logo — text only */}
        <div className="flex lg:flex-1">
          <Link href="/" className="-m-1.5 p-1.5 flex items-center gap-2.5 group">
            <span className="font-bold text-xl text-white tracking-tight">
              F3<span className="text-amber-500">Next</span>
            </span>
          </Link>
        </div>

        {/* Mobile Menu Button */}
        <div className="flex lg:hidden">
          <button
            type="button"
            className="-m-2.5 inline-flex items-center justify-center rounded-md p-2.5 text-gray-400 hover:text-white"
            onClick={() => setMobileMenuOpen(true)}
          >
            <span className="sr-only">Open main menu</span>
            <Menu className="h-6 w-6" aria-hidden="true" />
          </button>
        </div>

        {/* Desktop Links */}
        <div className="hidden lg:flex lg:gap-x-8">
          <Link href="#problem" className="text-sm font-medium leading-6 text-gray-400 hover:text-white transition-colors">
            Why F3Next
          </Link>
          <Link href="#how-it-works" className="text-sm font-medium leading-6 text-gray-400 hover:text-white transition-colors">
            How it Works
          </Link>
          <Link href="#comparison" className="text-sm font-medium leading-6 text-gray-400 hover:text-white transition-colors">
            Comparison
          </Link>
          <Link href="#cohort" className="text-sm font-medium leading-6 text-amber-500 hover:text-amber-400 transition-colors">
            Early Access
          </Link>
        </div>

        {/* Desktop CTAs */}
        <div className="hidden lg:flex lg:flex-1 lg:justify-end gap-4 items-center">
          <Link href="/login" className="text-sm font-medium text-gray-400 hover:text-white transition-colors">
            Sign in
          </Link>
          <Link
            href="/landing_page"
            className="rounded-md bg-amber-500 px-5 py-2.5 text-sm font-bold text-black hover:bg-amber-400 transition-colors shadow-lg shadow-amber-500/20"
          >
            Free ERP Discovery →
          </Link>
        </div>
      </nav>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div className="lg:hidden" role="dialog" aria-modal="true">
          <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" onClick={() => setMobileMenuOpen(false)} />
          <div className="fixed inset-y-0 right-0 z-50 w-full overflow-y-auto bg-[#09090B] border-l border-white/[0.08] px-6 py-6 sm:max-w-sm">
            <div className="flex items-center justify-between">
              <Link href="/" className="-m-1.5 p-1.5 flex items-center gap-2.5">
                <span className="font-bold text-xl text-white">F3<span className="text-amber-500">Next</span></span>
              </Link>
              <button
                type="button"
                className="-m-2.5 rounded-md p-2.5 text-gray-400"
                onClick={() => setMobileMenuOpen(false)}
              >
                <X className="h-6 w-6" aria-hidden="true" />
              </button>
            </div>
            <div className="mt-8 flow-root">
              <div className="space-y-1">
                {[
                  { href: '#problem', label: 'Why F3Next' },
                  { href: '#how-it-works', label: 'How it Works' },
                  { href: '#comparison', label: 'Comparison' },
                  { href: '#cohort', label: 'Early Access', highlight: true },
                ].map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`block rounded-lg px-4 py-3 text-base font-semibold ${
                      item.highlight
                        ? 'text-amber-500 bg-amber-500/10'
                        : 'text-gray-300 hover:text-white hover:bg-white/[0.05]'
                    } transition-colors`}
                  >
                    {item.label}
                  </Link>
                ))}
                <div className="pt-4 border-t border-white/[0.08] mt-4 space-y-3">
                  <Link
                    href="/landing_page"
                    className="block rounded-md bg-amber-500 px-4 py-3 text-base font-bold text-black text-center"
                  >
                    Free ERP Discovery →
                  </Link>
                  <Link
                    href="/login"
                    className="block rounded-md px-4 py-3 text-base font-medium text-gray-400 text-center hover:text-white"
                  >
                    Sign in
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
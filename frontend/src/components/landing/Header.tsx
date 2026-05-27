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
    <header className={`fixed inset-x-0 top-0 z-50 transition-all duration-500 ${
      scrolled
        ? 'bg-[#09090B]/90 backdrop-blur-xl border-b border-white/[0.06]'
        : 'bg-transparent'
    }`}>
      <nav className="flex items-center justify-between px-6 py-4 lg:px-10 max-w-7xl mx-auto" aria-label="Global">

        {/* Logo */}
        <div className="flex lg:flex-1">
          <Link href="/" className="-m-1.5 p-1.5 flex items-center gap-2 group">
            <span className="text-lg font-semibold text-white tracking-tight" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>
              F3<span className="text-amber-500">Next</span>
            </span>
          </Link>
        </div>

        {/* Mobile Menu Button */}
        <div className="flex lg:hidden">
          <button
            type="button"
            className="-m-2.5 inline-flex items-center justify-center rounded-lg p-2.5 text-zinc-500 hover:text-white transition-colors"
            onClick={() => setMobileMenuOpen(true)}
          >
            <span className="sr-only">Open main menu</span>
            <Menu className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        {/* Desktop Links */}
        <div className="hidden lg:flex lg:gap-x-8 items-center">
          {[
            { href: '#chaos-to-clarity', label: 'Why F3Next' },
            { href: '#how-it-works', label: 'How it Works' },
            { href: '#pricing', label: 'Pricing' },
            { href: '#cohort', label: 'Early Access' },
          ].map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-[13px] font-medium text-zinc-500 hover:text-white transition-colors duration-200"
            >
              {item.label}
            </Link>
          ))}
        </div>

        {/* Desktop CTAs */}
        <div className="hidden lg:flex lg:flex-1 lg:justify-end gap-5 items-center">
          <Link href="/login" className="text-[13px] font-medium text-zinc-500 hover:text-white transition-colors duration-200">
            Sign in
          </Link>
          <Link
            href="/signup"
            className="rounded-lg bg-amber-500 px-5 py-2 text-[13px] font-semibold text-black hover:bg-amber-400 transition-all duration-200 lift-hover"
          >
            Start Free
          </Link>
        </div>
      </nav>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div className="lg:hidden" role="dialog" aria-modal="true">
          <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm" onClick={() => setMobileMenuOpen(false)} />
          <div className="fixed inset-y-0 right-0 z-50 w-full overflow-y-auto bg-[#09090B] border-l border-white/[0.06] px-6 py-6 sm:max-w-sm">
            <div className="flex items-center justify-between">
              <Link href="/" className="-m-1.5 p-1.5 flex items-center gap-2">
                <span className="text-lg font-semibold text-white" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>
                  F3<span className="text-amber-500">Next</span>
                </span>
              </Link>
              <button
                type="button"
                className="-m-2.5 rounded-lg p-2.5 text-zinc-500 hover:text-white transition-colors"
                onClick={() => setMobileMenuOpen(false)}
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
            <div className="mt-10 flow-root">
              <div className="space-y-1">
                {[
                  { href: '#chaos-to-clarity', label: 'Why F3Next' },
                  { href: '#how-it-works', label: 'How it Works' },
                  { href: '#pricing', label: 'Pricing' },
                  { href: '#cohort', label: 'Early Access' },
                ].map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className="block rounded-lg px-4 py-3 text-[15px] font-medium text-zinc-400 hover:text-white hover:bg-white/[0.04] transition-colors"
                  >
                    {item.label}
                  </Link>
                ))}
                <div className="pt-6 border-t border-white/[0.06] mt-6 space-y-3">
                  <Link
                    href="/signup"
                    className="block rounded-lg bg-amber-500 px-4 py-3 text-[15px] font-semibold text-black text-center"
                  >
                    Start Free
                  </Link>
                  <Link
                    href="/login"
                    className="block rounded-lg px-4 py-3 text-[15px] font-medium text-zinc-500 text-center hover:text-white transition-colors"
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
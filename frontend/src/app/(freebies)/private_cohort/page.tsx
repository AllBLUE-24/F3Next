'use client';

import React from 'react';
import Link from 'next/link';
import { ShieldCheck, Lock, MessageCircle, Star, CheckCircle2, ArrowRight } from 'lucide-react';

export default function PrivateCohortSuccess() {
  return (
    <div className="min-h-screen bg-[#0B0F19] text-white flex flex-col relative overflow-hidden font-sans">
      
      {/* --- BACKGROUND EFFECTS --- */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Grid */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f2937_1px,transparent_1px),linear-gradient(to_bottom,#1f2937_1px,transparent_1px)] bg-[size:40px_40px] opacity-20"></div>
        {/* Glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-indigo-600/20 blur-[120px] rounded-full"></div>
      </div>

      {/* --- MAIN CONTENT --- */}
      <main className="flex-grow flex items-center justify-center px-4 sm:px-6 relative z-10 py-20">
        <div className="max-w-3xl w-full text-center space-y-12">
          
          {/* 1. THE REVEAL */}
          <div className="animate-in fade-in zoom-in duration-700 slide-in-from-bottom-4">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-green-500/10 border border-green-500/30 text-green-400 text-sm font-bold uppercase tracking-widest mb-8 shadow-[0_0_20px_rgba(74,222,128,0.1)]">
              <ShieldCheck className="w-4 h-4" />
              Spot Secured
            </div>
            
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 text-white">
              Welcome to the <br/>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">
                Inner Circle.
              </span>
            </h1>
            
            <p className="text-xl text-gray-400 max-w-2xl mx-auto leading-relaxed">
              You have successfully joined the F3Next Private Cohort. 
              While others wait for the public launch, your factory's dedicated instance is being prepared.
            </p>
          </div>

          {/* 2. THE VALUE CARD (The "Why this was a good idea" section) */}
          <div className="grid md:grid-cols-2 gap-6 max-w-2xl mx-auto animate-in fade-in slide-in-from-bottom-8 duration-700 delay-200">
             
             {/* Card 1: The Price Lock */}
             <div className="bg-white/5 backdrop-blur-sm border border-white/10 p-6 rounded-2xl text-left hover:bg-white/10 transition-colors group relative overflow-hidden">
                <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
                    <Lock className="w-24 h-24 text-white" />
                </div>
                <div className="relative z-10">
                    <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center mb-4 shadow-lg shadow-indigo-900/50">
                        <Star className="w-5 h-5 text-white fill-current" />
                    </div>
                    <h3 className="text-lg font-bold text-white mb-1">Founder's Pricing</h3>
                    <div className="flex items-baseline gap-2 mb-2">
                        <span className="text-2xl font-bold text-green-400">₹4,999</span>
                        <span className="text-sm text-gray-500 line-through">₹10,000</span>
                    </div>
                    <p className="text-sm text-gray-400 leading-snug">
                        Your pricing is <span className="text-white font-semibold">locked for life</span>. Even when public pricing doubles, you pay the same.
                    </p>
                </div>
             </div>

             {/* Card 2: Premium Support */}
             <div className="bg-white/5 backdrop-blur-sm border border-white/10 p-6 rounded-2xl text-left hover:bg-white/10 transition-colors group relative overflow-hidden">
                 <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
                    <MessageCircle className="w-24 h-24 text-white" />
                </div>
                <div className="relative z-10">
                    <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center mb-4 shadow-lg shadow-green-900/50">
                        <MessageCircle className="w-5 h-5 text-white" />
                    </div>
                    <h3 className="text-lg font-bold text-white mb-2">Priority Line</h3>
                    <p className="text-sm text-gray-400 mb-4 leading-snug">
                        Have a specific problem on your factory floor? You now have direct access to our engineering team.
                    </p>
                    <a 
                        href="https://wa.me/919370983966?text=Hey%2C%20I%20just%20joined%20the%20F3Next%20Private%20Cohort%21%20I%20have%20a%20question..."
                        target="_blank"
                        rel="noopener noreferrer" 
                        className="inline-flex items-center text-sm font-bold text-green-400 hover:text-green-300 transition-colors"
                    >
                        Chat on WhatsApp <ArrowRight className="w-4 h-4 ml-1" />
                    </a>
                </div>
             </div>
          </div>

          {/* 3. CTA / CONTACT STRIP */}
          <div className="animate-in fade-in slide-in-from-bottom-8 duration-700 delay-300">
             <div className="bg-indigo-900/30 border border-indigo-500/30 rounded-xl p-6 max-w-lg mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="text-left">
                    <p className="text-sm font-semibold text-indigo-200 uppercase tracking-wider mb-1">Direct Founder Contact</p>
                    <p className="text-2xl font-bold text-white tracking-widest">+91 9370983966</p>
                </div>
                <a 
                    href="https://wa.me/919370983966?text=Hey%2C%20I%20just%20joined%20the%20F3Next%20Private%20Cohort%21"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full sm:w-auto px-6 py-3 bg-white text-indigo-900 font-bold rounded-lg hover:bg-gray-100 transition-colors flex items-center justify-center gap-2"
                >
                    <MessageCircle className="w-5 h-5" />
                    Say Hello
                </a>
             </div>
             <p className="mt-6 text-sm text-gray-500">
                We will email you as soon as the platform goes live for your batch.
             </p>
          </div>

        </div>
      </main>

      {/* --- FOOTER --- */}
      <footer className="py-6 text-center text-gray-600 text-xs border-t border-gray-900 relative z-10">
        <p>SECURE CONNECTION • 256-BIT ENCRYPTED • SESSION ID: {Math.random().toString(36).substring(7).toUpperCase()}</p>
      </footer>
    </div>
  );
}
'use client';

import React from 'react';
import { Check, X } from 'lucide-react';

export default function Comparison() {
  return (
    <section className="py-24 bg-gray-50" id="comparison">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold text-gray-900 tracking-tight sm:text-4xl">
            Why Manufacturers are Switching
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            The old way vs. the autonomous way.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 items-center max-w-5xl mx-auto">
            
            {/* LEFT: The Old Way (Muted) */}
            <div className="bg-white p-8 rounded-2xl border border-gray-100 text-gray-500 opacity-80 hover:opacity-100 transition-opacity">
                <h3 className="text-sm font-bold uppercase tracking-widest text-gray-400 mb-6">Traditional ERP</h3>
                <div className="space-y-6">
                    <div className="flex justify-between items-center border-b border-gray-100 pb-4">
                        <span>Setup Time</span>
                        <span className="font-medium text-gray-700">3–6 Months</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-gray-100 pb-4">
                        <span>Upfront Cost</span>
                        <span className="font-medium text-red-500">₹5,00,000+</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-gray-100 pb-4">
                        <span>Success Rate</span>
                        <span className="font-medium text-red-500">{'<'} 30%</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-gray-100 pb-4">
                        <span>Consultants</span>
                        <span className="flex items-center text-gray-700">Required <Check className="w-4 h-4 ml-2 text-gray-400"/></span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span>Changes</span>
                        <span className="font-medium text-gray-700">Expensive</span>
                    </div>
                </div>
            </div>

            {/* RIGHT: F3Next (Highlighted) */}
            <div className="bg-white p-8 rounded-2xl border-2 border-indigo-600 shadow-2xl relative transform md:scale-105 z-10">
                <div className="absolute top-0 right-0 bg-indigo-600 text-white text-xs font-bold px-3 py-1 rounded-bl-lg rounded-tr-lg">
                    RECOMMENDED
                </div>
                <h3 className="text-sm font-bold uppercase tracking-widest text-indigo-600 mb-6 flex items-center gap-2">
                    F3Next <span className="bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full text-[10px]">AI Driven</span>
                </h3>
                
                <div className="space-y-6">
                    <div className="flex justify-between items-center border-b border-indigo-50 pb-4">
                        <span className="font-medium text-gray-900">Setup Time</span>
                        <span className="font-bold text-green-600 flex items-center">
                             {'<'} 48 Hours
                        </span>
                    </div>
                    <div className="flex justify-between items-center border-b border-indigo-50 pb-4">
                        <span className="font-medium text-gray-900">Upfront Cost</span>
                        <span className="font-bold text-green-600">Zero</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-indigo-50 pb-4">
                        <span className="font-medium text-gray-900">Success Rate</span>
                        <span className="font-bold text-green-600">95%+</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-indigo-50 pb-4">
                        <span className="font-medium text-gray-900">Consultants</span>
                        <span className="flex items-center text-gray-400">Not needed <X className="w-4 h-4 ml-2 text-gray-300"/></span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="font-medium text-gray-900">Changes</span>
                        <span className="font-bold text-indigo-600">Included (AI)</span>
                    </div>
                </div>
            </div>

        </div>
      </div>
    </section>
  );
}
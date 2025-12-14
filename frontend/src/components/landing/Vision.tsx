'use client';

import React from 'react';
import { MessageSquare, Settings, Database, Factory, LayoutGrid, Users, TrendingDown, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function Vision() {
  return (
    <section id="how-it-works">
      {/* HOW IT WORKS */}
      <div className="py-24 bg-indigo-900 text-white">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl mb-4">
              How it Works
            </h2>
            <p className="text-indigo-200 max-w-2xl mx-auto">
              Three simple phases to go from idea to a working system.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 relative">
            {/* Connecting Line (Desktop) */}
            <div className="hidden md:block absolute top-12 left-[16%] right-[16%] h-0.5 bg-indigo-700 -z-10"></div>

            {/* Step 1 */}
            <div className="relative flex flex-col items-center text-center">
              <div className="w-24 h-24 bg-indigo-800 rounded-full flex items-center justify-center border-4 border-indigo-900 mb-6 z-10">
                <MessageSquare className="w-10 h-10 text-indigo-300" />
              </div>
              <h3 className="text-xl font-bold mb-3">1. Recommendation</h3>
              <p className="text-indigo-200 text-sm leading-relaxed px-4">
                You answer 5–7 simple questions. F3Next recommends the right ERP setup and pricing — instantly.
              </p>
            </div>

            {/* Step 2 */}
            <div className="relative flex flex-col items-center text-center">
               <div className="w-24 h-24 bg-indigo-800 rounded-full flex items-center justify-center border-4 border-indigo-900 mb-6 z-10">
                <Settings className="w-10 h-10 text-indigo-300" />
              </div>
              <h3 className="text-xl font-bold mb-3">2. Guided Configuration</h3>
              <p className="text-indigo-200 text-sm leading-relaxed px-4">
                Our AI clarifies your workflow and narrows down required modules. No overwhelming forms.
              </p>
            </div>

            {/* Step 3 */}
            <div className="relative flex flex-col items-center text-center">
               <div className="w-24 h-24 bg-indigo-800 rounded-full flex items-center justify-center border-4 border-indigo-900 mb-6 z-10">
                <Database className="w-10 h-10 text-indigo-300" />
              </div>
              <h3 className="text-xl font-bold mb-3">3. Automated Setup</h3>
              <p className="text-indigo-200 text-sm leading-relaxed px-4">
                We generate data templates, validate settings, and deploy your instance. You approve, we execute.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* WHO IS THIS FOR / TRUST */}
      <div className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="lg:grid lg:grid-cols-2 gap-16">
                {/* Who is it for */}
                <div>
                    <h3 className="text-2xl font-bold text-gray-900 mb-6">Who is F3Next for?</h3>
                    <ul className="space-y-6">
                        <li className="flex items-start">
                            <Factory className="w-5 h-5 text-indigo-600 mr-3 mt-1 shrink-0" />
                            <div>
                                <span className="font-semibold text-gray-900 block">Manufacturing Companies (MSMEs)</span>
                                <span className="text-sm text-gray-600">Factories that need to track scrap, waste, and true production costs.</span>
                            </div>
                        </li>
                        <li className="flex items-start">
                            <LayoutGrid className="w-5 h-5 text-indigo-600 mr-3 mt-1 shrink-0" />
                            <div>
                                <span className="font-semibold text-gray-900 block">Inventory Heavy Operations</span>
                                <span className="text-sm text-gray-600">Businesses struggling with "Where is my stock?" and dead capital.</span>
                            </div>
                        </li>
                        <li className="flex items-start">
                            <AlertTriangle className="w-5 h-5 text-indigo-600 mr-3 mt-1 shrink-0" />
                            <div>
                                <span className="font-semibold text-gray-900 block">Tired of Failed Implementations</span>
                                <span className="text-sm text-gray-600">
                                    Traditional ERPs fail 70% of the time. We are built for the 95%+ success rate.
                                </span>
                            </div>
                        </li>
                        <li className="flex items-start">
                            <TrendingDown className="w-5 h-5 text-indigo-600 mr-3 mt-1 shrink-0" />
                            <div>
                                <span className="font-semibold text-gray-900 block">Cost Conscious Leaders</span>
                                <span className="text-sm text-gray-600">
                                    For those who refuse to pay Lakhs in consulting fees for a "Standard" setup.
                                </span>
                            </div>
                        </li>
                    </ul>
                </div>

                {/* Trust & Safety */}
                <div className="mt-12 lg:mt-0 bg-gray-50 p-8 rounded-2xl border border-gray-100 h-fit">
                     <h3 className="text-xl font-bold text-gray-900 mb-4">Safety First Architecture</h3>
                     <p className="text-gray-600 mb-6 text-sm">
                        We use AI to recommend and configure, but we never deploy irreversible changes without your say-so.
                     </p>
                     <div className="space-y-5">
                         <div className="flex gap-4">
                             <div className="w-1 h-full min-h-[40px] bg-green-500 rounded-full"></div>
                             <div>
                                 <h4 className="font-semibold text-gray-900 text-sm">Human-in-the-loop</h4>
                                 <p className="text-xs text-gray-500 mt-1">Every major configuration decision is reviewed by you.</p>
                             </div>
                         </div>
                         <div className="flex gap-4">
                             <div className="w-1 h-full min-h-[40px] bg-green-500 rounded-full"></div>
                             <div>
                                 <h4 className="font-semibold text-gray-900 text-sm">Preview before Import</h4>
                                 <p className="text-xs text-gray-500 mt-1">See exactly how your data will look before it hits the database.</p>
                             </div>
                         </div>
                         <div className="flex gap-4">
                             <div className="w-1 h-full min-h-[40px] bg-green-500 rounded-full"></div>
                             <div>
                                 <h4 className="font-semibold text-gray-900 text-sm">95%+ Success Rate</h4>
                                 <p className="text-xs text-gray-500 mt-1">Compared to the industry average of {'<'}30%.</p>
                             </div>
                         </div>
                     </div>
                </div>
            </div>
        </div>
      </div>
    </section>
  );
}
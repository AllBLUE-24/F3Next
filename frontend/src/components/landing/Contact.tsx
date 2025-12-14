'use client';

import React from 'react';
import Link from 'next/link';
import { Phone, Mail, ArrowRight } from 'lucide-react';

export default function Contact() {
  return (
    <section className="bg-white" id="contact">
        {/* PRICING TEASER */}
        <div className="py-20 border-t border-gray-100">
            <div className="max-w-4xl mx-auto text-center px-4">
                <h2 className="text-3xl font-bold text-gray-900 mb-4">Simple, predictable pricing.</h2>
                <p className="text-lg text-gray-600 mb-8">
                    Pricing is based on company size and selected modules. Start small. Upgrade anytime.
                </p>
                <Link href="#cohort" className="text-indigo-600 font-semibold hover:text-indigo-500 flex items-center justify-center gap-2">
                    Get a price estimate in the Health Check <ArrowRight className="w-4 h-4"/>
                </Link>
            </div>
        </div>

        {/* FINAL CTA STRIP */}
        <div className="bg-indigo-600 py-16">
            <div className="max-w-4xl mx-auto text-center px-4">
                <h2 className="text-3xl font-bold text-white mb-2">Stop planning ERP. Start running it.</h2>
                <p className="text-indigo-200 mb-8">Takes less than 3 minutes. No commitment.</p>
                <Link 
                    href="/landing_page" 
                    className="inline-block bg-white text-indigo-600 px-8 py-3 rounded-full font-bold hover:bg-indigo-50 transition shadow-lg"
                >
                    Start with 5 Questions
                </Link>
            </div>
        </div>

      {/* CONTACT FORM */}
      <div className="py-24 bg-gray-900">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl font-bold text-white mb-4">
            Still have questions?
          </h2>
          <p className="text-gray-400 mb-8">
             Our engineering team is ready to chat about deployment, security, or custom needs.
          </p>

          {/* Contact Details */}
          <div className="flex flex-col md:flex-row justify-center items-center gap-6 mb-10 text-gray-300">
             <div className="flex items-center gap-2">
               <Phone className="w-5 h-5 text-indigo-400" />
               <a href="tel:+919370983966" className="hover:text-white transition">+91 9370983966 (available on whatsapp)</a>
             </div>
             
          </div>
          
          <div className="bg-gray-800/50 p-8 rounded-xl shadow-lg border border-gray-700">
            <form className="space-y-4" action="mailto:support@f3next.com" method="post" encType="text/plain">
               <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <input 
                    type="text" 
                    name="name"
                    placeholder="Name" 
                    className="w-full px-4 py-3 border border-gray-700 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-white bg-gray-900 placeholder-gray-500" 
                  />
                  <input 
                    type="email" 
                    name="email"
                    placeholder="Work Email" 
                    className="w-full px-4 py-3 border border-gray-700 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-white bg-gray-900 placeholder-gray-500" 
                  />
               </div>
               <textarea 
                 name="message"
                 rows={4} 
                 placeholder="How can we help?" 
                 className="w-full px-4 py-3 border border-gray-700 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-white bg-gray-900 placeholder-gray-500"
               ></textarea>
               <button type="submit" className="w-full bg-indigo-600 text-white py-3 rounded-lg font-bold hover:bg-indigo-700 transition">
                  Send Message via Email
               </button>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}
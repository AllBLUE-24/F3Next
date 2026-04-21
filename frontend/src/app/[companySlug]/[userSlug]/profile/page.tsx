"use client";

import { use } from "react";
import { User, Building2, CreditCard, ShieldCheck } from "lucide-react";

interface PageProps {
  params: Promise<{ companySlug: string; userSlug: string }>;
}

export default function ProfilePage({ params }: PageProps) {
  const { companySlug, userSlug } = use(params);

  return (
    <div className="max-w-4xl space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-white tracking-tight">Account Profile</h1>
        <p className="text-zinc-400 mt-2">Manage your workspace settings and billing preferences.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* User Details */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 border-b border-white/10 pb-2">
            <User className="h-5 w-5 text-amber-500" />
            <h2 className="text-lg font-bold text-white">User Information</h2>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-6 space-y-6">
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-zinc-500">Username / Slug</label>
              <div className="mt-1 text-zinc-200 font-mono text-sm">{userSlug}</div>
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-zinc-500">Role</label>
              <div className="mt-1 inline-flex items-center gap-1.5 rounded-full border border-amber-500/20 bg-amber-500/10 px-2.5 py-0.5 text-xs font-bold text-amber-400">
                <ShieldCheck className="h-3.5 w-3.5" /> Workspace Admin
              </div>
            </div>
          </div>
        </section>

        {/* Company Details */}
        <section className="space-y-4">
          <div className="flex items-center gap-3 border-b border-white/10 pb-2">
            <Building2 className="h-5 w-5 text-amber-500" />
            <h2 className="text-lg font-bold text-white">Company Workspace</h2>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-6 space-y-6">
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-zinc-500">Workspace Slug</label>
              <div className="mt-1 text-zinc-200 font-mono text-sm">{companySlug}</div>
            </div>
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-zinc-500">Environment</label>
              <div className="mt-1 text-zinc-200 font-medium">Production <span className="text-zinc-600 font-normal ml-2">(DigitalOcean)</span></div>
            </div>
          </div>
        </section>

        {/* Billing & Plan */}
        <section className="space-y-4 md:col-span-2">
          <div className="flex items-center gap-3 border-b border-white/10 pb-2">
            <CreditCard className="h-5 w-5 text-amber-500" />
            <h2 className="text-lg font-bold text-white">Billing & Plan</h2>
          </div>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between rounded-xl border border-white/10 bg-white/5 p-6">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h3 className="text-xl font-bold text-white">Early Access Cohort</h3>
                <span className="rounded-full bg-green-500/10 border border-green-500/20 px-2 py-0.5 text-xs font-bold text-green-400 uppercase tracking-widest">Active</span>
              </div>
              <p className="text-sm text-zinc-400">Unlimited ERP deployments and operations during the beta period.</p>
            </div>
            <button className="mt-6 sm:mt-0 px-5 py-2.5 bg-white text-black text-sm font-bold rounded-lg hover:bg-zinc-200 transition-colors whitespace-nowrap">
              Manage Billing
            </button>
          </div>
        </section>

      </div>
    </div>
  );
}
"use client";

import { use } from "react";
import { User, Building2, CreditCard, ShieldCheck } from "lucide-react";
import { TeamInvitesPanel } from "@/components/platform/TeamInvitesPanel";

interface PageProps {
  params: Promise<{ companySlug: string; userSlug: string }>;
}

export default function ProfilePage({ params }: PageProps) {
  const { companySlug, userSlug } = use(params);

  return (
    <div className="max-w-4xl space-y-10 fade-in-up">
      
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Account Profile</h1>
        <p className="text-zinc-500 text-sm mt-1.5">Manage your workspace settings and billing preferences.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* User Details */}
        <section className="space-y-3">
          <div className="flex items-center gap-2.5 border-b border-[var(--border-subtle)] pb-2">
            <User className="h-4 w-4 text-amber-500" />
            <h2 className="text-sm font-bold text-white">User Information</h2>
          </div>
          <div className="surface-card p-5 space-y-5" style={{ borderRadius: 'var(--radius-lg)' }}>
            <div>
              <label className="text-[10px] font-bold uppercase tracking-wider text-zinc-600">Username / Slug</label>
              <div className="mt-1 text-zinc-300 font-mono text-sm">{userSlug}</div>
            </div>
            <div>
              <label className="text-[10px] font-bold uppercase tracking-wider text-zinc-600">Role</label>
              <div className="mt-1.5 inline-flex items-center gap-1.5 rounded-lg border border-amber-500/20 bg-amber-500/8 px-2.5 py-1 text-[11px] font-bold text-amber-400">
                <ShieldCheck className="h-3 w-3" /> Workspace Admin
              </div>
            </div>
          </div>
        </section>

        {/* Company Details */}
        <section className="space-y-3">
          <div className="flex items-center gap-2.5 border-b border-[var(--border-subtle)] pb-2">
            <Building2 className="h-4 w-4 text-amber-500" />
            <h2 className="text-sm font-bold text-white">Company Workspace</h2>
          </div>
          <div className="surface-card p-5 space-y-5" style={{ borderRadius: 'var(--radius-lg)' }}>
            <div>
              <label className="text-[10px] font-bold uppercase tracking-wider text-zinc-600">Workspace Slug</label>
              <div className="mt-1 text-zinc-300 font-mono text-sm">{companySlug}</div>
            </div>
            <div>
              <label className="text-[10px] font-bold uppercase tracking-wider text-zinc-600">Environment</label>
              <div className="mt-1 text-zinc-300 text-sm font-medium">Production <span className="text-zinc-600 font-normal ml-2">(DigitalOcean)</span></div>
            </div>
          </div>
        </section>

        {/* Billing & Plan */}
        <section className="space-y-3 md:col-span-2">
          <div className="flex items-center gap-2.5 border-b border-[var(--border-subtle)] pb-2">
            <CreditCard className="h-4 w-4 text-amber-500" />
            <h2 className="text-sm font-bold text-white">Billing & Plan</h2>
          </div>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between surface-card p-5" style={{ borderRadius: 'var(--radius-lg)' }}>
            <div>
              <div className="flex items-center gap-3 mb-1.5">
                <h3 className="text-lg font-bold text-white">Early Access Cohort</h3>
                <span className="rounded-lg bg-green-500/10 border border-green-500/20 px-2 py-0.5 text-[10px] font-bold text-green-400 uppercase tracking-wider">Active</span>
              </div>
              <p className="text-xs text-zinc-500">Unlimited ERP deployments and operations during the beta period.</p>
            </div>
            <button className="mt-5 sm:mt-0 px-5 py-2 bg-white/[0.08] border border-[var(--border-default)] text-white text-sm font-medium rounded-xl hover:bg-white/[0.08] transition-all whitespace-nowrap">
              Manage Billing
            </button>
          </div>
        </section>

        <TeamInvitesPanel companySlug={companySlug} />
      </div>
    </div>
  );
}
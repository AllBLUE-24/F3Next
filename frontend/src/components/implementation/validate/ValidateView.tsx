'use client';

// src/components/implementation/validate/ValidateView.tsx

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { AlertTriangle, Info, CheckCircle, ChevronDown, ChevronUp, ArrowRight, MessageSquare } from 'lucide-react';
import type { CompanyProfile, ValidationItem } from '@/types/implementation';

interface Props {
  profile: CompanyProfile;
  validationItems: ValidationItem[];
  submitAction: (formData: FormData) => Promise<void>;
  sandboxHref: string;
  companySlug: string;
}

const TYPE_CONFIG = {
  missing:       { label: 'Missing',       icon: AlertTriangle, color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/20' },
  contradiction: { label: 'Contradiction', icon: AlertTriangle, color: 'text-red-400',    bg: 'bg-red-500/10 border-red-500/20' },
  suggestion:    { label: 'Suggestion',    icon: Info,          color: 'text-blue-400',   bg: 'bg-blue-500/10 border-blue-500/20' },
};

export function ValidateView({ profile, validationItems, submitAction, sandboxHref, companySlug }: Props) {
  const [responses, setResponses]     = useState<Record<string, string>>({});
  const [profileEdits, setProfileEdits] = useState<Record<string, string>>({});
  const [note, setNote]               = useState('');
  const [expanded, setExpanded]       = useState<string | null>(validationItems[0]?.id ?? null);
  const [resolved, setResolved]       = useState<Set<string>>(new Set());
  const [isPending, startTransition]  = useTransition();
  const router = useRouter();

  const toggleExpand = (id: string) => setExpanded((prev) => (prev === id ? null : id));
  const markResolved = (id: string) => setResolved((prev) => new Set([...prev, id]));

  const unresolvedRequired = validationItems.filter(
    (item) => item.required && !resolved.has(item.id)
  );
  const canSubmit = unresolvedRequired.length === 0;

  const handleSubmit = () => {
    startTransition(async () => {
      const formData = new FormData();
      formData.append('companySlug', companySlug);
      formData.append('responses', JSON.stringify(responses));
      formData.append('profileEdits', JSON.stringify(profileEdits));
      formData.append('note', note);
      await submitAction(formData);
      router.push(sandboxHref);
    });
  };

  return (
    <div className="space-y-10">
      {/* Header */}
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-500 mb-2">Step 03 of 04</p>
        <h1 className="text-3xl font-black text-white mb-3">Review your profile.</h1>
        <p className="text-gray-500 text-base leading-relaxed">
          Here's what we found. Confirm what's right, correct what's off, and answer what we couldn't figure out.
        </p>
      </div>

      {/* Confidence badge */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1 bg-white/[0.06] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${profile.confidence}%`,
              background: profile.confidence > 75 ? '#22c55e' : profile.confidence > 50 ? '#f59e0b' : '#ef4444',
            }}
          />
        </div>
        <span className="text-xs font-mono text-gray-500">{profile.confidence}% confidence</span>
      </div>

      {/* Company Profile Card */}
      <div className="bg-white/[0.02] border border-white/[0.07] rounded-2xl p-6 space-y-5">
        <h2 className="text-sm font-bold text-white uppercase tracking-widest">Company Profile</h2>
        <div className="grid grid-cols-2 gap-4">
          {[
            ['Legal Name', profile.legalName, 'legalName'],
            ['Industry', profile.industry, 'industry'],
            ['Country', profile.country, 'country'],
            ['Currency', profile.currency, 'currency'],
            ['Fiscal Year Start', profile.fiscalYearStart, 'fiscalYearStart'],
            ['GST Number', profile.gstNumber ?? '—', 'gstNumber'],
          ].map(([label, value, key]) => (
            <div key={key}>
              <p className="text-[10px] uppercase tracking-widest text-gray-700 mb-1">{label}</p>
              <input
                className="w-full bg-transparent text-sm text-white font-medium border-b border-white/[0.06] focus:border-amber-500/50 outline-none py-1 transition-colors placeholder:text-gray-700"
                defaultValue={value}
                onChange={(e) => setProfileEdits((prev) => ({ ...prev, [key]: e.target.value }))}
              />
            </div>
          ))}
        </div>

        {/* Modules */}
        <div>
          <p className="text-[10px] uppercase tracking-widest text-gray-700 mb-2">Detected Modules</p>
          <div className="flex flex-wrap gap-2">
            {profile.modules.map((m) => (
              <span key={m} className="text-xs bg-amber-500/10 border border-amber-500/20 text-amber-400 px-2.5 py-1 rounded-full font-medium">
                {m}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Validation Items */}
      {validationItems.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-white uppercase tracking-widest">
            {validationItems.length} thing{validationItems.length !== 1 ? 's' : ''} need your attention
          </h2>
          <div className="space-y-2">
            {validationItems.map((item) => {
              const cfg = TYPE_CONFIG[item.type];
              const isExpanded = expanded === item.id;
              const isResolved = resolved.has(item.id);

              return (
                <div
                  key={item.id}
                  className={`rounded-xl border transition-all duration-300 ${
                    isResolved ? 'bg-green-500/5 border-green-500/20 opacity-60' : `${cfg.bg}`
                  }`}
                >
                  {/* Header row */}
                  <button
                    onClick={() => toggleExpand(item.id)}
                    className="w-full flex items-center gap-3 p-4 text-left"
                  >
                    {isResolved
                      ? <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                      : <cfg.icon className={`w-4 h-4 ${cfg.color} flex-shrink-0`} />
                    }
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-bold uppercase tracking-widest ${isResolved ? 'text-green-500' : cfg.color}`}>
                          {isResolved ? 'Resolved' : cfg.label}
                        </span>
                        {item.required && !isResolved && (
                          <span className="text-[9px] bg-red-500/20 text-red-400 border border-red-500/20 px-1.5 py-0.5 rounded font-bold uppercase">
                            Required
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-white font-medium mt-0.5">{item.field}</p>
                      <p className="text-xs text-gray-500 mt-0.5 truncate">{item.message}</p>
                    </div>
                    {isExpanded
                      ? <ChevronUp className="w-4 h-4 text-gray-600 flex-shrink-0" />
                      : <ChevronDown className="w-4 h-4 text-gray-600 flex-shrink-0" />
                    }
                  </button>

                  {/* Expanded input */}
                  {isExpanded && !isResolved && (
                    <div className="px-4 pb-4 space-y-3">
                      <textarea
                        rows={2}
                        placeholder={`Provide ${item.field.toLowerCase()}…`}
                        className="w-full p-3 bg-black/20 border border-white/[0.08] rounded-lg focus:ring-1 focus:ring-amber-500 focus:border-amber-500 outline-none text-sm text-white placeholder:text-gray-700 resize-none transition"
                        value={responses[item.id] ?? ''}
                        onChange={(e) => setResponses((prev) => ({ ...prev, [item.id]: e.target.value }))}
                      />
                      <button
                        onClick={() => {
                          if (responses[item.id]?.trim()) markResolved(item.id);
                        }}
                        disabled={!responses[item.id]?.trim()}
                        className="text-xs font-bold text-amber-500 hover:text-amber-400 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                      >
                        Mark as provided →
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Note box */}
      <div className="bg-white/[0.02] border border-white/[0.06] rounded-xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <MessageSquare className="w-4 h-4 text-gray-600" />
          <p className="text-xs font-bold uppercase tracking-widest text-gray-600">Add a note (optional)</p>
        </div>
        <textarea
          rows={3}
          placeholder="Anything our system should know that wasn't in your files…"
          className="w-full bg-transparent text-sm text-white placeholder:text-gray-700 outline-none resize-none"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </div>

      {/* CTA */}
      {!canSubmit && (
        <p className="text-xs text-yellow-500 font-medium">
          {unresolvedRequired.length} required item{unresolvedRequired.length !== 1 ? 's' : ''} still need{unresolvedRequired.length === 1 ? 's' : ''} a response before you can continue.
        </p>
      )}

      <button
        onClick={handleSubmit}
        disabled={!canSubmit || isPending}
        className="w-full py-4 rounded-xl bg-amber-500 text-black font-black text-base hover:bg-amber-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2 group shadow-xl shadow-amber-500/10"
      >
        {isPending ? (
          <>
            <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
            Submitting…
          </>
        ) : (
          <>
            Confirm & Start Import
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </>
        )}
      </button>
    </div>
  );
}
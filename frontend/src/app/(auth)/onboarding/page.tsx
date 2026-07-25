"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/utils/supabase/client";
import { getAuthUser } from "@/utils/auth-user";
import { isDevAuthBypassEnabled } from "@/utils/dev-auth";
import { getBaseApiUrl } from "@/lib/config";
import { slugify } from "@/lib/slugify";
import { ArrowRight, ArrowLeft, CheckCircle2, Copy, Loader2, Users } from "lucide-react";

type Step = "profile" | "company" | "invite";

const STEPS: { id: Step; label: string }[] = [
  { id: "profile", label: "Profile" },
  { id: "company", label: "Company" },
  { id: "invite", label: "Team" },
];

const INDUSTRY_HINTS = [
  "Manufacturing",
  "Trading & Distribution",
  "Construction",
  "Services",
  "Other",
];

export default function OnboardingPage() {
  const router = useRouter();
  const devBypass = isDevAuthBypassEnabled();

  const [sessionUser, setSessionUser] = useState<{ id: string; email?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState<Step>("profile");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    fullName: "",
    userSlug: "",
    role: "",
    companyName: "",
    companySlug: "",
    industryHint: "",
  });

  const [workspace, setWorkspace] = useState<{
    companySlug: string;
    userSlug: string;
    projectId?: string;
  } | null>(null);

  const [inviteUrl, setInviteUrl] = useState("");
  const [colleagueEmail, setColleagueEmail] = useState("");
  const [copyDone, setCopyDone] = useState(false);
  const [inviteLoading, setInviteLoading] = useState(false);

  useEffect(() => {
    if (devBypass) {
      getAuthUser().then(({ user }) => {
        if (!user) {
          router.push("/login");
        } else {
          setSessionUser(user);
          setLoading(false);
        }
      });
      return;
    }

    const supabase = createClient();

    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) {
        router.push("/login");
      } else {
        setSessionUser(user);
        setLoading(false);
      }
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session?.user) router.push("/login");
      else setSessionUser(session.user);
    });

    return () => subscription.unsubscribe();
  }, [router, devBypass]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => {
      const next = { ...prev, [name]: value };
      if (name === "fullName") next.userSlug = slugify(value);
      if (name === "companyName") next.companySlug = slugify(value);
      return next;
    });
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: "" }));
  };

  const handleSlugChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: slugify(e.target.value) }));
  };

  const validateProfile = () => {
    const next: Record<string, string> = {};
    if (!formData.fullName.trim()) next.fullName = "Full name is required";
    if (!formData.userSlug.trim()) next.userSlug = "User handle is required";
    if (!formData.role.trim()) next.role = "Role is required";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const validateCompany = () => {
    const next: Record<string, string> = {};
    if (!formData.companyName.trim()) next.companyName = "Company name is required";
    if (!formData.companySlug.trim()) next.companySlug = "Workspace URL is required";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const completeSetup = async () => {
    if (!sessionUser) return;
    setIsSubmitting(true);
    setErrors({});

    try {
      const res = await fetch(`${getBaseApiUrl()}/api/onboarding/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: sessionUser.id,
          email: sessionUser.email || "",
          full_name: formData.fullName.trim(),
          user_slug: formData.userSlug.trim(),
          role: formData.role.trim(),
          company_name: formData.companyName.trim(),
          company_slug: formData.companySlug.trim(),
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        let message = "Something went wrong";
        if (typeof data.detail === "string") message = data.detail;
        else if (Array.isArray(data.detail)) {
          message = data.detail
            .map((err: { loc?: string[]; msg?: string }) => `${err.loc?.join(".") || "field"}: ${err.msg}`)
            .join("; ");
        }
        throw new Error(message);
      }

      setWorkspace({
        companySlug: formData.companySlug.trim(),
        userSlug: formData.userSlug.trim(),
        projectId: data.project_id,
      });
      setStep("invite");
    } catch (err: unknown) {
      setErrors({ form: err instanceof Error ? err.message : "Setup failed" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const createInviteLink = useCallback(async () => {
    if (!sessionUser || !workspace) return;
    setInviteLoading(true);
    try {
      const res = await fetch(`${getBaseApiUrl()}/api/invites/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: sessionUser.id,
          company_slug: workspace.companySlug,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create invite");
      const origin = typeof window !== "undefined" ? window.location.origin : "";
      setInviteUrl(`${origin}${data.invite_url}`);
    } catch (err: unknown) {
      setErrors({ form: err instanceof Error ? err.message : "Could not create invite link" });
    } finally {
      setInviteLoading(false);
    }
  }, [sessionUser, workspace]);

  useEffect(() => {
    if (step === "invite" && workspace && !inviteUrl && !inviteLoading) {
      createInviteLink();
    }
  }, [step, workspace, inviteUrl, inviteLoading, createInviteLink]);

  const sendColleagueInvite = async () => {
    if (!sessionUser || !workspace || !colleagueEmail.trim()) return;
    setInviteLoading(true);
    try {
      const res = await fetch(`${getBaseApiUrl()}/api/invites/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: sessionUser.id,
          company_slug: workspace.companySlug,
          email: colleagueEmail.trim(),
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to send invite");
      }
      setColleagueEmail("");
      setErrors({});
    } catch (err: unknown) {
      setErrors({ form: err instanceof Error ? err.message : "Invite failed" });
    } finally {
      setInviteLoading(false);
    }
  };

  const goHome = () => {
    if (workspace) {
      router.push(`/${workspace.companySlug}/${workspace.userSlug}/home`);
    }
  };

  const stepIndex = STEPS.findIndex((s) => s.id === step);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[var(--bg-void)]">
        <Loader2 className="w-6 h-6 animate-spin text-amber-500" />
      </div>
    );
  }

  const inputClass = "block w-full px-3.5 py-3 border border-white/[0.08] rounded-lg text-[14px] text-zinc-200 bg-white/[0.03] focus:ring-1 focus:ring-amber-500/30 focus:border-amber-500/30 outline-none transition-all duration-200 placeholder:text-zinc-700";

  return (
    <div className="flex min-h-screen w-full bg-[#09090B] text-white">

      {/* ═══ LEFT: Contextual Guide Panel (desktop only) ═══ */}
      <div className="relative hidden md:flex md:w-1/2 flex-col justify-between p-14 lg:p-16 overflow-hidden">
        <div className="absolute inset-0 bg-[#0c0c10]" />
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-amber-500/[0.04] rounded-full blur-[160px] pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-amber-600/[0.03] rounded-full blur-[140px] pointer-events-none" />
        <div className="absolute inset-y-0 right-0 w-px bg-gradient-to-b from-transparent via-white/[0.06] to-transparent" />

        {/* Logo */}
        <div className="relative z-10">
          <span className="text-lg font-semibold text-white/90 tracking-tight" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>
            F3<span className="text-amber-500">Next</span>
          </span>
        </div>

        {/* Dynamic Context */}
        <div className="relative z-10 my-auto max-w-sm space-y-6">
          {isSubmitting ? (
            <div className="space-y-6 fade-in-up">
              <div className="flex items-center gap-3">
                <Loader2 className="w-6 h-6 text-amber-500 animate-spin" />
                <h3 className="text-xl font-semibold tracking-tight text-white" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>
                  Deploying your workspace
                </h3>
              </div>
              <p className="text-[13px] text-zinc-500 leading-relaxed">
                Configuring your Frappe/ERPNext container, bootstrapping industry playbooks, and preparing validation rules.
              </p>
              <div className="bg-white/[0.02] border border-white/[0.04] rounded-xl p-5 space-y-3 font-mono text-[11px]">
                <div className="flex items-center justify-between text-zinc-400">
                  <div className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-ping shrink-0" />
                    <span>Deploying isolated environment...</span>
                  </div>
                  <span className="text-emerald-400 font-medium">Active</span>
                </div>
                <div className="flex items-center justify-between text-zinc-600">
                  <div className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-zinc-700 shrink-0" />
                    <span>Seeding playbooks...</span>
                  </div>
                  <span className="font-medium">Pending</span>
                </div>
                <div className="flex items-center justify-between text-zinc-600">
                  <div className="flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-zinc-700 shrink-0" />
                    <span>Initializing context engine...</span>
                  </div>
                  <span className="font-medium">Pending</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4 fade-in-up">
              {step === "profile" && (
                <div className="space-y-3">
                  <span className="inline-flex items-center bg-amber-500/10 border border-amber-500/20 px-3 py-1 rounded-full text-[10px] font-medium uppercase tracking-wider text-amber-500">Step 1 of 3</span>
                  <h3 className="text-2xl font-semibold tracking-tight text-white leading-tight" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>Set up your identity</h3>
                  <p className="text-[14px] text-zinc-500 leading-relaxed">Your workspace persona maps natural language commands to operational actions.</p>
                </div>
              )}
              {step === "company" && (
                <div className="space-y-3">
                  <span className="inline-flex items-center bg-amber-500/10 border border-amber-500/20 px-3 py-1 rounded-full text-[10px] font-medium uppercase tracking-wider text-amber-500">Step 2 of 3</span>
                  <h3 className="text-2xl font-semibold tracking-tight text-white leading-tight" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>Configure your workspace</h3>
                  <p className="text-[14px] text-zinc-500 leading-relaxed">Your industry selection pre-populates database structures and instructs our context engine.</p>
                </div>
              )}
              {step === "invite" && (
                <div className="space-y-3">
                  <span className="inline-flex items-center bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full text-[10px] font-medium uppercase tracking-wider text-emerald-400">Step 3 of 3</span>
                  <h3 className="text-2xl font-semibold tracking-tight text-white leading-tight" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>Invite your team</h3>
                  <p className="text-[14px] text-zinc-500 leading-relaxed">ERP workflows work best with multiple users. Invite co-founders, accountants, and managers.</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="relative z-10 mt-auto pt-6 text-[11px] text-zinc-700 font-medium">
          Built for Indian manufacturers
        </div>
      </div>

      {/* ═══ RIGHT: Form Panel ═══ */}
      <div className="relative flex w-full md:w-1/2 flex-col justify-center items-center px-6 py-12 sm:px-12 lg:px-16 overflow-y-auto min-h-screen">
        <div className="absolute top-1/4 right-1/3 w-72 h-72 rounded-full bg-amber-500/[0.02] blur-[120px] pointer-events-none" />

        <div className="relative z-10 w-full max-w-md space-y-6">
          {/* Header */}
          <div className="fade-in-up">
            <h1 className="text-[28px] font-semibold tracking-[-0.02em] text-white" style={{ fontFamily: 'var(--font-outfit), sans-serif' }}>
              Set up your workspace
            </h1>
            <p className="mt-2 text-[14px] text-zinc-500">
              A few details and you&apos;re ready to operate.
            </p>
          </div>

          {/* Stepper */}
          <div className="flex items-center justify-center gap-2 bg-white/[0.02] border border-white/[0.04] p-3 rounded-xl">
            {STEPS.map((s, i) => (
              <div key={s.id} className="flex items-center gap-2">
                <div
                  className={`flex items-center justify-center w-7 h-7 rounded-full text-[11px] font-semibold transition-all ${
                    i < stepIndex
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                      : i === stepIndex
                        ? "bg-amber-500 text-black"
                        : "bg-white/[0.02] text-zinc-600 border border-white/[0.06]"
                  }`}
                >
                  {i < stepIndex ? <CheckCircle2 className="w-3.5 h-3.5" /> : i + 1}
                </div>
                <span className={`text-[11px] font-medium ${i === stepIndex ? "text-zinc-300" : "text-zinc-600"} hidden sm:inline`}>
                  {s.label}
                </span>
                {i < STEPS.length - 1 && <div className="w-4 h-px bg-white/[0.06]" />}
              </div>
            ))}
          </div>

          {errors.form && (
            <div className="p-3.5 text-[13px] text-red-400 bg-red-500/[0.06] border border-red-500/15 rounded-lg">
              {errors.form}
            </div>
          )}

          {/* ── STEP: Profile ── */}
          {step === "profile" && (
            <div className="space-y-4">
              <div className="space-y-4">
                <div>
                  <label className="block text-[12px] font-medium text-zinc-500 mb-1.5">Full name</label>
                  <input name="fullName" value={formData.fullName} onChange={handleChange} placeholder="Parth Patel" className={inputClass} />
                  {errors.fullName && <p className="mt-1 text-[11px] text-red-400">{errors.fullName}</p>}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[12px] font-medium text-zinc-500 mb-1.5">Role</label>
                    <input name="role" value={formData.role} onChange={handleChange} placeholder="CEO, CTO…" className={inputClass} />
                    {errors.role && <p className="mt-1 text-[11px] text-red-400">{errors.role}</p>}
                  </div>
                  <div>
                    <label className="block text-[12px] font-medium text-zinc-500 mb-1.5">Your handle</label>
                    <div className="flex items-center px-3.5 py-3 border border-white/[0.08] rounded-lg bg-white/[0.03] focus-within:ring-1 focus-within:ring-amber-500/30">
                      <span className="text-zinc-600 mr-1 select-none">/</span>
                      <input name="userSlug" value={formData.userSlug} onChange={handleSlugChange} className="w-full bg-transparent text-[14px] text-zinc-200 outline-none" />
                    </div>
                    {errors.userSlug && <p className="mt-1 text-[11px] text-red-400">{errors.userSlug}</p>}
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={() => { if (validateProfile()) setStep("company"); }}
                className="w-full py-3 px-4 rounded-lg text-[14px] font-semibold text-black bg-amber-500 hover:bg-amber-400 transition-all duration-200 flex items-center justify-center gap-2 shadow-lg shadow-amber-500/10 cursor-pointer"
              >
                Continue <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* ── STEP: Company ── */}
          {step === "company" && (
            <div className="space-y-4">
              <div className="space-y-4">
                <div>
                  <label className="block text-[12px] font-medium text-zinc-500 mb-1.5">Company name</label>
                  <input name="companyName" value={formData.companyName} onChange={handleChange} placeholder="Green Surface Pvt Ltd" className={inputClass} />
                  {errors.companyName && <p className="mt-1 text-[11px] text-red-400">{errors.companyName}</p>}
                </div>
                <div>
                  <label className="block text-[12px] font-medium text-zinc-500 mb-1.5">Workspace URL</label>
                  <div className="flex items-center px-3.5 py-3 border border-white/[0.08] rounded-lg bg-white/[0.03] text-zinc-500 text-[14px] focus-within:ring-1 focus-within:ring-amber-500/30">
                    <span className="hidden sm:inline shrink-0 select-none">f3next.in/</span>
                    <input name="companySlug" value={formData.companySlug} onChange={handleSlugChange} className="w-full bg-transparent text-zinc-200 outline-none ml-1" />
                  </div>
                  {errors.companySlug && <p className="mt-1 text-[11px] text-red-400">{errors.companySlug}</p>}
                </div>
                <div>
                  <label className="block text-[12px] font-medium text-zinc-500 mb-1.5">Industry (optional)</label>
                  <select
                    name="industryHint"
                    value={formData.industryHint}
                    onChange={handleChange}
                    className="block w-full px-3.5 py-3 border border-white/[0.08] rounded-lg text-[14px] text-zinc-200 bg-white/[0.03] focus:ring-1 focus:ring-amber-500/30 outline-none cursor-pointer"
                  >
                    <option value="">Select industry vertical...</option>
                    {INDUSTRY_HINTS.map((h) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setStep("profile")}
                  className="flex-1 py-3 px-4 rounded-lg text-[13px] font-medium text-zinc-400 border border-white/[0.08] hover:bg-white/[0.04] flex items-center justify-center gap-1 transition-all duration-200 cursor-pointer"
                >
                  <ArrowLeft className="w-4 h-4 shrink-0" /> Back
                </button>
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => { if (validateCompany()) completeSetup(); }}
                  className="flex-[2] py-3 px-4 rounded-lg text-[14px] font-semibold text-black bg-amber-500 hover:bg-amber-400 disabled:opacity-50 flex items-center justify-center gap-2 transition-all duration-200 shadow-lg shadow-amber-500/10 cursor-pointer"
                >
                  {isSubmitting ? (
                    <><Loader2 className="w-4 h-4 animate-spin shrink-0" /> Creating...</>
                  ) : (
                    <>Create workspace <ArrowRight className="w-4 h-4 shrink-0" /></>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* ── STEP: Invite ── */}
          {step === "invite" && workspace && (
            <div className="space-y-4">
              <div className="space-y-4">
                <div className="flex items-start gap-3 rounded-lg border border-amber-500/15 bg-amber-500/[0.04] p-4">
                  <Users className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-[13px] font-medium text-white">Invite your team</p>
                    <p className="text-[12px] text-zinc-500 mt-1 leading-relaxed">
                      Share a secure workspace link or invite colleagues directly.
                    </p>
                  </div>
                </div>

                <div>
                  <label className="block text-[12px] font-medium text-zinc-500 mb-1.5">Invite link</label>
                  <div className="flex gap-2">
                    <input
                      readOnly
                      value={inviteUrl || (inviteLoading ? "Generating secure invite link…" : "")}
                      className="flex-1 px-3 py-3 border border-white/[0.08] rounded-lg text-[12px] text-zinc-400 bg-white/[0.03] font-mono truncate outline-none select-all"
                    />
                    <button
                      type="button"
                      disabled={!inviteUrl}
                      onClick={async () => {
                        if (!inviteUrl) return;
                        await navigator.clipboard.writeText(inviteUrl);
                        setCopyDone(true);
                        setTimeout(() => setCopyDone(false), 2000);
                      }}
                      className="px-3.5 py-3 rounded-lg border border-white/[0.08] text-zinc-300 hover:bg-white/[0.04] disabled:opacity-40 transition-all flex items-center justify-center cursor-pointer"
                      title="Copy link"
                    >
                      {copyDone ? <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" /> : <Copy className="w-4 h-4 shrink-0" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-[12px] font-medium text-zinc-500 mb-1.5">Colleague email (optional)</label>
                  <div className="flex gap-2">
                    <input
                      type="email"
                      value={colleagueEmail}
                      onChange={(e) => setColleagueEmail(e.target.value)}
                      placeholder="colleague@company.com"
                      className={`flex-1 ${inputClass}`}
                    />
                    <button
                      type="button"
                      disabled={!colleagueEmail.trim() || inviteLoading}
                      onClick={sendColleagueInvite}
                      className="px-4 py-3 rounded-lg text-[13px] font-medium text-amber-500 border border-amber-500/20 hover:bg-amber-500/[0.06] disabled:opacity-40 transition-all cursor-pointer shrink-0"
                    >
                      Add
                    </button>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={goHome}
                  className="flex-1 py-3 px-4 rounded-lg text-[13px] font-medium text-zinc-500 hover:text-zinc-300 transition-colors cursor-pointer"
                >
                  Skip for now
                </button>
                <button
                  type="button"
                  onClick={goHome}
                  className="flex-[2] py-3 px-4 rounded-lg text-[14px] font-semibold text-black bg-amber-500 hover:bg-amber-400 flex items-center justify-center gap-2 transition-all duration-200 shadow-lg shadow-amber-500/10 cursor-pointer"
                >
                  Go to workspace <ArrowRight className="w-4 h-4 shrink-0" />
                </button>
              </div>
            </div>
          )}

          <p className="text-center text-[13px] text-zinc-600">
            Already have an account?{" "}
            <Link href="/login" className="font-medium text-amber-500 hover:text-amber-400 transition-colors duration-200">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

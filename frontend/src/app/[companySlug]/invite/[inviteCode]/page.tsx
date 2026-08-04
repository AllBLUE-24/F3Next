"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/utils/supabase/client";
import { getAuthUser } from "@/utils/auth-user";
import { isDevAuthBypassEnabled } from "@/utils/dev-auth";
import { getBaseApiUrl } from "@/lib/config";
import { slugify } from "@/lib/slugify";
import { DEPARTMENTS, departmentLabel } from "@/lib/departments";
import { Bot, Loader2, Users } from "lucide-react";

interface PageProps {
  params: Promise<{ companySlug: string; inviteCode: string }>;
}

function InviteForm({ companySlug, inviteCode }: { companySlug: string; inviteCode: string }) {
  const router = useRouter();
  const supabase = createClient();

  const [user, setUser] = useState<{ id: string; email?: string } | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [isValidating, setIsValidating] = useState(true);
  const [inviteData, setInviteData] = useState<{
    company_name?: string;
    department?: string | null;
    department_label?: string | null;
  } | null>(null);
  const [error, setError] = useState("");

  const [formData, setFormData] = useState({
    fullName: "",
    userSlug: "",
    role: "",
    department: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isDevAuthBypassEnabled()) {
      getAuthUser().then(({ user }) => {
        setUser(user);
        setAuthLoading(false);
      });
      return;
    }

    supabase.auth.getUser().then(({ data: { user: u } }) => {
      setUser(u);
      setAuthLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, [supabase]);

  useEffect(() => {
    const checkInvite = async () => {
      try {
        const res = await fetch(
          `${getBaseApiUrl()}/api/invites/validate?code=${inviteCode}&slug=${companySlug}`
        );
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "This invite link is invalid or has expired.");
        }
        const json = await res.json();
        setInviteData(json);
        if (json.department) {
          setFormData((prev) => ({ ...prev, department: json.department }));
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Invalid invite");
      } finally {
        setIsValidating(false);
      }
    };
    checkInvite();
  }, [inviteCode, companySlug]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => {
      const next = { ...prev, [name]: value };
      if (name === "fullName") next.userSlug = slugify(value);
      return next;
    });
  };

  const handleSlugChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: slugify(e.target.value) }));
  };

  const handleJoinTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setIsSubmitting(true);
    setError("");

    try {
      const res = await fetch(`${getBaseApiUrl()}/api/invites/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          invite_code: inviteCode,
          user_id: user.id,
          full_name: formData.fullName,
          user_slug: formData.userSlug,
          role: formData.role,
          department: formData.department || undefined,
        }),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Failed to join team. Please try again.");

      router.push(`/${companySlug}/${formData.userSlug}/home`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to join team");
      setIsSubmitting(false);
    }
  };

  const companyLabel = inviteData?.company_name || companySlug;
  const loginHref = `/login?redirect=/${companySlug}/invite/${inviteCode}`;

  if (isValidating || authLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[var(--bg-void)]">
        <Loader2 className="w-6 h-6 animate-spin text-amber-500" />
      </div>
    );
  }

  if (error && !inviteData) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg-void)] p-4">
        <div className="absolute inset-0 void-grid opacity-40" />
        <div className="relative w-full max-w-md p-8 text-center surface-card" style={{ borderRadius: "var(--radius-xl)" }}>
          <div className="inline-flex items-center justify-center w-12 h-12 bg-red-500/10 rounded-2xl mb-4">
            <span className="text-red-400 text-xl">✕</span>
          </div>
          <h1 className="text-xl font-bold text-white mb-2">Invite unavailable</h1>
          <p className="text-sm text-zinc-500 mb-6">{error}</p>
          <Link href="/login" className="text-sm font-medium text-amber-400 hover:text-amber-300">
            Go to sign in
          </Link>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg-void)] p-4">
        <div className="absolute inset-0 void-grid opacity-40" />
        <div className="relative w-full max-w-md p-8 space-y-6 surface-card text-center" style={{ borderRadius: "var(--radius-xl)" }}>
          <div className="inline-flex items-center justify-center w-12 h-12 bg-amber-500 rounded-2xl shadow-lg shadow-amber-500/20">
            <Bot className="w-6 h-6 text-black" />
          </div>
          <div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-400 mb-3">
              <Users className="w-3 h-3" /> Team invitation
            </span>
            <h1 className="text-2xl font-bold text-white">You&apos;ve been invited</h1>
            <p className="mt-2 text-sm text-zinc-500">
              Join <span className="text-zinc-300 font-medium">{companyLabel}</span> on F3Next.
            </p>
          </div>
          <Link
            href={loginHref}
            className="block w-full py-2.5 px-4 rounded-xl text-sm font-bold text-black bg-amber-500 hover:bg-amber-400 transition-all"
          >
            Sign in or create account
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-void)] p-4">
      <div className="absolute inset-0 void-grid opacity-40" />

      <div className="relative w-full max-w-lg p-8 space-y-6 surface-card" style={{ borderRadius: "var(--radius-xl)" }}>
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-400 mb-3">
            <Users className="w-3 h-3" /> Team invitation
          </span>
          <h1 className="text-2xl font-bold text-white">Join {companyLabel}</h1>
          <p className="mt-1.5 text-sm text-zinc-500">Set up your profile for this workspace.</p>
        </div>

        {error && (
          <div className="p-3 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl">
            {error}
          </div>
        )}

        <form onSubmit={handleJoinTeam} className="space-y-4">
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-zinc-500 mb-1.5">
              Signed in as
            </label>
            <div className="flex items-center gap-2 px-3.5 py-2.5 border border-[var(--border-default)] rounded-xl bg-[var(--bg-void)] text-sm text-zinc-300">
              <span className="h-2 w-2 rounded-full bg-emerald-500 shrink-0" />
              {user.email}
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-zinc-500 mb-1.5">
              Full name
            </label>
            <input
              name="fullName"
              type="text"
              required
              placeholder="Jane Doe"
              value={formData.fullName}
              onChange={handleChange}
              className="block w-full px-3.5 py-2.5 border border-[var(--border-default)] rounded-xl text-sm text-zinc-200 bg-[var(--bg-void)] focus:ring-2 focus:ring-amber-500/30 outline-none placeholder:text-zinc-700"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wider text-zinc-500 mb-1.5">
                Your role
              </label>
              <input
                name="role"
                type="text"
                required
                placeholder="Engineer"
                value={formData.role}
                onChange={handleChange}
                className="block w-full px-3.5 py-2.5 border border-[var(--border-default)] rounded-xl text-sm text-zinc-200 bg-[var(--bg-void)] focus:ring-2 focus:ring-amber-500/30 outline-none"
              />
            </div>
            <div>
              <label className="block text-[11px] font-bold uppercase tracking-wider text-zinc-500 mb-1.5">
                Department
              </label>
              <select
                name="department"
                value={formData.department}
                onChange={handleChange}
                className="block w-full px-3.5 py-2.5 border border-[var(--border-default)] rounded-xl text-sm text-zinc-200 bg-[var(--bg-void)] focus:ring-2 focus:ring-amber-500/30 outline-none"
              >
                <option value="">Select department</option>
                {DEPARTMENTS.map((d) => (
                  <option key={d.value} value={d.value}>
                    {d.label}
                  </option>
                ))}
              </select>
              {inviteData?.department && (
                <p className="text-[11px] text-zinc-600 mt-1">
                  Invited for: {departmentLabel(inviteData.department)}
                </p>
              )}
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-zinc-500 mb-1.5">
              Your handle
            </label>
            <div className="flex items-center px-3.5 py-2.5 border border-[var(--border-default)] rounded-xl bg-[var(--bg-void)]">
              <span className="text-zinc-600 mr-1">@</span>
              <input
                name="userSlug"
                type="text"
                required
                value={formData.userSlug}
                onChange={handleSlugChange}
                className="w-full bg-transparent text-sm text-zinc-200 outline-none"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 px-4 rounded-xl text-sm font-bold text-black bg-amber-500 hover:bg-amber-400 disabled:opacity-50 transition-all shadow-lg shadow-amber-500/10"
          >
            {isSubmitting ? "Joining workspace…" : "Confirm & join team"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function InvitePage({ params }: PageProps) {
  const { companySlug, inviteCode } = use(params);
  return <InviteForm companySlug={companySlug} inviteCode={inviteCode} />;
}

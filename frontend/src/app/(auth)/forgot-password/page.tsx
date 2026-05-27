"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { createClient } from "@/utils/supabase/client";
import { Loader2, ArrowLeft } from "lucide-react";
import AuthSplitLayout from "@/components/auth/AuthSplitLayout";

function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const supabase = createClient();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const redirectTo = `${window.location.origin}/auth/callback?next=${encodeURIComponent("/auth/reset-password")}`;

    const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo,
    });

    if (resetError) {
      setError(resetError.message || "Failed to send reset email.");
      setLoading(false);
      return;
    }

    setSuccess(true);
    setLoading(false);
  };

  return (
    <AuthSplitLayout>
      {/* Header */}
      <div className="fade-in-up">
        <h1
          className="text-[28px] font-semibold text-white tracking-[-0.02em]"
          style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
        >
          Reset password
        </h1>
        <p className="mt-2 text-[14px] text-zinc-500">
          We&apos;ll email you a link to choose a new password.
        </p>
      </div>

      {error && (
        <div className="p-3.5 text-[13px] text-red-400 bg-red-500/[0.06] border border-red-500/15 rounded-lg">
          {error}
        </div>
      )}

      {success ? (
        <div className="space-y-5">
          <div className="p-3.5 text-[13px] text-emerald-400 bg-emerald-500/[0.06] border border-emerald-500/15 rounded-lg">
            Check your inbox for a password reset link. Use the most recent email if you request multiple times.
          </div>
          <Link
            href="/login"
            className="flex items-center justify-center gap-2 w-full py-3 text-[13px] font-medium text-zinc-500 hover:text-zinc-300 transition-colors duration-200"
          >
            <ArrowLeft className="w-4 h-4 shrink-0" /> Back to sign in
          </Link>
        </div>
      ) : (
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="block text-[12px] font-medium text-zinc-500 mb-1.5">
              Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              className="block w-full px-3.5 py-3 border border-white/[0.08] rounded-lg text-[14px] text-zinc-200 bg-white/[0.03] focus:ring-1 focus:ring-amber-500/30 focus:border-amber-500/30 outline-none transition-all duration-200 placeholder:text-zinc-700"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-lg text-[14px] font-semibold text-black bg-amber-500 hover:bg-amber-400 focus:outline-none disabled:opacity-50 disabled:cursor-wait transition-all duration-200 shadow-lg shadow-amber-500/10 cursor-pointer"
          >
            {loading ? "Sending…" : "Send reset link"}
          </button>
          <Link
            href="/login"
            className="flex items-center justify-center gap-2 text-[13px] font-medium text-zinc-600 hover:text-zinc-400 transition-colors duration-200"
          >
            <ArrowLeft className="w-4 h-4 shrink-0" /> Back to sign in
          </Link>
        </form>
      )}
    </AuthSplitLayout>
  );
}

export default function ForgotPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center bg-[var(--bg-void)]">
          <Loader2 className="w-5 h-5 animate-spin text-amber-500" />
        </div>
      }
    >
      <ForgotPasswordForm />
    </Suspense>
  );
}

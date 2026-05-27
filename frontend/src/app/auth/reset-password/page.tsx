"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/utils/supabase/client";
import { Loader2 } from "lucide-react";
import AuthSplitLayout from "@/components/auth/AuthSplitLayout";

function ResetPasswordForm() {
  const router = useRouter();
  const supabase = createClient();

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const [hasSession, setHasSession] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setHasSession(!!session);
      setCheckingSession(false);
    });
  }, [supabase]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    const { error: updateError } = await supabase.auth.updateUser({ password });

    if (updateError) {
      setError(updateError.message || "Failed to update password.");
      setLoading(false);
      return;
    }

    router.push("/auth/resolve");
  };

  if (checkingSession) {
    return (
      <div className="flex h-screen items-center justify-center bg-[var(--bg-void)]">
        <Loader2 className="w-5 h-5 animate-spin text-amber-500" />
      </div>
    );
  }

  if (!hasSession) {
    return (
      <AuthSplitLayout>
        <div className="space-y-4 text-center fade-in-up">
          <p className="text-[14px] text-zinc-400">
            This reset link is invalid or has expired. Request a new one from the sign-in page.
          </p>
          <Link
            href="/forgot-password"
            className="inline-block text-[13px] font-medium text-amber-500 hover:text-amber-400 transition-colors duration-200"
          >
            Request new reset link
          </Link>
        </div>
      </AuthSplitLayout>
    );
  }

  return (
    <AuthSplitLayout>
      {/* Header */}
      <div className="fade-in-up">
        <h1
          className="text-[28px] font-semibold text-white tracking-[-0.02em]"
          style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
        >
          New password
        </h1>
        <p className="mt-2 text-[14px] text-zinc-500">
          Choose a secure new password for your account.
        </p>
      </div>

      {error && (
        <div className="p-3.5 text-[13px] text-red-400 bg-red-500/[0.06] border border-red-500/15 rounded-lg">
          {error}
        </div>
      )}

      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <label className="block text-[12px] font-medium text-zinc-500 mb-1.5">
            New password
          </label>
          <input
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="block w-full px-3.5 py-3 border border-white/[0.08] rounded-lg text-[14px] text-zinc-200 bg-white/[0.03] focus:ring-1 focus:ring-amber-500/30 focus:border-amber-500/30 outline-none transition-all duration-200 placeholder:text-zinc-700"
            placeholder="••••••••"
          />
        </div>
        <div>
          <label className="block text-[12px] font-medium text-zinc-500 mb-1.5">
            Confirm password
          </label>
          <input
            type="password"
            required
            minLength={6}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className="block w-full px-3.5 py-3 border border-white/[0.08] rounded-lg text-[14px] text-zinc-200 bg-white/[0.03] focus:ring-1 focus:ring-amber-500/30 focus:border-amber-500/30 outline-none transition-all duration-200 placeholder:text-zinc-700"
            placeholder="••••••••"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 px-4 rounded-lg text-[14px] font-semibold text-black bg-amber-500 hover:bg-amber-400 focus:outline-none disabled:opacity-50 disabled:cursor-wait transition-all duration-200 shadow-lg shadow-amber-500/10 cursor-pointer"
        >
          {loading ? "Updating…" : "Update password"}
        </button>
      </form>
    </AuthSplitLayout>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center bg-[var(--bg-void)]">
          <Loader2 className="w-5 h-5 animate-spin text-amber-500" />
        </div>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}

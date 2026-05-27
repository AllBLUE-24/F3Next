'use client';

import React, { Suspense, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { createClient } from '@/utils/supabase/client';
import { Loader2 } from 'lucide-react';
import AuthSplitLayout from '@/components/auth/AuthSplitLayout';

export const dynamic = 'force-dynamic';

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectPath = searchParams.get('redirect');
  const callbackError = searchParams.get('error');

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [infoMessage, setInfoMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [needsEmailConfirmation, setNeedsEmailConfirmation] = useState(false);
  const supabase = createClient();

  const callbackErrorMessage = useMemo(() => {
    if (callbackError === 'auth_callback_failed') {
      return 'Authentication callback failed. Please try again.';
    }

    if (callbackError === 'email_confirmation_failed') {
      return 'Email confirmation failed. Request a new verification email and try again.';
    }

    return '';
  }, [callbackError]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setInfoMessage('');
    setNeedsEmailConfirmation(false);
    setLoading(true);

    const { data, error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (authError || !data.user) {
      console.error('[Login] Error:', authError);

      if (authError?.message?.includes('Email not confirmed')) {
        setNeedsEmailConfirmation(true);
        setError('Your email is not verified yet.');
      } else {
        setError('Invalid email or password.');
      }

      setLoading(false);
      return;
    }

    if (redirectPath) {
      router.push(
        `${redirectPath}${redirectPath.includes('?') ? '&' : '?'}return=true`
      );
    } else {
      router.push('/auth/resolve');
    }
  };

  const handleResendVerification = async () => {
    if (!email) {
      setError('Enter your email address first.');
      return;
    }

    setError('');
    setInfoMessage('');
    setLoading(true);

    const { error: resendError } = await supabase.auth.resend({
      type: 'signup',
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/confirm`,
      },
    });

    if (resendError) {
      console.error('[Login] Resend verification error:', resendError);
      setError(resendError.message || 'Failed to resend verification email.');
    } else {
      setInfoMessage('Verification email sent. Use the newest email only.');
    }

    setLoading(false);
  };

  const handleGoogleSignIn = async () => {
    setError('');
    setInfoMessage('');
    setNeedsEmailConfirmation(false);
    setLoading(true);

    const { error: authError } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    if (authError) {
      console.error('[Login] Google OAuth error:', authError);
      setError(authError.message || 'Google sign-in failed.');
      setLoading(false);
    }
  };

  const displayError = error || callbackErrorMessage;

  return (
    <AuthSplitLayout>
      {/* Header */}
      <div className="fade-in-up">
        <h1
          className="text-[28px] font-semibold text-white tracking-[-0.02em]"
          style={{ fontFamily: 'var(--font-outfit), sans-serif' }}
        >
          Welcome back
        </h1>
        <p className="mt-2 text-[14px] text-zinc-500">
          Sign in to your F3Next account
        </p>
      </div>

      {/* Errors & Messages */}
      {displayError && (
        <div className="p-3.5 text-[13px] text-red-400 bg-red-500/[0.06] border border-red-500/15 rounded-lg">
          {displayError}
        </div>
      )}

      {infoMessage && (
        <div className="p-3.5 text-[13px] text-emerald-400 bg-emerald-500/[0.06] border border-emerald-500/15 rounded-lg">
          {infoMessage}
        </div>
      )}

      {/* Google OAuth */}
      <button
        onClick={handleGoogleSignIn}
        disabled={loading}
        type="button"
        className="flex items-center justify-center w-full px-4 py-3 text-[13px] font-medium text-white bg-white/[0.06] border border-white/[0.08] rounded-lg hover:bg-white/[0.1] hover:border-white/[0.12] focus:outline-none transition-all duration-200 disabled:opacity-50 cursor-pointer"
      >
        <svg className="w-4 h-4 mr-2.5 shrink-0" viewBox="0 0 24 24">
          <path
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            fill="#4285F4"
          />
          <path
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            fill="#34A853"
          />
          <path
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            fill="#FBBC05"
          />
          <path
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            fill="#EA4335"
          />
        </svg>
        Continue with Google
      </button>

      {/* Divider */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full h-px bg-white/[0.06]" />
        </div>
        <div className="relative flex justify-center">
          <span className="px-3 bg-[#09090B] text-[11px] text-zinc-600">
            or
          </span>
        </div>
      </div>

      {/* Email Form */}
      <form className="space-y-4" onSubmit={handleLogin}>
        <div>
          <label className="block text-[12px] font-medium text-zinc-500 mb-1.5">
            Email
          </label>
          <input
            type="email"
            required
            className="block w-full px-3.5 py-3 border border-white/[0.08] rounded-lg text-[14px] text-zinc-200 bg-white/[0.03] focus:ring-1 focus:ring-amber-500/30 focus:border-amber-500/30 outline-none transition-all duration-200 placeholder:text-zinc-700"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="block text-[12px] font-medium text-zinc-500">
              Password
            </label>
            <Link
              href="/forgot-password"
              className="text-[11px] font-medium text-zinc-600 hover:text-zinc-400 transition-colors duration-200"
            >
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              required
              className="block w-full px-3.5 py-3 pr-14 border border-white/[0.08] rounded-lg text-[14px] text-zinc-200 bg-white/[0.03] focus:ring-1 focus:ring-amber-500/30 focus:border-amber-500/30 outline-none transition-all duration-200 placeholder:text-zinc-700"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button
              type="button"
              onClick={() => setShowPassword((value) => !value)}
              className="absolute inset-y-0 right-0 px-3.5 text-[12px] font-medium text-zinc-600 hover:text-zinc-400 transition-colors duration-200 cursor-pointer"
            >
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 px-4 rounded-lg text-[14px] font-semibold text-black bg-amber-500 hover:bg-amber-400 focus:outline-none disabled:opacity-50 disabled:cursor-wait transition-all duration-200 shadow-lg shadow-amber-500/10 cursor-pointer"
        >
          {loading ? 'Signing in...' : 'Sign in'}
        </button>
      </form>

      {needsEmailConfirmation && (
        <button
          type="button"
          onClick={handleResendVerification}
          disabled={loading}
          className="w-full py-3 px-4 border border-white/[0.08] rounded-lg text-[13px] font-medium text-zinc-400 hover:bg-white/[0.04] disabled:opacity-50 disabled:cursor-wait transition-all duration-200 cursor-pointer"
        >
          {loading ? 'Sending...' : 'Resend verification email'}
        </button>
      )}

      <p className="text-center text-[13px] text-zinc-600">
        Don&apos;t have an account?{' '}
        <Link
          href={redirectPath ? `/signup?redirect=${redirectPath}` : '/signup'}
          className="font-medium text-amber-500 hover:text-amber-400 transition-colors duration-200"
        >
          Sign up
        </Link>
      </p>
    </AuthSplitLayout>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center bg-[var(--bg-void)]">
          <Loader2 className="w-5 h-5 animate-spin text-amber-500" />
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}

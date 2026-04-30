'use client';

import React, { Suspense, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { createClient } from '@/utils/supabase/client';
import { Bot, Loader2 } from 'lucide-react';

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
    <div className="flex items-center justify-center min-h-screen bg-[var(--bg-void)]">
      {/* Subtle grid background */}
      <div className="absolute inset-0 void-grid opacity-40" />

      <div className="relative w-full max-w-md p-8 space-y-6 surface-card fade-in-up" style={{ borderRadius: 'var(--radius-xl)' }}>
        {/* Logo */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-amber-500 rounded-2xl mb-4 shadow-lg shadow-amber-500/20">
            <Bot className="w-6 h-6 text-black" />
          </div>
          <h2 className="text-2xl font-bold text-white">
            Welcome Back
          </h2>
          <p className="mt-1.5 text-sm text-zinc-500">
            Sign in to access your F3Next dashboard
          </p>
        </div>

        {displayError && (
          <div className="p-3 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl">
            {displayError}
          </div>
        )}

        {infoMessage && (
          <div className="p-3 text-sm text-green-400 bg-green-500/10 border border-green-500/20 rounded-xl">
            {infoMessage}
          </div>
        )}

        <button
          onClick={handleGoogleSignIn}
          disabled={loading}
          type="button"
          className="flex items-center justify-center w-full px-4 py-2.5 text-sm font-medium text-zinc-300 bg-white/[0.04] border border-[var(--border-default)] rounded-xl hover:bg-white/[0.08] focus:outline-none transition-all disabled:opacity-50"
        >
          <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
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
          Sign in with Google
        </button>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[var(--border-subtle)]" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-3 bg-[var(--bg-card)] text-zinc-600 text-xs">
              Or continue with email
            </span>
          </div>
        </div>

        <form className="space-y-4" onSubmit={handleLogin}>
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-zinc-500 mb-1.5">
              Email
            </label>
            <input
              type="email"
              required
              className="block w-full px-3.5 py-2.5 border border-[var(--border-default)] rounded-xl text-sm text-zinc-200 bg-[var(--bg-void)] focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500/40 outline-none transition-all placeholder:text-zinc-700"
              placeholder="user@f3next.in"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-zinc-500 mb-1.5">
              Password
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                className="block w-full px-3.5 py-2.5 pr-16 border border-[var(--border-default)] rounded-xl text-sm text-zinc-200 bg-[var(--bg-void)] focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500/40 outline-none transition-all placeholder:text-zinc-700"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowPassword((value) => !value)}
                className="absolute inset-y-0 right-0 px-3 text-xs font-medium text-zinc-600 hover:text-zinc-400 transition-colors"
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl text-sm font-bold text-black bg-amber-500 hover:bg-amber-400 focus:outline-none disabled:opacity-50 disabled:cursor-wait transition-all shadow-lg shadow-amber-500/10"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        {needsEmailConfirmation && (
          <button
            type="button"
            onClick={handleResendVerification}
            disabled={loading}
            className="w-full py-2.5 px-4 border border-[var(--border-default)] rounded-xl text-sm font-medium text-zinc-400 bg-white/[0.03] hover:bg-white/[0.06] disabled:opacity-50 disabled:cursor-wait transition-all"
          >
            {loading ? 'Sending...' : 'Resend verification email'}
          </button>
        )}

        <p className="text-center text-xs text-zinc-600">
          Don&apos;t have an account?{' '}
          <Link
            href={redirectPath ? `/signup?redirect=${redirectPath}` : '/signup'}
            className="font-medium text-amber-400 hover:text-amber-300 transition-colors"
          >
            Sign up
          </Link>
        </p>
      </div>
    </div>
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

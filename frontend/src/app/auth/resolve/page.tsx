'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/utils/supabase/client';

interface ResolveUserResponse {
  company_slug?: string;
  user_slug?: string;
}

/**
 * /auth/resolve — The single source of truth for post-authentication routing.
 *
 * This page is responsible for:
 * 1. Getting the current user from Supabase
 * 2. Calling the backend to resolve their company/user slugs
 * 3. Routing them to the correct destination
 *
 * This cleanly separates "authentication" (handled by Supabase + middleware)
 * from "business routing" (handled here via the backend resolve endpoint).
 */
export default function AuthResolvePage() {
  const router = useRouter();
  const supabase = createClient();
  const [error, setError] = useState('');
  const [retrying, setRetrying] = useState(false);

  const resolveAndRedirect = async () => {
    setError('');
    setRetrying(true);

    try {
      const {
        data: { user },
        error: authError,
      } = await supabase.auth.getUser();

      if (authError || !user) {
        console.error('[Resolve] No user found:', authError);
        router.replace('/login');
        return;
      }

      const res = await fetch(`/api/resolve/user/${user.id}`);

      if (res.ok) {
        const data: ResolveUserResponse = await res.json();

        if (data.company_slug && data.user_slug) {
          router.replace(`/${data.company_slug}/${data.user_slug}/home`);
        } else {
          router.replace('/onboarding');
        }
      } else if (res.status === 404) {
        router.replace('/onboarding');
      } else {
        throw new Error(`Backend returned ${res.status}`);
      }
    } catch (err: unknown) {
      console.error('[Resolve] Error:', err);
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to load your workspace. Please try again.'
      );
      setRetrying(false);
    }
  };

  useEffect(() => {
    resolveAndRedirect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="w-full max-w-sm p-8 text-center">
        {error ? (
          <div className="space-y-4">
            <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md">
              {error}
            </div>
            <button
              onClick={resolveAndRedirect}
              disabled={retrying}
              className="w-full py-2 px-4 rounded-lg text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-70 disabled:cursor-wait"
            >
              {retrying ? 'Retrying...' : 'Try Again'}
            </button>
            <button
              onClick={() => router.replace('/login')}
              className="w-full py-2 px-4 rounded-lg text-sm font-medium text-gray-600 hover:text-gray-800"
            >
              Back to Login
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto" />
            <p className="text-sm text-gray-500">Loading your workspace...</p>
          </div>
        )}
      </div>
    </div>
  );
}

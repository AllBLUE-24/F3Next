'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function DevTestPage() {
  const router = useRouter();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/dev/create-test-session`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed');
        const targetUrl = data.url?.startsWith('/') ? data.url : `/${data.url}`;
        setUrl(targetUrl);
        setStatus('success');
        router.replace(targetUrl);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to create test session');
        setStatus('error');
      }
    })();
  }, [router]);

  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-center text-white">
          <div className="animate-spin w-10 h-10 border-2 border-amber-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p>Creating test session...</p>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <p className="text-zinc-500 text-sm mb-6">Make sure the backend is running on port 8000.</p>
          <Link href="/" className="text-amber-500 hover:text-amber-400">← Back to landing</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <p className="text-white">Redirecting...</p>
    </div>
  );
}

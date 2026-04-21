// PATH: src/app/[companySlug]/[userSlug]/(implementation)/sandbox/page.tsx

import { redirect } from 'next/navigation';
import { ImplementationServerProvider } from '@/components/implementation/ImplementationServerProvider';
import { SandboxView } from '@/components/implementation/sandbox/SandboxView';
import type { SandboxInstance } from '@/types/implementation';

export const metadata = { title: 'Sandbox — F3Next' };

// ── Dev mock ──────────────────────────────────────────────────────────────────
const DEV_SANDBOX: SandboxInstance = {
  url: 'https://sandbox-dev.erpnext.f3next.in',
  username: 'Administrator',
  password: 'f3next@dev123',
  expiresAt: new Date(Date.now() + 20 * 60 * 60 * 1000).toISOString(), // 20 hours from now
  isApproved: false,
};
// ─────────────────────────────────────────────────────────────────────────────

async function fetchSandbox(companySlug: string): Promise<SandboxInstance | null> {
  try {
    const base = 'http://backend_api:8000';
    const res = await fetch(
      `${base}/api/implementation/sandbox/${companySlug}`,
      { cache: 'no-store', headers: { 'x-internal-secret': process.env.INTERNAL_SECRET! } }
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function approveForProduction(formData: FormData) {
  'use server';
  const base = 'http://backend_api:8000';
  const res = await fetch(`${base}/api/implementation/signal/sandbox-approved`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-internal-secret': process.env.INTERNAL_SECRET!,
    },
    body: JSON.stringify({ 
      project_id: formData.get('jobId'), 
      company_slug: formData.get('companySlug'),
      erpnext_base_url: "https://sandbox-dev.erpnext.f3next.in",
      erpnext_api_key: "dev-mock-key",
      dry_run: false
    }),
  });
  if (!res.ok) throw new Error('Approval failed');
}

interface Props {
  params: Promise<{ companySlug: string; userSlug: string }>;
  searchParams: Promise<{ jobId?: string }>;
}

export default async function SandboxPage({ params, searchParams }: Props) {
  const { companySlug, userSlug } = await params;
  const { jobId } = await searchParams;
  const isDev = process.env.NODE_ENV === 'development';

  const sandbox = !isDev
    ? await fetchSandbox(companySlug)
    : (await fetchSandbox(companySlug)) ?? DEV_SANDBOX;

  if (!sandbox || !jobId) redirect(`/${companySlug}/${userSlug}/validate`);

  return (
    <ImplementationServerProvider companySlug={companySlug} userSlug={userSlug}>
      <SandboxView
        jobId={jobId}
        sandbox={sandbox}
        companySlug={companySlug}
        approveAction={approveForProduction}
      />
    </ImplementationServerProvider>
  );
}
import { redirect } from 'next/navigation';
import { ImportView } from '@/components/implementation/import/ImportView';
import type { LiveInstance } from '@/types/implementation';
import { getBaseApiUrl } from '@/lib/config';
import { getProjectContext } from '@/lib/context/project-context';

export const metadata = { title: 'Import — F3Next' };

async function fetchDeployment(companySlug: string): Promise<LiveInstance | null> {
  try {
    const base = getBaseApiUrl();
    const res = await fetch(`${base}/api/deployment/slug/${companySlug}`, {
      cache: 'no-store',
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (!data.instanceUrl) return null;
    return {
      url: data.instanceUrl,
      username: data.userId || 'Administrator',
      password: data.adminPassword || '',
      isApproved: false,
    };
  } catch {
    return null;
  }
}

async function approveForImport(formData: FormData) {
  'use server';
  const base = getBaseApiUrl();
  const res = await fetch(`${base}/api/implementation/signal/sandbox-approved`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id: formData.get('jobId'),
      dry_run: false,
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    const msg = errorData?.detail || errorData?.message || res.statusText;
    throw new Error(`Import approval failed: ${msg}`);
  }
}

interface Props {
  params: Promise<{ companySlug: string; userSlug: string }>;
  searchParams: Promise<{ jobId?: string }>;
}

export default async function ImportPage({ params, searchParams }: Props) {
  const { companySlug, userSlug } = await params;
  let { jobId } = await searchParams;

  if (!jobId) {
    const context = await getProjectContext(companySlug);
    jobId = context.project_id;
  }

  const instance = await fetchDeployment(companySlug);
  if (!instance) {
    redirect(`/${companySlug}/${userSlug}/validate?jobId=${jobId}`);
  }

  return (
    <ImportView
      jobId={jobId}
      companySlug={companySlug}
      instance={instance}
      approveAction={approveForImport}
    />
  );
}

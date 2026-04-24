// PATH: src/app/[companySlug]/[userSlug]/(implementation)/validate/page.tsx

import { redirect } from 'next/navigation';
import { ImplementationServerProvider } from '@/components/implementation/ImplementationServerProvider';
import { ValidateView } from '@/components/implementation/validate/ValidateView';
import type { ValidatePreviewData } from '@/lib/api/implementation_api';
import { getBaseApiUrl } from '@/lib/config';

export const metadata = { title: 'Review & Validate — F3Next' };


async function fetchPreviewData(projectId: string): Promise<ValidatePreviewData | null> {
  try {
    const base = getBaseApiUrl();
    const res = await fetch(
      `${base}/api/implementation/validate-preview/${projectId}`,
      { cache: 'no-store' }
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function submitValidation(formData: FormData) {
  'use server';
  const base = getBaseApiUrl();
  const res = await fetch(`${base}/api/implementation/signal/validation-submitted`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      project_id:   formData.get('jobId'),
      responses:    JSON.parse(formData.get('responses') as string || '{}'),
      profile_edits: JSON.parse(formData.get('profileEdits') as string || '{}'),
      note:         formData.get('note') || '',
    }),
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => null); 
    const backendMessage = errorData?.detail || errorData?.message || res.statusText;
    throw new Error(`Validation failed: ${backendMessage}`);
  }
}

async function submitImport(formData: FormData) {
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
    const backendMessage = errorData?.detail || errorData?.message || res.statusText;
    throw new Error(`Import approval failed: ${backendMessage}`);
  }
}

interface Props {
  params: Promise<{ companySlug: string; userSlug: string }>;
  searchParams: Promise<{ jobId?: string }>;
}

export default async function ValidatePage({ params, searchParams }: Props) {
  const { companySlug, userSlug } = await params;
  const { jobId } = await searchParams;

  if (!jobId) {
    redirect(`/${companySlug}/${userSlug}/analyze`);
  }

  const preview = await fetchPreviewData(jobId);

  if (!preview || preview.doctypes.length === 0) {
    // No data yet — redirect back to analyze
    redirect(`/${companySlug}/${userSlug}/analyze?jobId=${jobId}`);
  }

  return (
    <ImplementationServerProvider companySlug={companySlug} userSlug={userSlug}>
      <ValidateView
        jobId={jobId}
        preview={preview}
        submitValidation={submitValidation}
        submitImport={submitImport}
        sandboxHref={`/${companySlug}/${userSlug}/sandbox?jobId=${jobId}`}
        companySlug={companySlug}
      />
    </ImplementationServerProvider>
  );
}
// PATH: src/app/[companySlug]/[userSlug]/(implementation)/validate/page.tsx

import { redirect } from 'next/navigation';
import { ValidateView } from '@/components/implementation/validate/ValidateView';
import type { ValidatePreviewData } from '@/lib/api/implementation_api';
import { getBaseApiUrl } from '@/lib/config';
import { getProjectContext } from '@/lib/context/project-context';

export const metadata = { title: 'Review & Validate — F3Next' };

async function fetchPreviewData(projectId: string): Promise<ValidatePreviewData | null> {
  try {
    const base = getBaseApiUrl();
    const res = await fetch(
      `${base}/api/implementation/validate-preview/${projectId}`,
      { cache: 'no-store' },
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
      project_id: formData.get('jobId'),
      responses: JSON.parse((formData.get('responses') as string) || '{}'),
      profile_edits: JSON.parse((formData.get('profileEdits') as string) || '{}'),
      note: formData.get('note') || '',
    }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => null);
    const backendMessage = errorData?.detail || errorData?.message || res.statusText;
    throw new Error(`Validation failed: ${backendMessage}`);
  }
}

interface Props {
  params: Promise<{ companySlug: string; userSlug: string }>;
  searchParams: Promise<{ jobId?: string }>;
}

export default async function ValidatePage({ params, searchParams }: Props) {
  const { companySlug, userSlug } = await params;
  let { jobId } = await searchParams;

  if (!jobId) {
    const context = await getProjectContext(companySlug);
    jobId = context.project_id;
  }

  const preview = await fetchPreviewData(jobId);

  if (!preview || preview.doctypes.length === 0) {
    redirect(`/${companySlug}/${userSlug}/analyze?jobId=${jobId}`);
  }

  return (
    <ValidateView
      jobId={jobId}
      preview={preview}
      submitValidation={submitValidation}
      importHref={`/${companySlug}/${userSlug}/import?jobId=${jobId}`}
      companySlug={companySlug}
    />
  );
}

import { UploadView } from '@/components/implementation/upload/UploadView';
import { getBaseApiUrl } from '@/lib/config';

export const metadata = { title: 'Upload Files — F3Next' };

// Action 1: Ask FastAPI for secure R2 upload URLs
export async function getPresignedUrls(projectId: string, fileNames: string[]) {
  'use server';
  const base = getBaseApiUrl();
  
  const res = await fetch(`${base}/api/implementation/presigned-urls`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'x-internal-secret': process.env.INTERNAL_SECRET! 
    },
    body: JSON.stringify({ project_id: projectId, file_names: fileNames }),
  });

  if (!res.ok) throw new Error('Failed to generate upload URLs');
  return res.json(); 
}

// Action 2: Tell FastAPI/Temporal the files are in R2
// Action 2: Tell FastAPI/Temporal the files are in R2
export async function signalUploadComplete(
  projectId: string,
  companySlug: string,
  uploadedFiles: { file_name: string, object_path: string }[],
  userNote: string = ""
) {
  'use server';
  const base = getBaseApiUrl();
  
  // 👇 1. WE ADDED THIS: Tell FastAPI to start the Temporal workflow first! 👇
  const startRes = await fetch(`${base}/api/implementation/start/${projectId}`, {
    method: 'POST',
    headers: { 'x-internal-secret': process.env.INTERNAL_SECRET! }
  });

  const startBody = startRes.ok ? await startRes.json().catch(() => ({})) : null;
  if (!startRes.ok) {
    const detail = typeof startBody === 'object' && startBody && 'detail' in startBody
      ? String((startBody as { detail?: string }).detail)
      : `HTTP ${startRes.status}`;
    throw new Error(`Failed to start implementation workflow: ${detail}`);
  }

  // Brief pause so persist_session can create is_sessions before we signal.
  if (startBody?.started) {
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }

  const res = await fetch(`${base}/api/implementation/signal/files-uploaded`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'x-internal-secret': process.env.INTERNAL_SECRET! 
    },
    body: JSON.stringify({
      project_id: projectId,
      uploaded_files: uploadedFiles,
      company_slug: companySlug,
      user_note: userNote,
    }),
  });

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    const detail = typeof errBody === 'object' && errBody && 'detail' in errBody
      ? String((errBody as { detail?: string }).detail)
      : `HTTP ${res.status}`;
    throw new Error(detail || 'Failed to signal Temporal workflow');
  }
  return res.json();
}


import { getProjectContext } from "@/lib/context/project-context";
import { notFound } from "next/navigation";

interface Props {
  params: Promise<{ companySlug: string; userSlug: string }>;
}

export default async function UploadPage({ params }: Props) {
  const { companySlug, userSlug } = await params;

  if (!companySlug) return notFound();

  // Grab the Universal Project Context to fetch the Project ID
  const context = await getProjectContext(companySlug);

  return (
    <UploadView
      projectId={context.project_id}
      getPresignedUrls={getPresignedUrls}
      signalUploadComplete={signalUploadComplete}
      analyzeHref={`/${companySlug}/${userSlug}/analyze`}
    />
  );
}
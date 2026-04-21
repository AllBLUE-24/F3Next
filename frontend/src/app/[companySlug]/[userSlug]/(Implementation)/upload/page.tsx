import { ImplementationServerProvider } from '@/components/implementation/ImplementationServerProvider';
import { UploadView } from '@/components/implementation/upload/UploadView';

export const metadata = { title: 'Upload Files — F3Next' };

// Action 1: Ask FastAPI for secure R2 upload URLs
export async function getPresignedUrls(projectId: string, fileNames: string[]) {
  'use server';
  const base = 'http://backend_api:8000';
  
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
export async function signalUploadComplete(projectId: string, companySlug: string, uploadedFiles: { file_name: string, object_path: string }[]) {
  'use server';
  const base = 'http://backend_api:8000';
  
  // 👇 1. WE ADDED THIS: Tell FastAPI to start the Temporal workflow first! 👇
  const startRes = await fetch(`${base}/api/implementation/start/${projectId}`, {
    method: 'POST',
    headers: { 'x-internal-secret': process.env.INTERNAL_SECRET! }
  });

  if (!startRes.ok) {
    console.error("Warning: Failed to start workflow (it might already be running)");
  }

  // 👇 2. YOUR EXISTING CODE: Now send the files to the running workflow 👇
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
    }),
  });

  if (!res.ok) throw new Error('Failed to signal Temporal workflow');
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
    <ImplementationServerProvider companySlug={companySlug} userSlug={userSlug}>
      <UploadView
        projectId={context.project_id}
        getPresignedUrls={getPresignedUrls}
        signalUploadComplete={signalUploadComplete}
        analyzeHref={`/${companySlug}/${userSlug}/analyze`}
      />
    </ImplementationServerProvider>
  );
}
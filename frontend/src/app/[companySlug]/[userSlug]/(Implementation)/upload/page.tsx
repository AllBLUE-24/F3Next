import { ImplementationServerProvider } from '@/components/implementation/ImplementationServerProvider';
import { UploadView } from '@/components/implementation/upload/UploadView';

export const metadata = { title: 'Upload Files — F3Next' };

async function uploadFiles(formData: FormData): Promise<{ jobId: string }> {
  'use server';
  const base = process.env.NEXT_PUBLIC_API_URL || process.env.API_BASE_URL || "http://localhost:8000";
  const res = await fetch(`${base}/implementation/upload`, {
    method: 'POST',
    headers: { 'x-internal-secret': process.env.INTERNAL_SECRET! },
    body: formData,
  });
  if (!res.ok) throw new Error('Upload failed');
  return res.json();
}

interface Props {
  params: Promise<{ companySlug: string; userSlug: string }>;
}

export default async function UploadPage({ params }: Props) {
  const { companySlug, userSlug } = await params;

  return (
    <ImplementationServerProvider companySlug={companySlug} userSlug={userSlug}>
      <UploadView
        uploadAction={uploadFiles}
        analyzeHref={`/${companySlug}/${userSlug}/analyze`}
      />
    </ImplementationServerProvider>
  );
}

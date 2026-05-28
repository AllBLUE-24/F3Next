import { redirect } from 'next/navigation';

interface Props {
  params: Promise<{ companySlug: string; userSlug: string }>;
  searchParams: Promise<{ jobId?: string }>;
}

/** Legacy route — redirects to /import */
export default async function SandboxRedirectPage({ params, searchParams }: Props) {
  const { companySlug, userSlug } = await params;
  const { jobId } = await searchParams;
  const q = jobId ? `?jobId=${encodeURIComponent(jobId)}` : '';
  redirect(`/${companySlug}/${userSlug}/import${q}`);
}

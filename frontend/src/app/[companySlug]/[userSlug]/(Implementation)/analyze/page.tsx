// PATH: src/app/[companySlug]/[userSlug]/(implementation)/analyze/page.tsx

import { redirect } from 'next/navigation';
import { AnalyzeView } from '@/components/implementation/analyze/AnalyzeView';
import type { AnalysisTask } from '@/types/implementation';

export const metadata = { title: 'Analyzing Your Data — F3Next' };

// ── Dev mock ──────────────────────────────────────────────────────────────────
const DEV_JOB_ID = 'dev-job-001';

const DEV_TASKS: AnalysisTask[] = [
  { id: '1', label: 'Parsing uploaded files',           status: 'done',    detail: '3 files processed', startedAt: new Date().toISOString(), completedAt: new Date().toISOString() },
  { id: '2', label: 'Detecting file formats',           status: 'done',    detail: 'SQL backup, 2x XLSX', startedAt: new Date().toISOString(), completedAt: new Date().toISOString() },
  { id: '3', label: 'Extracting company metadata',      status: 'done',    detail: 'Found: Middle Ground Pvt Ltd', startedAt: new Date().toISOString(), completedAt: new Date().toISOString() },
  { id: '4', label: 'Mapping chart of accounts',        status: 'running', detail: null, startedAt: new Date().toISOString(), completedAt: null },
  { id: '5', label: 'Detecting inventory structure',    status: 'idle',    detail: null, startedAt: null, completedAt: null },
  { id: '6', label: 'Validating supplier master data',  status: 'idle',    detail: null, startedAt: null, completedAt: null },
  { id: '7', label: 'Building company profile',         status: 'idle',    detail: null, startedAt: null, completedAt: null },
];
// ─────────────────────────────────────────────────────────────────────────────

interface Props {
  params: Promise<{ companySlug: string; userSlug: string }>;
  searchParams: Promise<{ jobId?: string }>;
}

export default async function AnalyzePage({ params, searchParams }: Props) {
  const { companySlug, userSlug } = await params;
  const { jobId } = await searchParams;

  const isDev = process.env.NODE_ENV === 'development';

  // In production: require real jobId. In dev: use mock if none provided.
  if (!jobId && !isDev) redirect(`/${companySlug}/${userSlug}/upload`);

  const resolvedJobId = jobId ?? DEV_JOB_ID;

  return (
    <AnalyzeView
      jobId={resolvedJobId}
      validateHref={`/${companySlug}/${userSlug}/validate`}
      devTasks={isDev && !jobId ? DEV_TASKS : undefined}
    />
  );
}
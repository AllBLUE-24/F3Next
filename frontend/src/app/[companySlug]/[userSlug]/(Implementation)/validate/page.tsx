// PATH: src/app/[companySlug]/[userSlug]/(implementation)/validate/page.tsx

import { redirect } from 'next/navigation';
import { ImplementationServerProvider } from '@/components/implementation/ImplementationServerProvider';
import { ValidateView } from '@/components/implementation/validate/ValidateView';
import type { CompanyProfile, ValidationItem } from '@/types/implementation';

export const metadata = { title: 'Review & Validate — F3Next' };

// ── Dev mock ──────────────────────────────────────────────────────────────────
const DEV_PROFILE: CompanyProfile = {
  name: 'Middle Ground',
  legalName: 'Middle Ground Private Limited',
  industry: 'Manufacturing',
  subIndustry: 'Metal Fabrication',
  size: 'small',
  employeeCount: 48,
  currency: 'INR',
  fiscalYearStart: 'April',
  country: 'India',
  state: 'Maharashtra',
  gstNumber: '27AABCU9603R1ZM',
  modules: ['Stock', 'Purchase', 'Sales', 'Accounts', 'Manufacturing'],
  warehouses: ['Main Warehouse', 'Finished Goods Store'],
  costCenters: ['Production', 'Admin', 'Sales'],
  confidence: 82,
};

const DEV_VALIDATION_ITEMS: ValidationItem[] = [
  {
    id: 'v1',
    type: 'missing',
    field: 'Opening Stock Quantities',
    message: 'We found item master data but no opening stock quantities in any of your files. ERPNext needs these to set initial inventory levels.',
    required: true,
    resolved: false,
    userResponse: null,
  },
  {
    id: 'v2',
    type: 'contradiction',
    field: 'Fiscal Year',
    message: 'Your SQL backup says fiscal year starts in January, but your Excel sheet shows April. Which is correct?',
    required: true,
    resolved: false,
    userResponse: null,
  },
  {
    id: 'v3',
    type: 'missing',
    field: 'Bank Account Details',
    message: 'No bank account or payment account information was found. You can add this after setup if you prefer.',
    required: false,
    resolved: false,
    userResponse: null,
  },
  {
    id: 'v4',
    type: 'suggestion',
    field: 'Cost Center Structure',
    message: 'We detected 3 cost centers. Would you like us to map these to the default ERPNext structure or keep your existing naming?',
    required: false,
    resolved: false,
    userResponse: null,
  },
];
// ─────────────────────────────────────────────────────────────────────────────

async function fetchValidationData(companySlug: string): Promise<{
  profile: CompanyProfile;
  items: ValidationItem[];
} | null> {
  try {
    const base = process.env.NEXT_PUBLIC_API_URL || process.env.API_BASE_URL || 'http://localhost:8000';
    const res = await fetch(
      `${base}/api/implementation/validate/${companySlug}`,
      { cache: 'no-store', headers: { 'x-internal-secret': process.env.INTERNAL_SECRET! } }
    );
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function submitValidation(formData: FormData) {
  'use server';
  const base = process.env.NEXT_PUBLIC_API_URL || process.env.API_BASE_URL || 'http://localhost:8000';
  const res = await fetch(`${base}/api/implementation/signal/validation-submitted`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-internal-secret': process.env.INTERNAL_SECRET!,
    },
    body: JSON.stringify({
      project_id:   formData.get('jobId'), // Maps to project_id in FastAPI
      companySlug:  formData.get('companySlug'),
      responses:    JSON.parse(formData.get('responses') as string),
      profileEdits: JSON.parse(formData.get('profileEdits') as string),
      note:         formData.get('note'),
    }),
  });
  
  if (!res.ok) {
    // 1. Try to extract the JSON error message from your backend
    const errorData = await res.json().catch(() => null); 
    
    // 2. Format a better error message for your console
    const backendMessage = errorData?.detail || errorData?.message || res.statusText;
    
    console.error(`Backend rejected the request with status: ${res.status}`);
    console.error(`Backend error details:`, errorData);
  
    // 3. Throw an error containing the actual backend complaint
    throw new Error(`Validation failed: ${backendMessage}`);
  }
}

interface Props {
  params: Promise<{ companySlug: string; userSlug: string }>;
  searchParams: Promise<{ jobId?: string }>;
}

export default async function ValidatePage({ params, searchParams }: Props) {
  const { companySlug, userSlug } = await params;
  const { jobId } = await searchParams;
  const isDev = process.env.NODE_ENV === 'development';

  // We should actually pass the jobId to fetch the real DB validation result !!
  // For now we'll just fix the immediate 404 submission error:
  const data = !isDev && jobId
    ? await fetchValidationData(jobId) // Changing this from companySlug to jobId!
    : (jobId ? await fetchValidationData(jobId) : null) ?? { profile: DEV_PROFILE, items: DEV_VALIDATION_ITEMS };

  if (!data || !jobId) redirect(`/${companySlug}/${userSlug}/analyze`);

  return (
    <ImplementationServerProvider companySlug={companySlug} userSlug={userSlug}>
      <ValidateView
        jobId={jobId}
        profile={data.profile}
        validationItems={data.items}
        submitAction={submitValidation}
        sandboxHref={`/${companySlug}/${userSlug}/sandbox?jobId=${jobId}`}
        companySlug={companySlug}
      />
    </ImplementationServerProvider>
  );
}
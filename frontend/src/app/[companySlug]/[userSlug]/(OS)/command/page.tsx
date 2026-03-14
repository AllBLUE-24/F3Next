/**
 * frontend/src/app/[companySlug]/[userSlug]/(OS)/command/page.tsx
 */

import React from "react";
import OSShell from "@/components/OS/OSShell";

interface Props {
  // 1. Update types to Promises
  params:       Promise<{ companySlug: string; userSlug: string }>;
  searchParams: Promise<{ project_id?: string; erp_type?: string }>;
}

// 2. Make the component async
export default async function CommandPage({ params, searchParams }: Props) {
  // 3. Await both sets of parameters
  const resolvedParams = await params;
  const resolvedSearchParams = await searchParams;

  const projectId = resolvedSearchParams.project_id ?? resolvedParams.companySlug;
  const erpType   = (resolvedSearchParams.erp_type ?? "erpnext") as "erpnext" | "odoo";

  return (
    <OSShell
      projectId={projectId}
      companyId={resolvedParams.companySlug}
      userId={resolvedParams.userSlug}
      erpType={erpType}
    />
  );
}

// 4. Make metadata async and await params
export async function generateMetadata({ params }: Props) {
  const resolvedParams = await params;
  
  return {
    title: `OS — ${resolvedParams.companySlug}`,
    description: "ERP Operating System — natural language command interface",
  };
}
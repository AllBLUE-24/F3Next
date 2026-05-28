"use client";

import { use } from "react";
import { usePathname } from "next/navigation";
import PrimarySidebar from "@/components/shared/PrimarySidebar";
import { UniversalHeader } from "@/components/shared/UniversalHeader";

export default function WorkspaceLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ companySlug: string; userSlug: string }>;
}) {
  const { companySlug, userSlug } = use(params);
  const pathname = usePathname();

  // Determine if we're in a full-bleed section (OS terminal, etc.)
  const isFullBleed = pathname.includes('/command') || 
                      pathname.includes('/upload') || 
                      pathname.includes('/analyze') || 
                      pathname.includes('/validate') || 
                      pathname.includes('/import') ||
                      pathname.includes('/sandbox') ||
                      pathname.includes('/discovery');

  return (
    <div className="flex h-dvh bg-[var(--bg-void)] text-[var(--text-primary)] font-sans selection:bg-amber-500/20 selection:text-amber-200 overflow-hidden">
      
      {/* ─── Primary Sidebar (Global Nav) ─── */}
      <PrimarySidebar companySlug={companySlug} userSlug={userSlug} />

      {/* ─── Main Content Area ─── */}
      <main className="flex-1 flex flex-col relative min-w-0 bg-[var(--bg-void)] overflow-hidden">
        <UniversalHeader />
        <div className="flex-1 overflow-y-auto w-full flex flex-col">
          {isFullBleed ? (
            children
          ) : (
            <div className="mx-auto max-w-6xl p-6 lg:p-10">
              {children}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
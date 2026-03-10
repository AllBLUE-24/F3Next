// PATH: src/app/[companySlug]/[userSlug]/(implementation)/layout.tsx
// ✅ Static — no async, no fetch, no params. Turbopack-safe.

import { ImplementationShell } from '@/components/implementation/shell/ImplementationShell';

export default function ImplementationLayout({ children }: { children: React.ReactNode }) {
  return (
    <ImplementationShell>
      {children}
    </ImplementationShell>
  );
}
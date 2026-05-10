import { ImplementationShell } from '@/components/implementation/shell/ImplementationShell';
import { ImplementationServerProvider } from "@/components/implementation/ImplementationServerProvider";

interface Props {
  children: React.ReactNode;
  params: Promise<{ companySlug: string; userSlug: string }>;
}

export default async function ImplementationLayout({ children, params }: Props) {
  const { companySlug, userSlug } = await params;
  return (
    <ImplementationServerProvider companySlug={companySlug} userSlug={userSlug}>
      <ImplementationShell>{children}</ImplementationShell>
    </ImplementationServerProvider>
  );
}
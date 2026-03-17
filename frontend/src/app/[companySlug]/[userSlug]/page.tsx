import { redirect } from "next/navigation";

interface Props {
  params: Promise<{ companySlug: string; userSlug: string }>;
}

export default async function UserRootPage({ params }: Props) {
  const { companySlug, userSlug } = await params;
  redirect(`/${companySlug}/${userSlug}/home`);
}

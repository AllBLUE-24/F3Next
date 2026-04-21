"use client";

import { use } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import FloatingAIBubble from "@/components/FloatingAIBubble";
import { LayoutGrid, User, LogOut } from "lucide-react";
import { createClient } from "@/utils/supabase/client";

export default function WorkspaceLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ companySlug: string; userSlug: string }>;
}) {
  const { companySlug, userSlug } = use(params);
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
  };

  const navItems = [
    { name: "Mission Control", href: `/${companySlug}/${userSlug}/home`, icon: LayoutGrid },
    { name: "Profile", href: `/${companySlug}/${userSlug}/profile`, icon: User },
  ];

  return (
    <div className="min-h-dvh bg-[#09090B] text-zinc-100 flex flex-col font-sans selection:bg-amber-500/20 selection:text-amber-200">
      {/* Sleek Minimal Header */}
      <header className="sticky top-0 z-50 flex h-16 items-center justify-between border-b border-white/5 bg-[#09090B]/80 px-6 backdrop-blur-md">
        <div className="flex items-center gap-8">
          <Link href={`/${companySlug}/${userSlug}/home`} className="flex items-center gap-2">
            <span className="text-lg font-black tracking-tight text-white">
              F3<span className="text-amber-500">Next</span>
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-zinc-400">
              Workspace
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-white/10 text-white"
                      : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200"
                  }`}
                >
                  <item.icon className="h-4 w-4" />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden md:block text-right text-xs">
            <p className="text-zinc-500 font-medium uppercase tracking-wider">{companySlug}</p>
            <p className="text-zinc-300 font-semibold">{userSlug}</p>
          </div>
          <div className="h-8 w-px bg-white/10 mx-2 hidden md:block"></div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">Sign Out</span>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl p-6 lg:p-12">
          {children}
        </div>
      </main>

      <FloatingAIBubble />
    </div>
  );
}
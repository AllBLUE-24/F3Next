"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutGrid, LogOut, Bot, UploadCloud, Terminal, Search, User, ChevronsLeft, ChevronsRight } from "lucide-react";
import { signOutAuth } from "@/utils/auth-user";
import { isDevAuthBypassEnabled } from "@/utils/dev-auth";
import { getBaseApiUrl } from "@/lib/config";
import { stageToHref } from "@/lib/implementation-routes";

export default function PrimarySidebar({ companySlug, userSlug }: { companySlug: string; userSlug: string }) {
  const [collapsed, setCollapsed] = useState(false);
  const [implementationHref, setImplementationHref] = useState(`/${companySlug}/${userSlug}/upload`);
  const pathname = usePathname();
  const router = useRouter();

  const base = `/${companySlug}/${userSlug}`;

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const api = getBaseApiUrl();
        const resolveRes = await fetch(`${api}/api/resolve/slug/${companySlug}`, { cache: "no-store" });
        if (!resolveRes.ok) return;
        const { project_id } = await resolveRes.json();
        if (!project_id || cancelled) return;

        const stageRes = await fetch(`${api}/api/implementation/stage/${project_id}`, { cache: "no-store" });
        if (!stageRes.ok) {
          if (!cancelled) setImplementationHref(`${base}/upload`);
          return;
        }
        const { stage } = await stageRes.json();
        if (!cancelled) {
          setImplementationHref(stageToHref(base, stage, project_id));
        }
      } catch {
        if (!cancelled) setImplementationHref(`${base}/upload`);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [companySlug, base]);

  const handleLogout = async () => {
    await signOutAuth();
    router.push(isDevAuthBypassEnabled() ? "/landing" : "/login");
  };

  const navItems = [
    { name: "Home", href: `${base}/home`, icon: LayoutGrid },
    { name: "Discovery", href: `${base}/discovery`, icon: Search },
    { name: "Implementation", href: implementationHref, icon: UploadCloud },
    { name: "OS", href: `${base}/command`, icon: Terminal },
  ];

  const isActiveRoute = (href: string, name: string) => {
    if (name === "Home") return pathname === `${base}/home`;
    if (name === "Discovery") return pathname.includes("/discovery");
    if (name === "Implementation") {
      return (
        pathname.includes("/upload") ||
        pathname.includes("/analyze") ||
        pathname.includes("/validate") ||
        pathname.includes("/import") ||
        pathname.includes("/sandbox")
      );
    }
    if (name === "OS") return pathname.includes("/command");
    return pathname === href;
  };

  return (
    <aside className={`flex flex-col border-r border-[var(--border-subtle)] bg-[var(--bg-shell)] transition-all duration-300 ${collapsed ? "w-20" : "w-64"} shrink-0 relative h-full z-40`}>

      <div className="h-[56px] flex items-center justify-between px-4 border-b border-[var(--border-subtle)] shrink-0 overflow-hidden relative">
        <Link href={`${base}/home`} className={`flex items-center gap-3 group whitespace-nowrap ${collapsed ? "justify-center w-full" : ""}`}>
          <div className="w-7 h-7 rounded-lg bg-amber-500 flex items-center justify-center shrink-0 group-hover:bg-amber-400 transition-colors shadow-lg shadow-amber-500/20">
            <Bot className="w-4 h-4 text-black" />
          </div>
          {!collapsed && (
            <span className="text-lg font-black tracking-tight text-white transition-opacity duration-300">
              F3<span className="text-amber-500">Next</span>
            </span>
          )}
        </Link>

        <button
          onClick={() => setCollapsed(!collapsed)}
          className={`text-zinc-500 hover:text-white hover:bg-white/[0.05] p-1.5 rounded-lg transition-colors z-50 ${collapsed ? "absolute inset-0 opacity-0" : ""}`}
        >
          {collapsed ? <ChevronsRight className="w-4 h-4" /> : <ChevronsLeft className="w-4 h-4" />}
        </button>
      </div>

      {!collapsed && (
        <div className="px-5 py-5 border-b border-[var(--border-subtle)] shrink-0">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center shrink-0">
              <span className="text-sm font-bold text-amber-400 uppercase">{userSlug.charAt(0)}</span>
            </div>
            <div className="overflow-hidden">
              <p className="text-sm font-bold text-white truncate capitalize">{companySlug.replace(/-/g, " ")}</p>
              <p className="text-[11px] text-zinc-500 truncate capitalize mt-0.5">{userSlug.replace(/-/g, " ")}</p>
            </div>
          </div>
        </div>
      )}

      <nav className="flex-1 overflow-y-auto py-5 px-3 space-y-1.5">
        {navItems.map((item) => {
          const active = isActiveRoute(item.href, item.name);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3.5 px-3.5 py-3 rounded-xl transition-all duration-200 group ${
                active ? "bg-amber-500/10 text-amber-400" : "text-zinc-400 hover:bg-white/[0.04] hover:text-white"
              } ${collapsed ? "justify-center" : ""}`}
              title={collapsed ? item.name : undefined}
            >
              <item.icon className={`w-5 h-5 shrink-0 transition-colors ${active ? "text-amber-400" : "text-zinc-500 group-hover:text-zinc-300"}`} />
              {!collapsed && <span className="text-[14px] font-semibold whitespace-nowrap">{item.name}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="p-3 border-t border-[var(--border-subtle)] shrink-0 space-y-1">
        <Link
          href={`${base}/profile`}
          className={`flex items-center gap-3.5 px-3.5 py-3 rounded-xl text-zinc-400 hover:bg-white/[0.04] hover:text-white transition-all group ${
            pathname.includes("/profile") ? "bg-white/[0.04] text-white" : ""
          } ${collapsed ? "justify-center" : ""}`}
          title={collapsed ? "Profile" : undefined}
        >
          <User className="w-5 h-5 shrink-0" />
          {!collapsed && <span className="text-[14px] font-semibold whitespace-nowrap">Profile</span>}
        </Link>
        <button
          onClick={handleLogout}
          className={`w-full flex items-center gap-3.5 px-3.5 py-3 rounded-xl text-zinc-500 hover:bg-red-500/10 hover:text-red-400 transition-all group ${collapsed ? "justify-center" : ""}`}
          title={collapsed ? "Sign Out" : undefined}
        >
          <LogOut className="w-5 h-5 shrink-0" />
          {!collapsed && <span className="text-[14px] font-semibold whitespace-nowrap">Sign Out</span>}
        </button>
      </div>
    </aside>
  );
}

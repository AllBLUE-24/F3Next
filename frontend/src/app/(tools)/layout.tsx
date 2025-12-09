"use client";

import FloatingAIBubble from "@/components/FloatingAIBubble";
import {
  CircleHelp,
  Lightbulb,
  CreditCard,
  Settings,
  FileText,
  Rocket,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useMemo, useState } from "react";
import { usePathname } from "next/navigation";

const interactiveClass = "hover-layer transition-colors duration-200";

const primaryNav = [
  { id: "help", label: "Guide", icon: CircleHelp },
  { id: "ideas", label: "Ideas", icon: Lightbulb },
  { id: "billing", label: "Billing", icon: CreditCard },
  { id: "settings", label: "Settings", icon: Settings },
  { id: "files", label: "Files", icon: FileText },
  { id: "launch", label: "Launch", icon: Rocket },
];

export default function ToolsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [activePrimary, setActivePrimary] = useState(primaryNav[0].id);
  const progressDots = useMemo(() => Array.from({ length: 6 }), []);

  return (
    <main className="relative min-h-dvh overflow-hidden bg-[#030303] text-foreground">
      <div className="pointer-events-none absolute inset-0 opacity-60">
        <div className="h-full w-full bg-[radial-gradient(circle_at_top,#10121d,transparent_55%)]" />
      </div>
      <div className="relative z-10 flex min-h-dvh">
        <div className="flex w-[var(--sidebar-width)] flex-col border-r border-white/5 bg-transparent backdrop-blur">
          <div className="flex h-[var(--header-height)] items-center justify-center border-b border-white/5">
            <div className="rounded-full border border-white/20 px-4 py-1 text-xs uppercase tracking-[0.4em] text-secondary">
              F3
            </div>
          </div>
          <div className="flex flex-1 flex-col items-center gap-4 py-6">
            {primaryNav.map(({ id, label, icon: Icon }) => {
              const isActive = id === activePrimary;
              return (
                <button
                  key={id}
                  aria-label={label}
                  title={label}
                  onClick={() => setActivePrimary(id)}
                  className={`group relative flex h-12 w-12 items-center justify-center rounded-2xl border border-transparent ${interactiveClass} ${
                    isActive ? "bg-white/10 border-white/20" : "hover:border-white/10"
                  }`}
                >
                  <span className="pointer-events-none absolute inset-0 rounded-2xl bg-white/10 opacity-0 blur-lg transition group-hover:opacity-60" />
                  <Icon
                    className={`relative h-5 w-5 ${
                      isActive ? "text-white" : "text-secondary"
                    }`}
                  />
                  {isActive && (
                    <span className="absolute -right-3 top-1/2 h-10 w-1.5 -translate-y-1/2 rounded-full bg-white" />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex min-h-dvh flex-1 flex-col">
          <header className="flex h-[var(--header-height)] items-center justify-between border-b border-white/5 bg-[radial-gradient(circle_at_top,#121624,transparent_80%)] px-6 shadow-[0_25px_60px_rgb(0_0_0/0.6)] lg:px-10">
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-3">
                <span className="nav-label text-sm text-white">F3Next</span>
                <span className="rounded-full border border-white/15 px-3 py-1 text-xs uppercase tracking-[0.3em] text-secondary">
                  Live
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-secondary">
                <span>Workspace health</span>
                <span className="inline-flex items-center gap-1">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-white" />
                  Synced 4m ago
                </span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                className={`hidden items-center gap-2 rounded-full border border-white/15 px-4 py-2 text-sm text-secondary lg:flex ${interactiveClass}`}
              >
                <span className="h-1.5 w-1.5 rounded-full bg-white/60" />
                Search workspace
              </button>
              <div className="flex items-center gap-2">
                {progressDots.map((_, index) => (
                  <span
                    key={index}
                    className={`h-2 w-2 rounded-full transition ${
                      index < 3 ? "bg-white" : "bg-white/30"
                    }`}
                  />
                ))}
              </div>
              <div className="text-right text-xs uppercase text-muted">
                <p>Operator</p>
                <p className="text-sm font-medium tracking-wide text-white">JD</p>
              </div>
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-full bg-white/5 text-xs font-semibold tracking-wide text-white shadow-lg ${interactiveClass}`}
              >
                JD
              </div>
            </div>
          </header>

          <div className="flex-1 overflow-y-auto px-4 pb-12 pt-8 lg:px-12">
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={`${activePrimary}-${pathname}`}
                layoutId="workspace"
                initial={{ x: "100%", opacity: 0 }}
                animate={{ x: "0%", opacity: 1 }}
                exit={{ x: "-10%", opacity: 0 }}
                transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
              >
                {children}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>

      <FloatingAIBubble />
    </main>
  );
}


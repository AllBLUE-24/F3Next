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

const interactiveClass =
  "transition-all duration-200 hover:shadow-2xl hover:-translate-y-1 hover:brightness-110 active:scale-95";

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
    <main className="void-grid min-h-dvh text-foreground">
      <header className="fixed left-0 top-0 z-40 flex h-[var(--header-height)] w-full items-center justify-between border-b border-white/10 bg-[#0a0a0a]/95 px-6 backdrop-blur-md lg:px-12">
        <span className="text-lg font-semibold tracking-[0.3em] text-white">
          F3Next
        </span>
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
        <div className="flex items-center gap-3">
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

      <aside className="fixed left-0 top-[var(--header-height)] z-40 flex h-[calc(100vh-var(--header-height))] w-[var(--sidebar-width)] flex-col items-center border-r border-white/10 bg-[#0a0a0a]">
        <div className="mt-8 flex flex-col items-center gap-4">
          {primaryNav.map(({ id, label, icon: Icon }) => {
            const isActive = id === activePrimary;
            return (
              <button
                key={id}
                aria-label={label}
                title={label}
                onClick={() => setActivePrimary(id)}
                className={`relative flex h-12 w-12 items-center justify-center rounded-2xl ${interactiveClass} ${
                  isActive ? "bg-white/10 shadow-lg" : "border border-transparent"
                }`}
              >
                <Icon
                  className={`h-5 w-5 ${
                    isActive ? "text-white" : "text-secondary"
                  }`}
                />
                {isActive && (
                  <span className="absolute left-0 top-1/2 h-10 w-1 -translate-x-3 -translate-y-1/2 rounded-full bg-white" />
                )}
              </button>
            );
          })}
        </div>
      </aside>

      <div className="relative z-10 min-h-dvh pt-[var(--header-height)]">
        <div className="ml-[var(--sidebar-width)] px-4 pb-16 pt-10 lg:px-14">
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

      <FloatingAIBubble />
    </main>
  );
}


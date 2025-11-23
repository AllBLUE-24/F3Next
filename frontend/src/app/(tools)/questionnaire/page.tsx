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
import { useMemo, useRef, useState } from "react";
import {
  PanelGroup,
  Panel,
  PanelResizeHandle,
  type ImperativePanelHandle,
} from "react-resizable-panels";

const primaryNav = [
  { id: "help", label: "Guide", icon: CircleHelp },
  { id: "ideas", label: "Ideas", icon: Lightbulb },
  { id: "billing", label: "Billing", icon: CreditCard },
  { id: "settings", label: "Settings", icon: Settings },
  { id: "files", label: "Files", icon: FileText },
  { id: "launch", label: "Launch", icon: Rocket },
];

const questionOptions = [
  {
    id: "strategic",
    label: "Strategic scenario planning",
    description: "Map best/worst case while staying within compliance guardrails.",
  },
  {
    id: "ops",
    label: "Operational depth dive",
    description: "Surface hidden blockers in the execution chain.",
  },
  {
    id: "signals",
    label: "Signal triangulation",
    description: "Fuse internal docs, chats, and milestones for a single truth.",
  },
];

const tabs = ["Files", "Chats", "Milestones"] as const;

export default function QuestionnairePage() {
  const [activePrimary, setActivePrimary] = useState("help");
  const [activeTab, setActiveTab] = useState<(typeof tabs)[number]>("Files");
  const [selectedOption, setSelectedOption] = useState("strategic");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const sidebarRef = useRef<ImperativePanelHandle>(null);

  const progressDots = useMemo(() => Array.from({ length: 6 }), []);

  const toggleSidebar = () => {
    if (!sidebarRef.current) return;
    if (sidebarCollapsed) {
      sidebarRef.current.expand();
    } else {
      sidebarRef.current.collapse();
    }
  };

  return (
    <main className="min-h-dvh bg-[var(--bg-void)] text-foreground">
      <header
        className="fixed left-0 top-0 z-20 flex h-[var(--header-height)] w-full items-center justify-between border-b border-subtle bg-[var(--bg-shell)]/90 px-6 backdrop-blur-sm lg:px-12"
        role="banner"
      >
        <span className="text-lg font-semibold tracking-[0.2em]">F3Next</span>
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
          <div className="text-right">
            <p className="text-xs uppercase text-muted">Operator</p>
            <p className="text-sm font-medium tracking-wide text-secondary">
              JD
            </p>
          </div>
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--bg-card)] text-sm font-semibold tracking-wide shadow-lift">
            JD
          </div>
        </div>
      </header>

      <aside
        className="fixed left-0 top-[var(--header-height)] z-20 flex h-[calc(100vh-var(--header-height))] w-[var(--sidebar-width)] flex-col items-center border-r border-subtle bg-[var(--bg-shell)] pt-6"
        aria-label="Primary"
      >
        <div className="flex flex-col items-center gap-4">
          {primaryNav.map(({ id, label, icon: Icon }) => {
            const isActive = id === activePrimary;
            return (
              <button
                key={id}
                aria-label={label}
                title={label}
                onClick={() => setActivePrimary(id)}
                className={`group relative flex h-12 w-12 items-center justify-center rounded-2xl border border-transparent transition-all hover:border-subtle hover:shadow-lift ${
                  isActive ? "bg-[var(--bg-card)]" : "bg-transparent"
                }`}
              >
                <Icon
                  className={`h-5 w-5 ${
                    isActive ? "text-white" : "text-secondary"
                  }`}
                />
                {isActive && (
                  <span className="absolute left-0 top-1/2 h-8 w-1 -translate-x-3 -translate-y-1/2 rounded-full bg-white" />
                )}
              </button>
            );
          })}
        </div>
      </aside>

      <div className="relative z-10 min-h-dvh pt-[var(--header-height)]">
        <div className="ml-[var(--sidebar-width)] px-4 pb-16 pt-10 lg:px-14">
          <PanelGroup
            direction="horizontal"
            className="rounded-[32px] border border-subtle/60 bg-transparent shadow-depth"
          >
            <Panel
              ref={sidebarRef}
              defaultSize={24}
              minSize={16}
              collapsible
              collapsedSize={6}
              onCollapse={() => setSidebarCollapsed(true)}
              onExpand={() => setSidebarCollapsed(false)}
            >
              <div
                className={`flex h-full flex-col border-r border-subtle/40 bg-[var(--bg-shell)]/95 px-4 pb-6 pt-5 backdrop-blur ${
                  sidebarCollapsed ? "items-center" : ""
                }`}
              >
                <div className="flex w-full items-center justify-between gap-3">
                  {!sidebarCollapsed && (
                    <div>
                      <p className="text-xs uppercase tracking-[0.4em] text-muted">
                        Stack
                      </p>
                      <p className="text-sm font-medium">Workspace</p>
                    </div>
                  )}
                  <button
                    onClick={toggleSidebar}
                    className="h-8 w-8 rounded-full border border-subtle text-xs uppercase tracking-[0.2em] text-secondary hover:border-white/40"
                    aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
                  >
                    {sidebarCollapsed ? "›" : "‹"}
                  </button>
                </div>

                <div className="mt-6 flex w-full items-end gap-6 border-b border-subtle/40 pb-3 text-sm uppercase tracking-[0.2em] text-secondary">
                  {tabs.map((tab) => {
                    const active = tab === activeTab;
                    return (
                      <button
                        key={tab}
                        title={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`relative pb-1 ${
                          sidebarCollapsed ? "w-8" : "w-auto"
                        }`}
                      >
                        <span className={sidebarCollapsed ? "sr-only" : ""}>
                          {tab}
                        </span>
                        <span
                          className={`absolute bottom-0 left-0 h-[2px] w-full transition ${
                            active ? "bg-white" : "bg-white/20"
                          }`}
                        />
                      </button>
                    );
                  })}
                </div>

                <div className="mt-6 flex-1 space-y-4 overflow-hidden">
                  {Array.from({ length: 4 }).map((_, index) => (
                    <div
                      key={index}
                      className={`rounded-2xl border border-subtle/40 bg-[var(--bg-float)] p-3 text-sm text-secondary ${
                        sidebarCollapsed ? "text-center" : ""
                      }`}
                    >
                      <p className="text-xs uppercase tracking-[0.3em] text-muted">
                        {sidebarCollapsed ? `0${index + 1}` : "Pinned"}
                      </p>
                      {!sidebarCollapsed && (
                        <p className="mt-2 text-foreground">
                          Placeholder slot {index + 1}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </Panel>

            <PanelResizeHandle className="relative hidden w-4 items-center justify-center lg:flex">
              <span className="h-14 w-px rounded-full bg-white/10" />
            </PanelResizeHandle>

            <Panel minSize={50}>
              <div className="flex min-h-[50vh] items-start justify-center bg-transparent px-2 py-8 sm:px-6 lg:px-10">
                <div className="inner-card w-full max-w-4xl rounded-3xl border border-subtle/50 p-8 shadow-inner sm:p-10 lg:p-12">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-xs uppercase tracking-[0.4em] text-muted">
                        Questionnaire
                      </p>
                      <h1 className="mt-3 text-3xl font-semibold leading-tight text-white">
                        What kind of insight should this agent prioritize?
                      </h1>
                    </div>
                    <span className="text-sm text-secondary">
                      Step 2 <span className="text-muted">/ 6</span>
                    </span>
                  </div>

                  <p className="mt-4 max-w-2xl text-sm text-secondary">
                    Choose the dominant objective for this run. We sculpt prompts,
                    validations, and follow-ups automatically—just outline the intent.
                  </p>

                  <div className="mt-10 space-y-4">
                    {questionOptions.map((option) => {
                      const isActive = option.id === selectedOption;
                      return (
                        <label
                          key={option.id}
                          className={`flex cursor-pointer items-start gap-4 rounded-2xl border border-subtle/60 px-5 py-4 transition ${
                            isActive ? "bg-white/5" : "bg-transparent"
                          }`}
                        >
                          <input
                            type="radio"
                            name="question-type"
                            value={option.id}
                            checked={isActive}
                            onChange={() => setSelectedOption(option.id)}
                            className="mt-1 h-4 w-4 appearance-none rounded-full border border-white/40 checked:bg-white"
                          />
                          <div>
                            <p className="text-base font-medium text-white">
                              {option.label}
                            </p>
                            <p className="text-sm text-secondary">
                              {option.description}
                            </p>
                          </div>
                        </label>
                      );
                    })}
                  </div>

                  <div className="mt-10 flex items-center justify-end">
                    <button className="rounded-full border border-white/20 px-8 py-3 text-sm font-semibold tracking-[0.3em] text-white shadow-[0_30px_60px_rgba(0,0,0,0.45)] transition hover:border-white/40">
                      CONTINUE
                    </button>
                  </div>
                </div>
              </div>
            </Panel>
          </PanelGroup>
        </div>
      </div>

      <FloatingAIBubble />
    </main>
  );
}


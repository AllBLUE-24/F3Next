"use client";

import FloatingAIBubble from "@/components/FloatingAIBubble";
import {
  CircleHelp,
  Lightbulb,
  CreditCard,
  Settings,
  FileText,
  Rocket,
  MessageSquare,
  Flag,
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

const secondaryTabs = [
  { id: "files", label: "Files", icon: FileText },
  { id: "chats", label: "Chats", icon: MessageSquare },
  { id: "milestones", label: "Milestones", icon: Flag },
] as const;

const fileItems = [
  { name: "inventory.csv", action: "Preview", detail: "SKU + supply delta" },
  { name: "pricing.csv", action: "Preview", detail: "Margin guardrails" },
];

const chatHistory = [
  { title: "Why Odoo?", meta: "Replay", excerpt: "Compare vs SAP for ops." },
  { title: "Budget guardrails", meta: "Replay", excerpt: "Board approved 18%" },
];

const milestones = [
  { title: "Config: Inventory", progress: 3, total: 5 },
  { title: "Stakeholder sign-off", progress: 1, total: 3 },
  { title: "QA scenarios", progress: 0, total: 4 },
];

const questionOptions = [
  {
    id: "commerce",
    label: "Commerce & Retail",
    description: "E-commerce, omnichannel, or direct-to-consumer brands.",
  },
  {
    id: "saas",
    label: "Software / SaaS",
    description: "Platforms, developer tools, or subscription products.",
  },
  {
    id: "ops",
    label: "Operations-heavy",
    description: "Manufacturing, logistics, field ops, or multi-site orgs.",
  },
];

type SecondaryTab = (typeof secondaryTabs)[number]["id"];

export default function QuestionnairePage() {
  const [activePrimary, setActivePrimary] = useState("help");
  const [activeTab, setActiveTab] = useState<SecondaryTab>("files");
  const [selectedOption, setSelectedOption] = useState("commerce");
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

  const renderTabContent = () => {
    if (activeTab === "files") {
      return fileItems.map((file) => (
        <div
          key={file.name}
          className="flex items-center justify-between rounded-2xl border border-subtle/40 bg-[var(--bg-float)] px-4 py-3"
        >
          <div>
            <p className="text-sm font-medium text-white">{file.name}</p>
            <p className="text-xs text-secondary">{file.detail}</p>
          </div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.3em] text-secondary">
            <span className="h-8 w-8 rounded-2xl border border-subtle/40 bg-[var(--bg-card)]" />
            {file.action}
          </div>
        </div>
      ));
    }

    if (activeTab === "chats") {
      return chatHistory.map((chat) => (
        <div
          key={chat.title}
          className="rounded-2xl border border-subtle/40 bg-[var(--bg-float)] px-4 py-3"
        >
          <p className="text-sm font-medium text-white">{chat.title}</p>
          <p className="text-xs text-secondary">{chat.excerpt}</p>
          <button className="mt-3 rounded-full border border-white/20 px-3 py-1 text-[10px] uppercase tracking-[0.3em] text-secondary">
            {chat.meta}
          </button>
        </div>
      ));
    }

    return milestones.map((milestone) => {
      const percent = (milestone.progress / milestone.total) * 100;
      return (
        <div
          key={milestone.title}
          className="rounded-2xl border border-subtle/40 bg-[var(--bg-float)] px-4 py-3"
        >
          <div className="flex items-center justify-between text-sm text-white">
            <span>{milestone.title}</span>
            <span className="text-secondary">
              {milestone.progress}/{milestone.total}
            </span>
          </div>
          <div className="mt-3 h-2 rounded-full border border-white/10 bg-black/30">
            <div
              className="h-full rounded-full shadow-[0_4px_8px_rgba(0,0,0,0.4)]"
              style={{ width: `${percent}%`, backgroundColor: "rgba(255,255,255,0.4)" }}
            />
          </div>
        </div>
      );
    });
  };

  return (
    <main className="void-grid min-h-dvh text-foreground">
      <header
        className="fixed left-0 top-0 z-40 flex h-[var(--header-height)] w-full items-center justify-between border-b border-white/10 bg-[#0a0a0a]/95 px-6 backdrop-blur-md lg:px-12"
        role="banner"
      >
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
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/5 text-xs font-semibold tracking-wide text-white shadow-lg transition hover:shadow-[0_12px_24px_rgba(0,0,0,0.6)]">
            JD
          </div>
        </div>
      </header>

      <aside
        className="fixed left-0 top-[var(--header-height)] z-40 flex h-[calc(100vh-var(--header-height))] w-[var(--sidebar-width)] flex-col items-center border-r border-white/10 bg-[#0a0a0a]"
        aria-label="Primary navigation"
      >
        <div className="mt-8 flex flex-col items-center gap-4">
          {primaryNav.map(({ id, label, icon: Icon }) => {
            const isActive = id === activePrimary;
            return (
              <button
                key={id}
                aria-label={label}
                title={label}
                onClick={() => setActivePrimary(id)}
                className={`relative flex h-12 w-12 items-center justify-center rounded-2xl transition-all ${
                  isActive
                    ? "bg-white/10 shadow-lg"
                    : "border border-transparent hover:shadow-xl"
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
          <div className="relative rounded-[36px] border border-white/10 bg-[#0b0b0b]/95 shadow-[0_50px_140px_rgba(0,0,0,0.7)]">
            <span
              className="pointer-events-none absolute -left-2 top-4 hidden h-[calc(100%-2rem)] w-px rounded-full bg-white/15 lg:block"
              aria-hidden="true"
            />
            <PanelGroup direction="horizontal">
              <Panel
                ref={sidebarRef}
                minSize={18}
                maxSize={40}
                defaultSize={28}
                collapsedSize={8}
                collapsible
                onCollapse={() => setSidebarCollapsed(true)}
                onExpand={() => setSidebarCollapsed(false)}
              >
                <div
                  className={`flex h-full flex-col border-r border-white/10 bg-[#0b0b0b] px-4 pb-6 pt-5 ${
                    sidebarCollapsed ? "items-center" : ""
                  }`}
                >
                  <div className="flex w-full items-center justify-between gap-3">
                    {!sidebarCollapsed && (
                      <div>
                        <p className="text-xs uppercase tracking-[0.4em] text-muted">
                          Workspace
                        </p>
                        <p className="text-sm font-medium text-white/80">
                          Secondary lane
                        </p>
                      </div>
                    )}
                    <button
                      onClick={toggleSidebar}
                      className="h-8 w-8 rounded-full border border-white/15 text-xs text-secondary hover:border-white/40"
                      aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
                    >
                      {sidebarCollapsed ? "›" : "‹"}
                    </button>
                  </div>

                  <div className="mt-6 flex w-full items-end gap-4 border-b border-white/10 pb-3 text-sm uppercase tracking-[0.2em] text-secondary">
                    {secondaryTabs.map(({ id, label, icon: Icon }) => {
                      const active = id === activeTab;
                      return (
                        <button
                          key={id}
                          title={label}
                          onClick={() => setActiveTab(id)}
                          className={`relative flex items-center gap-2 pb-1 ${
                            sidebarCollapsed ? "justify-center" : ""
                          }`}
                        >
                          <Icon className="h-4 w-4" />
                          <span className={sidebarCollapsed ? "sr-only" : ""}>
                            {label}
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

                  <div className="mt-6 flex-1 space-y-4 overflow-y-auto pr-1">
                    {renderTabContent()}
                  </div>
                </div>
              </Panel>

              <PanelResizeHandle className="hidden w-4 items-center justify-center lg:flex">
                <span className="h-14 w-px rounded-full bg-white/10" />
              </PanelResizeHandle>

              <Panel minSize={50}>
                <div className="flex min-h-[60vh] items-start justify-center px-4 py-12 sm:px-8 lg:px-12">
                  <div className="inner-card w-full max-w-4xl rounded-3xl border border-white/10 p-8 sm:p-10 lg:p-14">
                    <div className="flex flex-wrap items-start justify-between gap-6">
                      <div>
                        <p className="text-xs uppercase tracking-[0.4em] text-muted">
                          Questionnaire
                        </p>
                        <h1 className="mt-3 text-3xl font-semibold leading-tight text-white">
                          What best describes your industry?
                        </h1>
                      </div>
                      <div className="tooltip text-xs uppercase tracking-[0.3em] text-secondary" data-tip="Clarifies prompts">
                        Why we ask
                      </div>
                    </div>

                    <p className="mt-4 max-w-2xl text-sm text-secondary">
                      We tailor the multi-agent prompt stack, validations, and follow-up
                      context for your vertical. Pick the closest match so Grok stays on-brand.
                    </p>

                    <div className="mt-10 space-y-4">
                      {questionOptions.map((option) => {
                        const isActive = option.id === selectedOption;
                        return (
                          <label
                            key={option.id}
                            className={`flex cursor-pointer items-start gap-4 rounded-2xl border border-white/10 px-5 py-4 transition ${
                              isActive ? "bg-white/5 shadow-inner" : "bg-transparent"
                            }`}
                          >
                            <input
                              type="radio"
                              name="industry"
                              value={option.id}
                              checked={isActive}
                              onChange={() => setSelectedOption(option.id)}
                              className="mt-1 h-4 w-4 appearance-none rounded-full border border-white/40 bg-transparent checked:bg-white"
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

                    <div className="mt-12 flex items-center justify-end">
                      <button className="rounded-full border border-white/20 px-6 py-3 text-sm font-semibold tracking-[0.3em] text-white shadow-md shadow-black/50 transition hover:shadow-xl">
                        Continue →
                      </button>
                    </div>
                  </div>
                </div>
              </Panel>
            </PanelGroup>
          </div>
        </div>
      </div>

      <FloatingAIBubble />
    </main>
  );
}


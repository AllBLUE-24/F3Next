"use client";

import { FileText, MessageSquare, Flag } from "lucide-react";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { usePathname } from "next/navigation";

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

const interactiveClass = "lift-hover transition-colors duration-200";

const routeTabMap: Record<string, SecondaryTab> = {
  "/questionnaire": "milestones",
  "/recommendations": "files",
  "/deploy": "chats",
};

const keyStats = [
  { label: "Confidence", value: "92%", meta: "+6% vs last run" },
  { label: "Latency", value: "41s", meta: "Target 38s" },
  { label: "Signals fused", value: "18", meta: "Docs · Chats · KPIs" },
];

const insightBullets = [
  "Agents flagged supply variance in SEA region.",
  "Leadership asked for ops-ready storyline.",
  "Context pack updated 12 minutes ago.",
];

export default function QuestionnairePage() {
  const pathname = usePathname();
  const [activeTab, setActiveTab] = useState<SecondaryTab>(
    routeTabMap[pathname] ?? "files",
  );
  const [selectedOption, setSelectedOption] = useState("commerce");

  useEffect(() => {
    setActiveTab(routeTabMap[pathname] ?? "files");
  }, [pathname]);

  const renderTabContent = () => {
    if (activeTab === "files") {
      return fileItems.map((file) => (
        <div
          key={file.name}
          className={`glass-panel flex items-center gap-4 rounded-2xl px-4 py-4 ${interactiveClass}`}
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-[#111827] text-[10px] uppercase tracking-[0.3em] text-secondary">
            CSV
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-white">{file.name}</p>
            <p className="text-xs text-secondary">{file.detail}</p>
          </div>
          <button className="rounded-full border border-white/15 px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-secondary">
            {file.action}
          </button>
        </div>
      ));
    }

    if (activeTab === "chats") {
      return chatHistory.map((chat) => (
        <div
          key={chat.title}
          className={`glass-panel rounded-2xl px-4 py-4 ${interactiveClass}`}
        >
          <p className="text-sm font-medium text-white">{chat.title}</p>
          <p className="text-xs text-secondary">{chat.excerpt}</p>
          <button
            className="mt-3 rounded-full border border-white/15 px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-secondary"
          >
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
          className={`glass-panel rounded-2xl px-4 py-4 ${interactiveClass}`}
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
              style={{ width: `${percent}%`, backgroundColor: "rgba(255,255,255,0.5)" }}
            />
          </div>
        </div>
      );
    });
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 16 },
    show: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] },
    },
  };

  const optionVariants = {
    hidden: { opacity: 0, y: 12 },
    show: (index: number) => ({
      opacity: 1,
      y: 0,
      transition: { delay: 0.1 + index * 0.1, duration: 0.3 },
    }),
  };

  return (
    <section className="overflow-hidden rounded-[36px] border border-white/10 bg-[#0b0b0b]/95 shadow-[0_50px_140px_rgba(0,0,0,0.7)]">
      <div className="flex flex-col lg:flex-row">
        <aside className="w-full max-w-full border-r border-white/10 bg-[#0b0b0b] px-5 py-6 lg:w-[320px]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.4em] text-muted">Stack</p>
              <p className="text-sm font-medium text-white/80">Secondary lane</p>
            </div>
          </div>

          <div className="mt-6 flex w-full gap-3 rounded-full bg-white/5 p-1 text-[11px] uppercase tracking-[0.3em] text-secondary">
            {secondaryTabs.map(({ id, label, icon: Icon }) => {
              const active = id === activeTab;
              return (
                <button
                  key={id}
                  title={label}
                  onClick={() => setActiveTab(id)}
                  className={`flex flex-1 items-center justify-center gap-2 rounded-full px-3 py-2 transition ${
                    active ? "bg-white/15 text-white shadow-inner" : "text-secondary"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{label}</span>
                </button>
              );
            })}
          </div>

          <div className="mt-6 flex flex-col gap-4 overflow-y-auto pr-1">
            {renderTabContent()}
          </div>
        </aside>

        <div className="flex-1 px-4 py-8 sm:px-6 lg:px-10">
          <motion.div
            variants={cardVariants}
            initial="hidden"
            animate="show"
            className={`card-gradient w-full rounded-[32px] border border-white/10 p-8 sm:p-10 lg:p-12 ${interactiveClass}`}
          >
            <div className="flex flex-wrap items-start justify-between gap-6 border-b border-white/10 pb-6">
              <div>
                <p className="text-xs uppercase tracking-[0.4em] text-secondary">
                  Questionnaire
                </p>
                <h1 className="mt-2 text-3xl font-semibold text-white">
                  What best describes your industry?
                </h1>
                <p className="mt-2 max-w-2xl text-sm text-secondary">
                  Signal weighting, tone, and validations adapt based on this choice. Pick
                  the industry the exec team cares about for this run.
                </p>
              </div>
              <div className="flex flex-col items-end gap-2 text-xs uppercase tracking-[0.3em] text-secondary">
                <span className="tooltip" data-tip="Clarifies prompts">
                  Why we ask
                </span>
                <span className="rounded-full border border-white/15 px-3 py-1 text-[10px] text-primary">
                  Step 02 · Context
                </span>
              </div>
            </div>

            <div className="mt-8 grid gap-8 lg:grid-cols-[1.7fr,1fr]">
              <div>
                <div className="space-y-4">
                  {questionOptions.map((option, index) => {
                    const isActive = option.id === selectedOption;
                    return (
                      <motion.label
                        key={option.id}
                        custom={index}
                        variants={optionVariants}
                        initial="hidden"
                        animate="show"
                        className={`flex cursor-pointer items-start gap-4 rounded-2xl border border-white/10 px-5 py-4 ${
                          interactiveClass
                        } ${isActive ? "bg-white/5" : "bg-transparent"}`}
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
                      </motion.label>
                    );
                  })}
                </div>

                <div className="mt-10 flex items-center justify-between border-t border-white/10 pt-6 text-xs text-secondary">
                  <span>Need a custom vertical? Drop a context file in Files.</span>
                  <button className="rounded-full border border-white/20 px-4 py-2 text-[11px] uppercase tracking-[0.3em] text-white">
                    Add intent
                  </button>
                </div>
              </div>

              <div className="space-y-5 rounded-2xl border border-white/10 bg-black/20 p-5">
                <div>
                  <p className="text-xs uppercase tracking-[0.4em] text-secondary">
                    Run stats
                  </p>
                  <div className="mt-4 space-y-3">
                    {keyStats.map((stat) => (
                      <div key={stat.label} className="flex items-center justify-between">
                        <div>
                          <p className="text-[11px] uppercase tracking-[0.3em] text-muted">
                            {stat.label}
                          </p>
                          <p className="text-sm text-secondary">{stat.meta}</p>
                        </div>
                        <p className="text-xl font-semibold text-white">{stat.value}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="border-t border-white/10 pt-4">
                  <p className="text-xs uppercase tracking-[0.4em] text-secondary">
                    Signals
                  </p>
                  <ul className="mt-3 space-y-2 text-sm text-secondary">
                    {insightBullets.map((item) => (
                      <li key={item} className="flex items-start gap-2">
                        <span className="mt-1 h-1.5 w-1.5 rounded-full bg-white/60" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <button className="w-full rounded-full border border-white/20 px-4 py-3 text-center text-sm font-semibold tracking-[0.3em] text-white">
                  Continue →
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}


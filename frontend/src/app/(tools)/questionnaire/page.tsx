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

const interactiveClass =
  "transition-all duration-200 hover:shadow-2xl hover:-translate-y-1 hover:brightness-110 active:scale-95";

const routeTabMap: Record<string, SecondaryTab> = {
  "/questionnaire": "milestones",
  "/recommendations": "files",
  "/deploy": "chats",
};

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
          className={`flex items-center justify-between rounded-2xl border border-white/10 bg-[#0b0b0b] px-4 py-3 ${interactiveClass}`}
        >
          <div>
            <p className="text-sm font-medium text-white">{file.name}</p>
            <p className="text-xs text-secondary">{file.detail}</p>
          </div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.3em] text-secondary">
            <span className="h-8 w-8 rounded-2xl border border-white/10 bg-[#111827]" />
            {file.action}
          </div>
        </div>
      ));
    }

    if (activeTab === "chats") {
      return chatHistory.map((chat) => (
        <div
          key={chat.title}
          className={`rounded-2xl border border-white/10 bg-[#0b0b0b] px-4 py-3 ${interactiveClass}`}
        >
          <p className="text-sm font-medium text-white">{chat.title}</p>
          <p className="text-xs text-secondary">{chat.excerpt}</p>
          <button
            className={`mt-3 rounded-full border border-white/15 px-3 py-1 text-[10px] uppercase tracking-[0.3em] text-secondary ${interactiveClass}`}
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
          className={`rounded-2xl border border-white/10 bg-[#0b0b0b] px-4 py-3 ${interactiveClass}`}
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

          <div className="mt-6 flex w-full gap-4 border-b border-white/10 pb-3 text-sm uppercase tracking-[0.2em] text-secondary">
            {secondaryTabs.map(({ id, label, icon: Icon }) => {
              const active = id === activeTab;
              return (
                <button
                  key={id}
                  title={label}
                  onClick={() => setActiveTab(id)}
                  className={`relative flex flex-1 items-center justify-center gap-2 pb-1 text-xs ${interactiveClass}`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{label}</span>
                  <span
                    className={`absolute bottom-0 left-0 h-[2px] w-full transition ${
                      active ? "bg-white" : "bg-white/20"
                    }`}
                  />
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
            className={`inner-card w-full max-w-4xl rounded-3xl border border-white/10 p-8 sm:p-10 lg:p-12 ${interactiveClass}`}
          >
            <div className="flex flex-wrap items-start justify-between gap-6">
              <div>
                <p className="text-xs uppercase tracking-[0.4em] text-muted">
                  Questionnaire
                </p>
                <h1 className="mt-3 text-3xl font-semibold leading-tight text-white">
                  What best describes your industry?
                </h1>
              </div>
              <div
                className="tooltip text-xs uppercase tracking-[0.3em] text-secondary"
                data-tip="Clarifies prompts"
              >
                Why we ask
              </div>
            </div>

            <p className="mt-4 max-w-2xl text-sm text-secondary">
              We tailor the multi-agent prompt stack, validations, and follow-up context
              for your vertical. Pick the closest match so Grok stays on brand.
            </p>

            <div className="mt-10 space-y-4">
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
                      <p className="text-base font-medium text-white">{option.label}</p>
                      <p className="text-sm text-secondary">{option.description}</p>
                    </div>
                  </motion.label>
                );
              })}
            </div>

            <div className="mt-12 flex items-center justify-end">
              <button
                className={`rounded-full border border-white/20 px-6 py-3 text-sm font-semibold tracking-[0.3em] text-white shadow-md shadow-black/50 ${interactiveClass}`}
              >
                Continue →
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}


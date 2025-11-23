const primaryNav = [
  { label: "Now", active: true },
  { label: "Agents", active: false },
  { label: "Docs", active: false },
  { label: "Signals", active: false },
];

const focusCards = [
  {
    title: "Executive Brief",
    description: "Summaries queued from the last sync. Ready for polish.",
    meta: "2 drafts",
  },
  {
    title: "Ops Health",
    description: "Validation queue looks stable. Keep monitoring throughput.",
    meta: "Live feed",
  },
];

const journeySteps = [
  { title: "Define intent", status: "done" },
  { title: "Assemble context", status: "active" },
  { title: "Generate pathways", status: "upcoming" },
  { title: "Publish & notify", status: "upcoming" },
];

const quickStats = [
  { label: "Queue", value: "08" },
  { label: "Latency", value: "42s" },
  { label: "Confidence", value: "92%" },
];

export default function QuestionnairePage() {
  return (
    <main className="relative min-h-dvh overflow-hidden bg-background text-foreground">
      <div className="flex min-h-dvh">
        {/* Primary sidebar */}
        <aside className="surface-shell flex w-[84px] flex-col items-center border-r border-subtle py-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-strong text-sm uppercase tracking-[0.2em] text-secondary">
            F3
          </div>

          <div className="mt-10 flex flex-1 flex-col items-center gap-4">
            {primaryNav.map(({ label, active }) => (
              <button
                key={label}
                aria-label={label}
                className={`group relative flex h-12 w-12 items-center justify-center rounded-2xl transition-all ${
                  active ? "bg-(--bg-card)" : "hover:bg-(--bg-float)"
                }`}
              >
                <span className="sr-only">{label}</span>
                <span className="flex h-5 w-5 items-center justify-center rounded-xl border border-subtle text-[10px] uppercase tracking-[0.3em] text-secondary">
                  ·
                </span>
                {active && (
                  <span className="absolute left-0 top-1/2 h-8 w-1 -translate-x-3 -translate-y-1/2 rounded-full bg-white" />
                )}
              </button>
            ))}
          </div>

          <div className="flex flex-col items-center gap-3 text-muted">
            <button className="flex h-10 w-10 items-center justify-center rounded-2xl border border-subtle text-xs uppercase tracking-[0.3em]">
              ?
            </button>
            <div className="h-10 w-10 rounded-2xl border border-subtle" />
          </div>
        </aside>

        {/* Base layer shell */}
        <section className="surface-shell relative flex flex-1 flex-col border-l border-subtle">
          <header className="flex h-20 items-center justify-between border-b border-subtle px-8">
            <div>
              <p className="text-sm uppercase tracking-[0.4em] text-muted">
                Operational state
              </p>
              <h1 className="text-lg font-medium">F3 Next Control Deck</h1>
            </div>
            <div className="flex gap-3 text-sm text-secondary">
              <button className="rounded-full border border-subtle px-4 py-2">
                Search
              </button>
              <button className="rounded-full border border-subtle px-4 py-2">
                Status
              </button>
            </div>
          </header>
          <div className="relative flex flex-1 items-center justify-center overflow-hidden">
            <div className="grid-noise absolute inset-0" />
            <div className="relative z-10 max-w-md px-8 text-center text-muted">
              <p>
                Base layer keeps parity with WhatsApp&mdash;a familiar dock to
                anchor navigation and presence indicators.
              </p>
              <p className="mt-4 text-sm text-secondary">
                The intelligence workspace sits above it, creating a depth cue
                for active tools.
              </p>
            </div>
          </div>
        </section>
      </div>

      {/* Overlay workspace */}
      <section className="z-10 flex flex-col gap-6 px-4 pb-10 pt-6 lg:absolute lg:left-[112px] lg:right-12 lg:top-12 lg:bottom-12 lg:flex-row lg:gap-8 lg:px-0">
        <div className="surface-card flex w-full flex-col gap-6 p-6 lg:w-80">
          <div className="flex items-center justify-between text-sm">
            <p className="uppercase tracking-[0.4em] text-muted">Focus</p>
            <span className="rounded-full border border-subtle px-3 py-1 text-xs text-secondary">
              Queue
            </span>
          </div>
          <div className="flex flex-col gap-4">
            {focusCards.map((card) => (
              <div
                key={card.title}
                className="surface-float flex flex-col gap-2 p-4"
              >
                <div className="flex items-center justify-between text-xs uppercase tracking-[0.3em] text-muted">
                  <span>{card.meta}</span>
                  <span className="h-2 w-2 rounded-full bg-white/60" />
                </div>
                <h2 className="text-base font-medium">{card.title}</h2>
                <p className="text-sm text-secondary">{card.description}</p>
              </div>
            ))}
          </div>

          <div className="rounded-3xl border border-dashed border-subtle p-4 text-sm text-secondary">
            Drop future Grok cards here. This column becomes the adaptive
            secondary sidebar.
          </div>
        </div>

        <div className="surface-card flex flex-1 flex-col gap-8 overflow-hidden p-8">
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.4em] text-muted">
                  Questionnaire
                </p>
                <h2 className="text-2xl font-semibold">
                  Context orchestration space
                </h2>
              </div>
              <button className="rounded-full border border-subtle px-5 py-2 text-sm text-secondary">
                Continue
              </button>
            </div>
            <p className="max-w-2xl text-sm text-secondary">
              Reserve this canvas for the multi-agent questionnaire flow. Panels
              stretch, split, or dock depending on how we compose atomic steps.
            </p>
          </div>

          <div className="flex flex-wrap gap-4">
            {quickStats.map((stat) => (
              <div
                key={stat.label}
                className="surface-float flex min-w-[120px] flex-1 flex-col gap-1 p-4"
              >
                <p className="text-xs uppercase tracking-[0.3em] text-muted">
                  {stat.label}
                </p>
                <p className="text-2xl font-semibold">{stat.value}</p>
              </div>
            ))}
          </div>

          <div className="flex flex-col gap-4">
            <p className="text-xs uppercase tracking-[0.3em] text-muted">
              Flow skeleton
            </p>
            <ol className="space-y-3">
              {journeySteps.map((step) => (
                <li
                  key={step.title}
                  className={`flex items-center gap-4 rounded-2xl border border-subtle p-4 ${
                    step.status === "active" ? "pill-active" : ""
                  }`}
                >
                  <span
                    className={`flex h-8 w-8 items-center justify-center rounded-2xl border border-subtle text-xs uppercase tracking-[0.3em] ${
                      step.status === "done"
                        ? "text-secondary"
                        : "text-muted"
                    }`}
                  >
                    {step.status === "done" ? "✓" : step.status === "active" ? "→" : "·"}
                  </span>
                  <div>
                    <p className="text-sm font-medium">{step.title}</p>
                    <p className="text-xs text-muted">
                      Placeholder copy describes what each agent stack owns.
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <div className="mt-auto flex items-center justify-between rounded-3xl border border-dashed border-subtle p-4 text-sm text-secondary">
            <span>Reserve lower third for live agent responses or logs.</span>
            <button className="rounded-full border border-subtle px-4 py-2 text-xs uppercase tracking-[0.3em]">
              Add block
            </button>
          </div>
        </div>
      </section>

      <button
        className="surface-card fixed bottom-8 right-8 flex h-14 w-14 items-center justify-center rounded-full border border-subtle text-xs uppercase tracking-[0.3em] text-secondary shadow-lg lg:bottom-12 lg:right-16"
        aria-label="Invoke AI copilot"
      >
        AI
      </button>
    </main>
  );
}


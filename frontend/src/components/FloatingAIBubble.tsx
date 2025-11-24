"use client";

import { useEffect, useState } from "react";

export default function FloatingAIBubble() {
  const [visible, setVisible] = useState(false);
  const [hovered, setHovered] = useState(false);
  const suggestions = [
    "Summarize latest signals",
    "Show deployment blockers",
    "Draft exec-ready note",
  ];

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 900);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div
      className={`fixed bottom-10 right-8 z-30 flex flex-col items-end gap-3 lg:bottom-14 lg:right-14 ${
        visible ? "opacity-100" : "translate-y-3 opacity-0"
      } transition-all duration-300`}
    >
      <div
        className={`w-64 rounded-2xl border border-white/15 bg-[#0b0b0b]/90 p-4 text-sm text-secondary shadow-[0_25px_60px_rgb(0_0_0/0.6)] backdrop-blur ${
          hovered ? "opacity-100 translate-y-0" : "pointer-events-none -translate-y-2 opacity-0"
        } transition-all duration-200`}
      >
        <p className="text-xs uppercase tracking-[0.4em] text-muted">Copilot ready</p>
        <ul className="mt-3 space-y-2">
          {suggestions.map((item) => (
            <li key={item} className="flex items-start gap-2">
              <span className="mt-1 h-1.5 w-1.5 rounded-full bg-white/60" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
      <button
        type="button"
        aria-label="Activate AI"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        className={`ai-orb flex h-12 w-12 items-center justify-center rounded-full border border-white/15 bg-white/10 text-[11px] font-semibold uppercase tracking-[0.3em] text-white/80 shadow-lg hover:-translate-y-1 ${
          hovered ? "scale-105 text-white" : ""
        }`}
      >
        AI
      </button>
    </div>
  );
}


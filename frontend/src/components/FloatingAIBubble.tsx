"use client";

import { useEffect, useState } from "react";

export default function FloatingAIBubble() {
  const [visible, setVisible] = useState(false);
  const [hovered, setHovered] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 900);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div
      className={`fixed bottom-10 right-8 z-30 flex flex-col items-end gap-2 lg:bottom-14 lg:right-14 ${
        visible ? "opacity-100" : "translate-y-3 opacity-0"
      } transition-all duration-300`}
    >
      <div
        className={`rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[10px] uppercase tracking-[0.3em] text-secondary shadow-sm transition ${
          hovered ? "opacity-100" : "opacity-0"
        }`}
      >
        Ask about industry?
      </div>
      <button
        type="button"
        aria-label="Activate AI"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        className={`ai-orb flex h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-white/10 text-[11px] font-semibold text-white/80 shadow-sm transition hover:-translate-y-1 hover:shadow-md ${
          hovered ? "scale-105 text-white" : ""
        }`}
      >
        AI
      </button>
    </div>
  );
}


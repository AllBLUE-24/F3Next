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
    <button
      type="button"
      aria-label="Floating AI bubble"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={`fixed bottom-10 right-8 z-30 flex h-16 w-16 items-center justify-center rounded-full border border-white/20 bg-[var(--bg-shell)] text-sm font-semibold text-white/70 shadow-[0_40px_80px_rgba(0,0,0,0.45)] transition-all duration-300 lg:bottom-14 lg:right-14 ${
        visible ? "opacity-100" : "translate-y-4 opacity-0"
      } ${hovered ? "scale-105 text-white" : ""}`}
    >
      AI
      <span
        className={`absolute right-full mr-4 rounded-full border border-white/10 bg-[var(--bg-card)] px-3 py-1 text-[11px] uppercase tracking-[0.3em] text-secondary transition-opacity duration-200 ${
          hovered ? "opacity-100" : "opacity-0"
        }`}
      >
        Need help?
      </span>
    </button>
  );
}


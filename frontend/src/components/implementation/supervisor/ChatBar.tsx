"use client";

import { useState, useCallback, KeyboardEvent } from "react";
import { Send, Loader2 } from "lucide-react";

export function ChatBar({
  onSend,
  disabled,
  sending,
  placeholder = "Ask about mappings, errors, or missing data…",
}: {
  onSend: (message: string) => Promise<void>;
  disabled?: boolean;
  sending?: boolean;
  placeholder?: string;
}) {
  const [text, setText] = useState("");

  const submit = useCallback(async () => {
    const trimmed = text.trim();
    if (!trimmed || disabled || sending) return;
    setText("");
    await onSend(trimmed);
  }, [text, disabled, sending, onSend]);

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void submit();
    }
  };

  return (
    <div className="shrink-0 border-t border-[var(--border-subtle)] bg-[var(--bg-card)] p-3">
      <div className="flex gap-2 items-end">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={disabled || sending}
          placeholder={placeholder}
          rows={2}
          maxLength={4000}
          className="flex-1 min-h-[44px] max-h-[120px] resize-y rounded-lg bg-black/25 border border-white/[0.08] px-3 py-2 text-[12px] text-zinc-200 placeholder:text-zinc-600 outline-none focus:border-amber-500/40 disabled:opacity-50"
        />
        <button
          type="button"
          onClick={() => void submit()}
          disabled={disabled || sending || !text.trim()}
          className="shrink-0 h-10 w-10 flex items-center justify-center rounded-lg bg-amber-500/20 border border-amber-500/30 text-amber-300 hover:bg-amber-500/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          title="Send message"
        >
          {sending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
        </button>
      </div>
      <p className="mt-1.5 text-[10px] text-zinc-600">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  );
}

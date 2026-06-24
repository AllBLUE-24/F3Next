"use client";

import { useState, useCallback, KeyboardEvent, useRef } from "react";
import { ArrowUp, Loader2, Plus } from "lucide-react";

export function ChatBar({
  onSend,
  onUploadFiles,
  disabled,
  sending,
  uploading,
  waitingForSystem,
  placeholder = "Ask about mappings, errors, or missing data…",
}: {
  onSend: (message: string) => Promise<void>;
  onUploadFiles?: (files: FileList) => Promise<void>;
  /** Hard block — e.g. message in flight */
  disabled?: boolean;
  sending?: boolean;
  uploading?: boolean;
  /** Pipeline running with no open prompt — show idle/waiting affordance */
  waitingForSystem?: boolean;
  placeholder?: string;
}) {
  const [text, setText] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const inputLocked = Boolean(disabled || sending || uploading);

  const submit = useCallback(async () => {
    const trimmed = text.trim();
    if (!trimmed || inputLocked) return;
    setText("");
    await onSend(trimmed);
  }, [text, inputLocked, onSend]);

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void submit();
    }
  };

  const resolvedPlaceholder = waitingForSystem
    ? "Reply in chat when the assistant asks a question…"
    : placeholder;

  return (
    <div className="shrink-0 border-t border-[var(--border-subtle)] bg-[var(--bg-card)] p-3">
      <div className="flex gap-2 items-end">
        {onUploadFiles && (
          <>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              accept=".sql,.csv,.xlsx,.xls,.json,.xml"
              onChange={(e) => {
                const files = e.target.files;
                if (files?.length) {
                  void onUploadFiles(files);
                }
                e.target.value = "";
              }}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={inputLocked}
              className="shrink-0 h-10 w-10 flex items-center justify-center rounded-full border border-white/[0.12] bg-white/[0.06] text-zinc-300 hover:bg-white/[0.1] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Upload files"
            >
              {uploading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Plus className="w-4 h-4" />
              )}
            </button>
          </>
        )}
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={inputLocked}
          placeholder={resolvedPlaceholder}
          rows={2}
          maxLength={4000}
          className="flex-1 min-h-[44px] max-h-[120px] resize-y rounded-xl bg-black/25 border border-white/[0.08] px-3 py-2.5 text-[12px] text-zinc-200 placeholder:text-zinc-600 outline-none focus:border-amber-500/40 disabled:opacity-60 disabled:cursor-not-allowed transition-opacity"
        />
        <button
          type="button"
          onClick={() => void submit()}
          disabled={inputLocked || !text.trim()}
          className={`shrink-0 h-10 w-10 flex items-center justify-center rounded-full border transition-colors disabled:cursor-not-allowed ${
            inputLocked
              ? "bg-white/[0.08] border-white/[0.12] text-zinc-500"
              : "bg-amber-500/20 border-amber-500/35 text-amber-300 hover:bg-amber-500/30"
          }`}
          title={
            waitingForSystem
              ? "Send a reply"
              : sending
                ? "Sending…"
                : "Send message"
          }
        >
          {sending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ArrowUp className="w-4 h-4" />
          )}
        </button>
      </div>
      <p className="mt-1.5 text-[10px] text-zinc-600">
        {onUploadFiles
          ? "+ to attach files · Enter to send · Shift+Enter for new line"
          : "Enter to send · Shift+Enter for new line"}
      </p>
    </div>
  );
}

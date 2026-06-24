"use client";

import type { ReactNode } from "react";
import { Sparkles, Bot, User } from "lucide-react";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  message_type: string;
  metadata?: Record<string, unknown>;
  created_at?: string | null;
};

function isDebugPipelineSummary(content: string): boolean {
  const trimmed = content.trim();
  return /^(validate_mapped_data|assess_data_readiness|execute_import_phase):/i.test(trimmed);
}

function formatContent(text: string): ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-zinc-100">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={i}
          className="text-[11px] font-mono bg-white/10 px-1 py-0.5 rounded text-amber-200/90"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

function SystemMessage({ message }: { message: ChatMessage }) {
  const label =
    message.message_type === "auto_fix_applied"
      ? "Auto-fix applied"
      : message.message_type === "gap_blocking"
        ? "Mapping blocked"
      : message.message_type === "readiness_summary"
        ? "Data readiness"
      : message.message_type === "validation_summary"
        ? "Validation"
      : message.message_type === "supervisor_question"
        ? "Needs your input"
        : "System";
  return (
    <div className="rounded-lg border border-amber-500/20 bg-amber-500/[0.06] px-3 py-2.5">
      <div className="flex items-center gap-1.5 mb-1">
        <Sparkles className="w-3 h-3 text-amber-400" />
        <span className="text-[10px] uppercase tracking-wider text-amber-400/80 font-medium">
          {label}
        </span>
      </div>
      <p className="text-[12px] text-zinc-300 leading-relaxed whitespace-pre-wrap">
        {formatContent(message.content)}
      </p>
    </div>
  );
}

function UserMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[92%] rounded-xl rounded-tr-sm bg-amber-500/15 border border-amber-500/25 px-3 py-2">
        <div className="flex items-center gap-1.5 mb-0.5 justify-end">
          <span className="text-[10px] text-amber-400/70">You</span>
          <User className="w-3 h-3 text-amber-400/70" />
        </div>
        <p className="text-[12px] text-zinc-100 leading-relaxed whitespace-pre-wrap">
          {message.content}
        </p>
      </div>
    </div>
  );
}

function AssistantMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[92%] rounded-xl rounded-tl-sm bg-white/[0.04] border border-white/[0.08] px-3 py-2">
        <div className="flex items-center gap-1.5 mb-0.5">
          <Bot className="w-3 h-3 text-zinc-500" />
          <span className="text-[10px] text-zinc-500">Assistant</span>
        </div>
        <p className="text-[12px] text-zinc-300 leading-relaxed whitespace-pre-wrap">
          {formatContent(message.content)}
        </p>
      </div>
    </div>
  );
}

export function ChatMessageList({
  messages,
  loading,
}: {
  messages: ChatMessage[];
  loading?: boolean;
}) {
  if (loading && messages.length === 0) {
    return (
      <p className="text-[11px] text-zinc-600 text-center py-4">Loading conversation…</p>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="text-center py-6 px-2">
        <p className="text-[11px] text-zinc-600 leading-relaxed">
          Ask about mappings, validation errors, or missing data. Example:{" "}
          <span className="text-zinc-500 italic">
            &quot;map vendor_name to supplier_name&quot;
          </span>
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {messages.map((m) => {
        if (
          m.message_type === "supervisor_question" &&
          isDebugPipelineSummary(m.content)
        ) {
          return null;
        }
        if (m.role === "system" || m.message_type === "supervisor_question") {
          if (m.role === "user") {
            return <UserMessage key={m.id} message={m} />;
          }
          if (m.role === "assistant" && m.message_type === "supervisor_question") {
            return (
              <div key={m.id} className="rounded-lg border border-amber-500/25 bg-amber-500/[0.08] px-3 py-2.5">
                <div className="flex items-center gap-1.5 mb-1">
                  <Sparkles className="w-3 h-3 text-amber-400" />
                  <span className="text-[10px] uppercase tracking-wider text-amber-400/80 font-medium">
                    Assistant question
                  </span>
                </div>
                <p className="text-[12px] text-zinc-200 leading-relaxed whitespace-pre-wrap">
                  {formatContent(m.content)}
                </p>
              </div>
            );
          }
          return <SystemMessage key={m.id} message={m} />;
        }
        if (m.role === "user") {
          return <UserMessage key={m.id} message={m} />;
        }
        return <AssistantMessage key={m.id} message={m} />;
      })}
    </div>
  );
}

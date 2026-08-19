"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  X,
  Send,
  MessageCircle,
  Phone,
  Mail,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import {
  type MarketingChatMessage,
  clearStoredChat,
  getConsultantOpening,
  loadStoredChat,
  saveStoredChat,
  sendConsultantMessage,
} from "@/lib/api/marketing_chat_api";

interface UiMessage extends MarketingChatMessage {
  id: string;
}

function ContactTeamCard() {
  return (
    <div className="mx-4 mb-3 rounded-xl border border-amber-500/20 bg-amber-500/[0.06] p-4">
      <p
        className="text-[13px] font-semibold text-white mb-1"
        style={{ fontFamily: "var(--font-outfit), sans-serif" }}
      >
        Ready to fix this?
      </p>
      <p className="text-[12px] text-zinc-400 mb-3 leading-relaxed">
        Our team at AllBlue can scope this properly and show you how F3Next would
        work for your setup — no commitment.
      </p>
      <div className="flex flex-col gap-2">
        <Link
          href="/onboarding"
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-amber-500 px-4 py-2.5 text-[13px] font-semibold text-black hover:bg-amber-400 transition-colors"
        >
          Start Free Discovery
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
        <div className="flex gap-2">
          <a
            href="tel:+919370983966"
            className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-[12px] text-zinc-300 hover:border-white/20 hover:text-white transition-colors"
          >
            <Phone className="w-3.5 h-3.5 text-amber-500/80" />
            WhatsApp
          </a>
          <a
            href="mailto:parth.kulkarni2412@gmail.com"
            className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-[12px] text-zinc-300 hover:border-white/20 hover:text-white transition-colors"
          >
            <Mail className="w-3.5 h-3.5 text-amber-500/80" />
            Email
          </a>
        </div>
      </div>
    </div>
  );
}

export default function ConsultantChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showContact, setShowContact] = useState(false);
  const [hasGreeted, setHasGreeted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, showContact, scrollToBottom]);

  useEffect(() => {
    const stored = loadStoredChat();
    if (stored.length > 0) {
      setMessages(
        stored.map((m, i) => ({ ...m, id: `stored-${i}` }))
      );
      setHasGreeted(true);
    }
  }, []);

  useEffect(() => {
    if (messages.length > 0) {
      saveStoredChat(messages.map(({ role, content }) => ({ role, content })));
    }
  }, [messages]);

  useEffect(() => {
    const open = () => setIsOpen(true);
    window.addEventListener("open-consultant-chat", open);
    return () => window.removeEventListener("open-consultant-chat", open);
  }, []);

  const ensureOpening = useCallback(async () => {
    if (hasGreeted || messages.length > 0) return;
    setHasGreeted(true);
    const opening = await getConsultantOpening();
    setMessages([
      {
        id: "opening",
        role: "assistant",
        content: opening,
      },
    ]);
  }, [hasGreeted, messages.length]);

  useEffect(() => {
    if (isOpen) {
      ensureOpening();
      setTimeout(() => textareaRef.current?.focus(), 200);
    }
  }, [isOpen, ensureOpening]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isLoading) return;

    const userMsg: UiMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
    };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput("");
    setIsLoading(true);

    try {
      const history = messages.map(({ role, content }) => ({ role, content }));
      const result = await sendConsultantMessage(text, history);
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: result.reply,
        },
      ]);
      if (result.show_contact) {
        setShowContact(true);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: "assistant",
          content:
            "Something went wrong on my end — but I'm still listening. What's the biggest bottleneck in your operations right now?",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClear = async () => {
    setMessages([]);
    setShowContact(false);
    clearStoredChat();
    const opening = await getConsultantOpening();
    setMessages([{ id: "opening", role: "assistant", content: opening }]);
    setHasGreeted(true);
  };

  const resizeTextarea = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 96)}px`;
  };

  useEffect(resizeTextarea, [input]);

  return (
    <>
      {/* Floating trigger */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            type="button"
            aria-label="Open consultant chat"
            onClick={() => setIsOpen(true)}
            className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 rounded-full border border-amber-500/30 bg-[#0c0c0e] pl-4 pr-5 py-3 shadow-2xl shadow-black/50 hover:border-amber-500/50 hover:bg-[#111113] transition-all group"
          >
            <span className="relative flex h-9 w-9 items-center justify-center rounded-full bg-amber-500/15 ai-orb">
              <Sparkles className="h-4 w-4 text-amber-500" />
            </span>
            <span className="hidden sm:block text-left">
              <span className="block text-[11px] text-zinc-500 leading-none mb-0.5">
                AllBlue consultant
              </span>
              <span
                className="block text-[13px] font-medium text-zinc-200"
                style={{ fontFamily: "var(--font-outfit), sans-serif" }}
              >
                What&apos;s slowing you down?
              </span>
            </span>
          </motion.button>
        )}
      </AnimatePresence>

      {/* Chat panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.96 }}
            transition={{ type: "spring", stiffness: 380, damping: 32 }}
            className="fixed bottom-6 right-6 z-50 flex w-[calc(100vw-2rem)] max-w-[420px] flex-col overflow-hidden rounded-2xl border border-white/[0.08] bg-[#09090B] shadow-2xl shadow-black/60"
            style={{ height: "min(580px, calc(100vh - 3rem))" }}
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-3.5 shrink-0">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-amber-500/15 border border-amber-500/20 ai-orb">
                  <MessageCircle className="h-4 w-4 text-amber-500" />
                </div>
                <div>
                  <p
                    className="text-[14px] font-semibold text-white leading-tight"
                    style={{ fontFamily: "var(--font-outfit), sans-serif" }}
                  >
                    AllBlue Consultant
                  </p>
                  <p className="text-[11px] text-zinc-500">Operations &amp; ERP advisory</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="rounded-lg p-1.5 text-zinc-500 hover:bg-white/5 hover:text-zinc-300 transition-colors"
                aria-label="Close chat"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 min-h-0">
              {messages.map((msg) => {
                const isUser = msg.role === "user";
                return (
                  <div
                    key={msg.id}
                    className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[88%] rounded-2xl px-3.5 py-2.5 text-[13px] leading-relaxed ${
                        isUser
                          ? "bg-amber-500 text-black rounded-br-md"
                          : "bg-white/[0.04] text-zinc-200 border border-white/[0.06] rounded-bl-md"
                      }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                );
              })}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="rounded-2xl rounded-bl-md bg-white/[0.04] border border-white/[0.06] px-4 py-3">
                    <span className="inline-flex gap-1">
                      {[0, 150, 300].map((delay) => (
                        <span
                          key={delay}
                          className="h-1.5 w-1.5 rounded-full bg-zinc-500 animate-bounce"
                          style={{ animationDelay: `${delay}ms` }}
                        />
                      ))}
                    </span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {showContact && <ContactTeamCard />}

            {/* Input */}
            <div className="border-t border-white/[0.06] p-3 shrink-0">
              <div className="flex items-end gap-2 rounded-xl border border-white/[0.08] bg-white/[0.02] px-3 py-2 focus-within:border-amber-500/30 transition-colors">
                <textarea
                  ref={textareaRef}
                  rows={1}
                  value={input}
                  disabled={isLoading}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Describe your bottleneck..."
                  className="flex-1 resize-none bg-transparent text-[13px] text-zinc-100 placeholder:text-zinc-600 outline-none leading-relaxed max-h-24"
                />
                <button
                  type="button"
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading}
                  className="mb-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-500 text-black disabled:opacity-30 hover:bg-amber-400 transition-colors"
                  aria-label="Send message"
                >
                  <Send className="h-3.5 w-3.5" />
                </button>
              </div>
              <div className="mt-2 flex justify-between px-1">
                <span className="text-[10px] text-zinc-600">↵ send · ⇧↵ newline</span>
                <button
                  type="button"
                  onClick={handleClear}
                  className="text-[10px] text-zinc-600 hover:text-zinc-400 transition-colors"
                >
                  New conversation
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

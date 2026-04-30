"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User, RefreshCw } from "lucide-react";

// --- Types ---
interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export type { Message };

interface ChatInterfaceProps {
  initialMessages?: Message[];
  onSendMessage?: (message: string) => Promise<string>;
  messages?: Message[];
  setMessages?: React.Dispatch<React.SetStateAction<Message[]>>;
}

// --- Component ---
const ChatInterface: React.FC<ChatInterfaceProps> = ({
  initialMessages = [],
  onSendMessage,
  messages: controlledMessages,
  setMessages: setControlledMessages,
}) => {
  const [internalMessages, setInternalMessages] = useState<Message[]>(initialMessages.length > 0 ? initialMessages : [
    {
      id: "welcome-1",
      role: "assistant",
      content: "Welcome to F3Next. I have loaded your project context.",
      timestamp: new Date(),
    }
  ]);
  const isControlled = controlledMessages != null && setControlledMessages != null;
  const messages = isControlled ? controlledMessages : internalMessages;
  const setMessages = isControlled ? setControlledMessages! : setInternalMessages;
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const resize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  };

  useEffect(() => { resize(); }, [inputValue]);

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
    setIsLoading(true);

    try {
      let botResponseContent = "";

      if (onSendMessage) {
        botResponseContent = await onSendMessage(userMsg.content);
      } else {
        await new Promise((resolve) => setTimeout(resolve, 1500)); 
        botResponseContent = "Mock response from the AI.";
      }

      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: botResponseContent,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (error) {
      console.error("Error sending message:", error);
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

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="flex flex-col h-full w-full bg-[var(--bg-void)]">
      
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-6" style={{ scrollBehavior: 'smooth' }}>
        <div className="w-full space-y-6">
          {messages.map((msg) => {
            const isUser = msg.role === "user";
            return (
              <div
                key={msg.id}
                className="flex w-full justify-start"
              >
                <div className="flex w-full gap-4 flex-row">
                  {/* Avatar */}
                  <div className={`flex-shrink-0 mt-0.5 w-6 h-6 rounded flex items-center justify-center ${
                    isUser ? "bg-amber-500/10 border border-amber-500/20" : "bg-[var(--bg-shell)] border border-[var(--border-subtle)]"
                  }`}>
                    {isUser ? <User className="w-3.5 h-3.5 text-amber-500" /> : <Bot className="w-3.5 h-3.5 text-zinc-400" />}
                  </div>

                  {/* Bubble */}
                  <div className="flex flex-col items-start max-w-full lg:max-w-[85%]">
                    <div
                      className={`text-[14px] leading-relaxed font-mono ${
                        isUser
                          ? "text-amber-500"
                          : "text-zinc-300"
                      }`}
                    >
                      {msg.content}
                    </div>
                    <span className="text-[9px] text-zinc-600 mt-1 font-mono">
                      {formatTime(msg.timestamp)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex w-full justify-start">
              <div className="flex w-full gap-4 flex-row">
                <div className="flex-shrink-0 mt-0.5 w-6 h-6 rounded bg-[var(--bg-shell)] border border-[var(--border-subtle)] flex items-center justify-center">
                  <Bot className="w-3.5 h-3.5 text-zinc-400" />
                </div>
                <div className="text-[14px] leading-relaxed font-mono text-zinc-400 flex items-center gap-1">
                  <span className="w-1 h-3 bg-zinc-600 animate-pulse"></span>
                  Processing...
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} className="h-4" />
        </div>
      </div>

      {/* Input Area (OS Terminal Style) */}
      <div style={{
        borderTop:  "1px solid #161b22",
        background: "#0a0d14",
        flexShrink: 0,
        position:   "relative",
      }}>
        <div style={{
          display: "flex", alignItems: "flex-start", padding: "14px 20px", gap: "12px",
        }}>
          {/* Badge */}
          <div style={{
              display: "flex", alignItems: "center", gap: "6px",
              padding: "4px 8px", borderRadius: "6px", cursor: "default",
              background: `rgba(245,158,11,0.1)`,
              border: `1px solid rgba(245,158,11,0.2)`,
              marginTop: "1px", flexShrink: 0,
              userSelect: "none"
          }}>
            <span style={{ fontSize: "10px" }}>🔍</span>
            <span style={{ 
              color: "#f59e0b", fontSize: "9.5px", fontWeight: 700, 
              letterSpacing: "1px", paddingTop: "1px" 
            }}>
              DISCOVERY
            </span>
          </div>

          <textarea
            ref={textareaRef}
            value={inputValue}
            rows={1}
            disabled={isLoading}
            placeholder={
              isLoading ? "processing..." : "What would you like to discover?..."
            }
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            style={{
              flex: 1, background: "transparent", border: "none", outline: "none",
              resize: "none", overflow: "hidden", fontFamily: "inherit",
              fontSize: "14px", lineHeight: "24px", color: "#e6edf3",
              caretColor: "#f59e0b", letterSpacing: "0.3px", marginTop: "1px"
            }}
            spellCheck={false}
          />

          {/* Loading indicator / Submit Hint */}
          <div style={{ flexShrink: 0, marginTop: "6px" }}>
            {isLoading ? (
              <span style={{ color: "#f59e0b", fontSize: "10px", animation: "blink 1s step-end infinite" }}>▮</span>
            ) : inputValue.trim() ? (
              <span style={{ color: "#30363d", fontSize: "10px" }}>↵</span>
            ) : null}
          </div>
        </div>

        {/* Hint bar */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 20px 12px",
          color: "#30363d", fontSize: "9.5px", letterSpacing: "0.5px",
        }}>
          <div>
            <span><kbd className="bg-[#161b22] px-1 py-0.5 rounded border border-[#30363d] text-[9px] mr-1">↵</kbd> send</span>
            <span className="ml-3"><kbd className="bg-[#161b22] px-1 py-0.5 rounded border border-[#30363d] text-[9px] mr-1">⇧↵</kbd> newline</span>
          </div>
          <button 
            onClick={() => setMessages([])} 
            className="flex items-center gap-1 hover:text-zinc-400 transition-colors"
          >
            <RefreshCw className="w-3 h-3" /> Clear session
          </button>
        </div>

        <style>{`
          @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
          textarea::placeholder { color: #30363d; }
          textarea:disabled::placeholder { color: #21262d; }
        `}</style>
      </div>
    </div>
  );
};

export default ChatInterface;
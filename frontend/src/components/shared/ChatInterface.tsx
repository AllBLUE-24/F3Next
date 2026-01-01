"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Bot, User, RefreshCw, MoreHorizontal } from "lucide-react";

// --- Types ---
interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface ChatInterfaceProps {
  initialMessages?: Message[];
  onSendMessage?: (message: string) => Promise<string>; // Optional handler for real API calls
}

// --- Component ---
const ChatInterface: React.FC<ChatInterfaceProps> = ({
  initialMessages = [],
  onSendMessage,
}) => {
  const [messages, setMessages] = useState<Message[]>(initialMessages.length > 0 ? initialMessages : [
    {
      id: "welcome-1",
      role: "assistant",
      content: "Hello! I am your AI assistant. How can I help you optimize your operations today?",
      timestamp: new Date(),
    }
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Handle Send Logic
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

      // If a parent handler is provided, use it (Real Logic)
      if (onSendMessage) {
        botResponseContent = await onSendMessage(userMsg.content);
      } else {
        // Fallback Simulation (Mock Logic)
        await new Promise((resolve) => setTimeout(resolve, 1500)); // Fake delay
        botResponseContent = "I've received your query. In a real implementation, I would process this via your LangChain agent and query the vector database.";
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

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Format time helper
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="flex flex-col h-[85vh] w-full max-w-4xl mx-auto bg-zinc-950 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden">
      
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 bg-zinc-900 border-b border-zinc-800">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-600/20 rounded-lg">
            <Bot className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-zinc-100">AI Agent</h2>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-xs text-zinc-400">Online & Ready</span>
            </div>
          </div>
        </div>
        <button 
          onClick={() => setMessages([])} 
          className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-full transition-colors"
          title="Clear Chat"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-zinc-700 scrollbar-track-transparent">
        {messages.map((msg) => {
          const isUser = msg.role === "user";
          return (
            <div
              key={msg.id}
              className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}
            >
              <div className={`flex max-w-[80%] md:max-w-[70%] gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
                
                {/* Avatar */}
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                  isUser ? "bg-indigo-600" : "bg-zinc-700"
                }`}>
                  {isUser ? <User className="w-5 h-5 text-white" /> : <Bot className="w-5 h-5 text-zinc-300" />}
                </div>

                {/* Bubble */}
                <div className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}>
                  <div
                    className={`px-5 py-3 rounded-2xl text-sm leading-relaxed shadow-sm ${
                      isUser
                        ? "bg-indigo-600 text-white rounded-br-none"
                        : "bg-zinc-800 text-zinc-100 border border-zinc-700 rounded-bl-none"
                    }`}
                  >
                    {msg.content}
                  </div>
                  <span className="text-[10px] text-zinc-500 mt-1 px-1">
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
            <div className="flex max-w-[80%] gap-3">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-zinc-700 flex items-center justify-center">
                <Bot className="w-5 h-5 text-zinc-300" />
              </div>
              <div className="bg-zinc-800 border border-zinc-700 px-4 py-3 rounded-2xl rounded-bl-none flex items-center gap-1">
                <span className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                <span className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                <span className="w-2 h-2 bg-zinc-500 rounded-full animate-bounce"></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-zinc-900 border-t border-zinc-800">
        <div className="relative flex items-center gap-2 max-w-4xl mx-auto">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            disabled={isLoading}
            className="w-full bg-zinc-950 text-zinc-100 placeholder-zinc-500 border border-zinc-700 rounded-xl py-3.5 pl-4 pr-12 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isLoading}
            className="absolute right-2 p-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg disabled:bg-zinc-700 disabled:text-zinc-500 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
        <p className="text-center text-xs text-zinc-600 mt-2">
          AI generated responses can be inaccurate.
        </p>
      </div>
    </div>
  );
};

export default ChatInterface;
"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation"; // <-- IMPORT ROUTER
import ChatInterface, { type Message } from "@/components/shared/ChatInterface";
import { sendMessageToDiscoveryAgent } from "@/lib/api/hooks_api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 90_000; // 90s then show helpful message

const INITIAL_MESSAGES: Message[] = [
  {
    id: "intro-1",
    role: "assistant",
    content: "Welcome to F3Next. I have loaded your project context.",
    timestamp: new Date(),
  },
];

interface DiscoveryClientProps {
  projectId: string;
  initialStep: number;
  companySlug: string; // <-- ADDED
  userSlug: string;    // <-- ADDED
}

export default function DiscoveryClient({ 
  projectId, 
  initialStep, 
  companySlug, 
  userSlug 
}: DiscoveryClientProps) {
  const router = useRouter(); // <-- INITIALIZE ROUTER
  
  const [currentStep, setCurrentStep] = useState<number>(initialStep);
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const isPollingRef = useRef(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    isPollingRef.current = false;
  };

  useEffect(() => {
    return () => stopPolling();
  }, []);

  const pollForResponse = (
    onBotResponse: (text: string) => void,
    lastAssistantContent: string
  ) => {
    if (isPollingRef.current) return;
    isPollingRef.current = true;

    timeoutRef.current = setTimeout(() => {
      stopPolling();
      onBotResponse(
        "The agent is taking longer than usual. Make sure the Discovery worker is running in a separate terminal: `python -m containers.discovery.worker` (and that Temporal is running: `temporal server start-dev`)."
      );
    }, POLL_TIMEOUT_MS);

    intervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/discovery/status/${projectId}`);
        if (!res.ok) {
          if (res.status === 404) {
            stopPolling();
            onBotResponse("Discovery session not found. Please refresh and try again.");
            return;
          }
          return;
        }
        
        const data = await res.json();
        
        // --- ADDED REDIRECT LOGIC ---
        // If the workflow is done, stop everything and route to recommendation page
        if (data.is_complete || data.status === "COMPLETE") {
          stopPolling();
          router.push(`/${companySlug}/${userSlug}/recommendation?projectId=${projectId}`);
          return;
        }
        // -----------------------------

        const botText = (data.bot_response || data.message || "").trim();
        const isNewResponse =
          botText &&
          botText !== "Thinking..." &&
          (botText !== lastAssistantContent || lastAssistantContent === "Thinking...");
          
        if (isNewResponse) {
          stopPolling();
          setCurrentStep(data.step ?? currentStep);
          onBotResponse(botText);
        }
      } catch (err) {
        console.error("Polling Error:", err);
      }
    }, POLL_INTERVAL_MS);
  };

  const handleDiscoveryMessage = async (userMessage: string): Promise<string> => {
    try {
      await sendMessageToDiscoveryAgent({
        project_id: projectId,
        step: currentStep,
        message: userMessage,
      });
      
      const lastAssistant = messages.filter((m) => m.role === "assistant").pop();
      const lastContent = lastAssistant?.content ?? "";
      
      pollForResponse((botText) => {
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === "assistant") {
            next[next.length - 1] = { ...last, content: botText };
          } else {
            next.push({
              id: `bot-${Date.now()}`,
              role: "assistant",
              content: botText,
              timestamp: new Date(),
            });
          }
          return next;
        });
      }, lastContent);
      
      return "Thinking...";
    } catch (error) {
      console.error("Chat Error:", error);
      return "Error connecting to agent.";
    }
  };

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-4 md:p-8 bg-zinc-950/50">
      <div className="mb-8 text-center space-y-2">
        <h1 className="text-3xl font-bold tracking-tight text-white">
          Discovery Agent
        </h1>
        <p className="text-zinc-400">
          Project ID: <span className="font-mono text-xs bg-zinc-800 px-2 py-1 rounded">{projectId}</span>
        </p>
      </div>

      <ChatInterface
        messages={messages}
        setMessages={setMessages}
        onSendMessage={handleDiscoveryMessage}
      />
    </main>
  );
}
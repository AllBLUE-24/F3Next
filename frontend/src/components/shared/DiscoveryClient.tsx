"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation"; 
import ChatInterface, { type Message } from "@/components/shared/ChatInterface";
import { sendMessageToDiscoveryAgent } from "@/lib/api/hooks_api";
import { getBaseApiUrl } from "@/lib/config";


const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 90_000;

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
  companySlug: string; 
  userSlug: string;    
}

export default function DiscoveryClient({ 
  projectId, 
  initialStep, 
  companySlug, 
  userSlug 
}: DiscoveryClientProps) {
  const router = useRouter(); 
  
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
        "The agent is taking longer than usual. Make sure the Discovery worker is running."
      );
    }, POLL_TIMEOUT_MS);

    intervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${getBaseApiUrl()}/api/discovery/status/${projectId}`);
        if (!res.ok) {
          if (res.status === 404) {
            stopPolling();
            onBotResponse("Discovery session not found. Please refresh and try again.");
            return;
          }
          return;
        }
        
        const data = await res.json();
        
        // If the workflow is done, stop everything and route to recommendation page
        if (data.is_complete || data.status === "COMPLETE") {
          stopPolling();
          router.push(`/${companySlug}/${userSlug}/recommendation?projectId=${projectId}`);
          return;
        }

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
    <div className="flex flex-col h-full w-full bg-[var(--bg-void)]">
      <div className="flex flex-1 overflow-hidden relative w-full">
        <ChatInterface
          messages={messages}
          setMessages={setMessages}
          onSendMessage={handleDiscoveryMessage}
        />
      </div>
    </div>
  );
}
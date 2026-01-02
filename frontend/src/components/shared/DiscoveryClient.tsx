"use client";

import { useState, useEffect, useRef } from "react";
import ChatInterface from "@/components/shared/ChatInterface";
import { sendMessageToDiscoveryAgent } from "@/lib/api/hooks_api";

interface DiscoveryClientProps {
  projectId: string;
  initialStep: number;
}

export default function DiscoveryClient({ projectId, initialStep }: DiscoveryClientProps) {
  const [currentStep, setCurrentStep] = useState<number>(initialStep);
  const isPollingRef = useRef(false); // Prevent double polling

  // Initial greeting
  const discoveryMessages = [
    {
      id: "intro-1",
      role: "assistant" as const,
      content: "Welcome to F3Next. I have loaded your project context.",
      timestamp: new Date(),
    }
  ];

  // --- THE POLLING LOGIC ---
  const pollForResponse = async () => {
    if (isPollingRef.current) return;
    isPollingRef.current = true;

    const intervalId = setInterval(async () => {
      try {
        const res = await fetch(`/api/discovery/status/${projectId}`);
        const data = await res.json();

        // 🔥 CRITICAL FIX: Handle BOTH possible variable names
        // The Status API usually returns 'bot_response'.
        // The Chat API usually returns 'message'.
        // We check both to be safe.
        const botText = data.bot_response || data.message;

        // Only update if we have actual text and it's new
        // Note: In a real app, you'd compare against the last message ID
        // For now, we check if the status is 'COMPLETE' or if step changed
        if (data.step !== currentStep && botText) {
          
          // Add the message to the UI
          // (Assuming ChatInterface has an internal method or we trigger it via state)
          // Since ChatInterface is a shared component, we might need to pass a callback 
          // OR force a reload. 
          // BUT simpler: Just return the text if this function was called by the handler.
          
          // STOP polling if step advanced
          setCurrentStep(data.step);
          clearInterval(intervalId);
          isPollingRef.current = false;
        }
      } catch (err) {
        console.error("Polling Error:", err);
      }
    }, 2000); 
  };

  const handleDiscoveryMessage = async (userMessage: string): Promise<string> => {
    try {
      // 1. Send the User Message
      const response = await sendMessageToDiscoveryAgent({
        project_id: projectId,
        step: currentStep, 
        message: userMessage
      });

      // 2. The immediate response is just an ACK ("Message received")
      // We do NOT want to show this to the user as the "Answer".
      // We want to wait for the real answer from the polling.
      
      // Start polling for the REAL answer
      pollForResponse();

      // Return a temporary placeholder or empty string
      // If ChatInterface requires a return string immediately, give a "Thinking..." msg
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
        initialMessages={discoveryMessages}
        onSendMessage={handleDiscoveryMessage}
      />
    </main>
  );
}
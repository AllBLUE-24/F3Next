"use client";

import ChatInterface from "@/components/shared/ChatInterface";
import { sendMessageToDiscoveryAgent } from "@/lib/api/hooks_api"; // Import the hook

export default function DiscoveryPage() {
  
  // Custom initial messages for the Discovery context
  const discoveryMessages = [
    {
      id: "intro-1",
      role: "assistant" as const,
      content: "Welcome to the F3Next Discovery Phase. I'm here to help understand your manufacturing requirements.",
      timestamp: new Date(),
    },
    {
      id: "intro-2",
      role: "assistant" as const,
      content: "To get started, could you tell me a bit about your current production volume and the specific pain points you are facing with your current system?",
      timestamp: new Date(),
    }
  ];

  // The Handler now calls the real API
  const handleDiscoveryMessage = async (message: string): Promise<string> => {
    // Call the function from hooks_api.ts
    // This will send the data to backend/app/api/discovery.py
    const response = await sendMessageToDiscoveryAgent(message);
    
    return response;
  };

  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-4 md:p-8 bg-zinc-950/50">
      
      {/* Page Title / Context Header */}
      <div className="mb-8 text-center space-y-2">
        <h1 className="text-3xl font-bold tracking-tight text-white">
          Discovery Agent
        </h1>
        <p className="text-zinc-400">
          Let's configure your perfect ERP environment.
        </p>
      </div>

      {/* The Chat Interface Component */}
      <ChatInterface 
        initialMessages={discoveryMessages}
        onSendMessage={handleDiscoveryMessage}
      />
      
    </main>
  );
}
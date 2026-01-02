// src/lib/api/hooks_api.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// 1. Define the Input Interface (What frontend sends)
interface ChatPayload {
  project_id: string;
  message: string;
  step?: number; // Optional for now, but good to have
}

interface DiscoveryResponse {
  step: number;
  message: string;
}

/**
 * Sends a user message to the Discovery Agent backend.
 * @param message - The user's input string
 * @param projectId - MUST be a valid UUID string from your database
 */
export const sendMessageToDiscoveryAgent = async (
  payload: ChatPayload
): Promise<DiscoveryResponse> => {
  try {
    const res = await fetch(`${API_BASE_URL}/api/discovery/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      // 2. Body is now clean because payload matches backend expectations
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      const errorDetail = typeof errorData.detail === 'object' 
        ? JSON.stringify(errorData.detail) 
        : errorData.detail;
        
      console.error("Backend Validation Error:", errorDetail);
      throw new Error(errorDetail || `API Error: ${res.status}`);
    }

    return await res.json();

  } catch (error) {
    console.error("Discovery Agent API Error:", error);
    // Return a fallback so the UI doesn't crash
    return { step: 0, message: "Connection error. Please try again." };
  }
};
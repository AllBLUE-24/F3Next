// Define the Base URL (Use env variable in production, fallback to localhost for dev)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface DiscoveryResponse {
  response: string;
  status: string;
}

/**
 * Sends a user message to the Discovery Agent backend.
 * @param message - The user's input string
 * @param projectId - (Optional) To maintain conversation context
 */
export const sendMessageToDiscoveryAgent = async (
  message: string, 
  projectId: string = "session-user-123"
): Promise<string> => {
  try {
    const res = await fetch(`${API_BASE_URL}/api/discovery/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: message,
        project_id: projectId,
      }),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || `API Error: ${res.status}`);
    }

    const data: DiscoveryResponse = await res.json();
    return data.response;

  } catch (error) {
    console.error("Discovery Agent API Error:", error);
    // Return a fallback message so the UI doesn't crash
    return "I'm having trouble connecting to the F3Next server right now. Please check your connection.";
  }
};
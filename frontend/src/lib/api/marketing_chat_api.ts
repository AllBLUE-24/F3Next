import { getBaseApiUrl } from "@/lib/config";

const API_BASE_URL = getBaseApiUrl();

export interface MarketingChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface MarketingChatResponse {
  reply: string;
  show_contact: boolean;
  user_turns: number;
}

export async function getConsultantOpening(): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/api/marketing/chat/opening`, {
    cache: "no-store",
  });
  if (!res.ok) {
    return "Hey — I'm from AllBlue. Tell me what's slowing down your business right now?";
  }
  const data = await res.json();
  return data.message ?? "";
}

export async function sendConsultantMessage(
  message: string,
  history: MarketingChatMessage[]
): Promise<MarketingChatResponse> {
  const res = await fetch(`${API_BASE_URL}/api/marketing/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      typeof err.detail === "string"
        ? err.detail
        : `Consultant chat failed (${res.status})`
    );
  }
  return res.json();
}

export const CONSULTANT_CHAT_STORAGE_KEY = "f3next-consultant-chat";

export function loadStoredChat(): MarketingChatMessage[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(CONSULTANT_CHAT_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveStoredChat(messages: MarketingChatMessage[]): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(CONSULTANT_CHAT_STORAGE_KEY, JSON.stringify(messages));
  } catch {
    /* ignore quota errors */
  }
}

export function clearStoredChat(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(CONSULTANT_CHAT_STORAGE_KEY);
}

/** Dispatch from CTAs to open the floating consultant panel */
export function openConsultantChat(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent("open-consultant-chat"));
}

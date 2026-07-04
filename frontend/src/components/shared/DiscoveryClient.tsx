"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import ChatInterface, { type Message } from "@/components/shared/ChatInterface";
import {
  completeDiscovery,
  getDiscoverySession,
  sendMessageToDiscoveryAgent,
} from "@/lib/api/hooks_api";

// ------------------------------------------------------------------
// Sidebar — simple session panel + recommendation CTA
// ------------------------------------------------------------------
function SessionPanel({
  userTurns,
  readyForRecommendation,
  isCompleting,
  onComplete,
}: {
  userTurns: number;
  readyForRecommendation: boolean;
  isCompleting: boolean;
  onComplete: () => void;
}) {
  return (
    <div
      style={{
        width: "240px",
        flexShrink: 0,
        borderLeft: "1px solid #161b22",
        background: "#070a10",
        display: "flex",
        flexDirection: "column",
        padding: "20px 16px",
        gap: "12px",
      }}
    >
      <div>
        <div
          style={{
            fontSize: "9px",
            letterSpacing: "1.5px",
            color: "#30363d",
            fontWeight: 700,
            marginBottom: "8px",
          }}
        >
          DISCOVERY WITH ADI
        </div>
        <p
          style={{
            fontSize: "11px",
            color: "#6e7681",
            lineHeight: 1.5,
            margin: 0,
          }}
        >
          Chat naturally — no script. Adi learns about your business through
          conversation.
        </p>
      </div>

      <div
        style={{
          padding: "10px 12px",
          borderRadius: "8px",
          background: "rgba(255,255,255,0.02)",
          border: "1px solid #161b22",
        }}
      >
        <div style={{ fontSize: "9px", color: "#30363d", marginBottom: "4px" }}>
          EXCHANGES
        </div>
        <div style={{ fontSize: "18px", fontWeight: 700, color: "#e6edf3" }}>
          {userTurns}
        </div>
      </div>

      <button
        type="button"
        onClick={onComplete}
        disabled={!readyForRecommendation || isCompleting}
        style={{
          marginTop: "auto",
          padding: "10px 14px",
          borderRadius: "8px",
          border: "none",
          fontSize: "11px",
          fontWeight: 700,
          cursor:
            readyForRecommendation && !isCompleting ? "pointer" : "not-allowed",
          background:
            readyForRecommendation && !isCompleting
              ? "linear-gradient(135deg, #f59e0b, #d97706)"
              : "#21262d",
          color:
            readyForRecommendation && !isCompleting ? "#000" : "#484f58",
          opacity: isCompleting ? 0.7 : 1,
          transition: "opacity 0.2s ease",
        }}
      >
        {isCompleting ? "Building recommendation…" : "Get my ERP recommendation"}
      </button>

      {!readyForRecommendation && (
        <p style={{ fontSize: "9px", color: "#30363d", margin: 0, lineHeight: 1.4 }}>
          Chat a bit first — then generate your fit score.
        </p>
      )}
    </div>
  );
}

function toUiMessages(
  raw: { role: string; content: string; ts?: string }[]
): Message[] {
  return raw.map((m, i) => ({
    id: `msg-${i}-${m.ts || i}`,
    role: m.role as "user" | "assistant",
    content: m.content,
    timestamp: m.ts ? new Date(m.ts) : new Date(),
  }));
}

// ------------------------------------------------------------------
// DiscoveryClient
// ------------------------------------------------------------------
interface DiscoveryClientProps {
  projectId: string;
  initialStep: number;
  companySlug: string;
  userSlug: string;
}

export default function DiscoveryClient({
  projectId,
  companySlug,
  userSlug,
}: DiscoveryClientProps) {
  const router = useRouter();

  const [messages, setMessages] = useState<Message[]>([]);
  const [userTurns, setUserTurns] = useState(0);
  const [readyForRecommendation, setReadyForRecommendation] = useState(false);
  const [isLoadingSession, setIsLoadingSession] = useState(true);
  const [isCompleting, setIsCompleting] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const session = await getDiscoverySession(projectId);
        if (cancelled) return;

        if (session.is_complete || session.awaiting_confirmation) {
          router.push(
            `/${companySlug}/${userSlug}/recommendation?projectId=${projectId}`
          );
          return;
        }

        setMessages(toUiMessages(session.messages));
        setUserTurns(session.user_turns);
        setReadyForRecommendation(session.ready_for_recommendation);
      } catch (err) {
        if (!cancelled) {
          setSessionError(
            err instanceof Error ? err.message : "Failed to load discovery session"
          );
        }
      } finally {
        if (!cancelled) setIsLoadingSession(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [projectId, companySlug, userSlug, router]);

  const handleDiscoveryMessage = async (userMessage: string): Promise<string> => {
    const result = await sendMessageToDiscoveryAgent({
      project_id: projectId,
      message: userMessage,
    });

    if (result.user_turns !== undefined) setUserTurns(result.user_turns);
    if (result.ready_for_recommendation !== undefined) {
      setReadyForRecommendation(result.ready_for_recommendation);
    }

    if (result.is_complete) {
      router.push(
        `/${companySlug}/${userSlug}/recommendation?projectId=${projectId}`
      );
    }

    return result.reply;
  };

  const handleComplete = async () => {
    setIsCompleting(true);
    try {
      const result = await completeDiscovery(projectId);

      if (result.confirmation_message) {
        const confirmationMsg: Message = {
          id: `msg-confirmation-${Date.now()}`,
          role: "assistant",
          content: result.confirmation_message,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, confirmationMsg]);
      }

      router.push(
        `/${companySlug}/${userSlug}/recommendation?projectId=${projectId}`
      );
    } catch (err) {
      console.error("Complete discovery error:", err);
      alert(
        err instanceof Error
          ? err.message
          : "Could not generate recommendation. Try again."
      );
    } finally {
      setIsCompleting(false);
    }
  };

  if (isLoadingSession) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          color: "#6e7681",
          fontSize: "13px",
        }}
      >
        Loading conversation…
      </div>
    );
  }

  if (sessionError) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          color: "#f85149",
          fontSize: "13px",
          padding: "24px",
          textAlign: "center",
        }}
      >
        {sessionError}
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        height: "100%",
        width: "100%",
        background: "var(--bg-void)",
      }}
    >
      <div style={{ flex: 1, overflow: "hidden", minWidth: 0 }}>
        <ChatInterface
          messages={messages}
          setMessages={setMessages}
          onSendMessage={handleDiscoveryMessage}
        />
      </div>

      <SessionPanel
        userTurns={userTurns}
        readyForRecommendation={readyForRecommendation}
        isCompleting={isCompleting}
        onComplete={handleComplete}
      />
    </div>
  );
}

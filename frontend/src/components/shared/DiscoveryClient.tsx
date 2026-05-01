"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import ChatInterface, { type Message } from "@/components/shared/ChatInterface";
import { sendMessageToDiscoveryAgent } from "@/lib/api/hooks_api";
import { getBaseApiUrl } from "@/lib/config";

const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS  = 90_000;

// ------------------------------------------------------------------
// Coverage types (mirror backend shape)
// ------------------------------------------------------------------
interface CoverageDim {
  status: "confirmed" | "partial" | null;
  value:  string | null;
}

interface Coverage {
  industry:      CoverageDim;
  strategy:      CoverageDim;
  scale:         CoverageDim;
  legacy_system: CoverageDim;
  pain_point:    CoverageDim;
}

const EMPTY_COVERAGE: Coverage = {
  industry:      { status: null, value: null },
  strategy:      { status: null, value: null },
  scale:         { status: null, value: null },
  legacy_system: { status: null, value: null },
  pain_point:    { status: null, value: null },
};

const DIM_LABELS: Record<keyof Coverage, string> = {
  industry:      "Industry",
  strategy:      "Fulfillment",
  scale:         "Scale",
  legacy_system: "Current System",
  pain_point:    "Core Challenge",
};

// ------------------------------------------------------------------
// CoveragePanel — sidebar showing what Adi has understood so far
// ------------------------------------------------------------------
function CoveragePanel({ coverage, turnCount }: { coverage: Coverage; turnCount: number }) {
  const dims = Object.keys(DIM_LABELS) as (keyof Coverage)[];
  const confirmedCount = dims.filter(d => coverage[d].status !== null).length;

  return (
    <div style={{
      width: "240px",
      flexShrink: 0,
      borderLeft: "1px solid #161b22",
      background: "#070a10",
      display: "flex",
      flexDirection: "column",
      padding: "20px 16px",
      gap: "4px",
    }}>
      {/* Header */}
      <div style={{ marginBottom: "16px" }}>
        <div style={{
          fontSize: "9px",
          letterSpacing: "1.5px",
          color: "#30363d",
          fontWeight: 700,
          marginBottom: "6px",
        }}>
          UNDERSTANDING YOUR BUSINESS
        </div>
        {/* Progress bar */}
        <div style={{
          height: "2px",
          background: "#161b22",
          borderRadius: "2px",
          overflow: "hidden",
        }}>
          <div style={{
            height: "100%",
            width: `${(confirmedCount / 5) * 100}%`,
            background: confirmedCount === 5
              ? "linear-gradient(90deg, #22c55e, #16a34a)"
              : "linear-gradient(90deg, #f59e0b, #d97706)",
            borderRadius: "2px",
            transition: "width 0.6s ease",
          }} />
        </div>
        <div style={{ fontSize: "9px", color: "#30363d", marginTop: "4px" }}>
          {confirmedCount}/5 dimensions mapped
          {turnCount > 0 && <span style={{ marginLeft: "6px" }}>· turn {turnCount}</span>}
        </div>
      </div>

      {/* Dimension rows */}
      {dims.map((dim) => {
        const { status, value } = coverage[dim];
        const isConfirmed = status === "confirmed";
        const isPartial   = status === "partial";
        const isUnknown   = status === null;

        const icon  = isConfirmed ? "✓" : isPartial ? "◐" : "·";
        const color = isConfirmed ? "#22c55e" : isPartial ? "#f59e0b" : "#30363d";

        return (
          <div key={dim} style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "8px",
            padding: "7px 8px",
            borderRadius: "6px",
            background: isConfirmed
              ? "rgba(34,197,94,0.04)"
              : isPartial
              ? "rgba(245,158,11,0.04)"
              : "transparent",
            transition: "background 0.3s ease",
          }}>
            <span style={{
              fontSize: "11px",
              color,
              flexShrink: 0,
              marginTop: "1px",
              transition: "color 0.3s ease",
            }}>
              {icon}
            </span>
            <div style={{ minWidth: 0 }}>
              <div style={{
                fontSize: "9px",
                color: isUnknown ? "#30363d" : "#6e7681",
                letterSpacing: "0.5px",
                fontWeight: 600,
                lineHeight: "1",
                marginBottom: "3px",
              }}>
                {DIM_LABELS[dim].toUpperCase()}
              </div>
              <div style={{
                fontSize: "10.5px",
                color: isConfirmed ? "#e6edf3" : isPartial ? "#8b949e" : "#30363d",
                lineHeight: "1.3",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                maxWidth: "160px",
                transition: "color 0.3s ease",
              }}>
                {value || (isUnknown ? "—" : "Partially known")}
              </div>
            </div>
          </div>
        );
      })}

      {/* Footer note */}
      <div style={{
        marginTop: "auto",
        paddingTop: "16px",
        fontSize: "9px",
        color: "#21262d",
        lineHeight: "1.5",
      }}>
        Adi extracts signals from your answers automatically. You don't need to follow a script.
      </div>
    </div>
  );
}

// ------------------------------------------------------------------
// DiscoveryClient
// ------------------------------------------------------------------
const INITIAL_MESSAGES: Message[] = [
  {
    id:        "intro-1",
    role:      "assistant",
    content:   "Connecting to Adi...",
    timestamp: new Date(),
  },
];

interface DiscoveryClientProps {
  projectId:   string;
  initialStep: number;
  companySlug: string;
  userSlug:    string;
}

export default function DiscoveryClient({
  projectId,
  initialStep,
  companySlug,
  userSlug,
}: DiscoveryClientProps) {
  const router = useRouter();

  const [currentStep, setCurrentStep] = useState<number>(initialStep);
  const [messages,    setMessages]    = useState<Message[]>(INITIAL_MESSAGES);
  const [coverage,    setCoverage]    = useState<Coverage>(EMPTY_COVERAGE);
  const [turnCount,   setTurnCount]   = useState<number>(0);

  const isPollingRef = useRef(false);
  const intervalRef  = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef   = useRef<ReturnType<typeof setTimeout>  | null>(null);

  const stopPolling = () => {
    if (intervalRef.current)  { clearInterval(intervalRef.current); intervalRef.current = null; }
    if (timeoutRef.current)   { clearTimeout(timeoutRef.current);   timeoutRef.current  = null; }
    isPollingRef.current = false;
  };

  useEffect(() => {
    // Kick off initial poll to fetch Adi's opening message
    pollForResponse((botText) => {
      setMessages([{
        id:        "adi-opening",
        role:      "assistant",
        content:   botText,
        timestamp: new Date(),
      }]);
    }, "Connecting to Adi...");

    return () => stopPolling();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const pollForResponse = (
    onBotResponse: (text: string) => void,
    lastAssistantContent: string,
  ) => {
    if (isPollingRef.current) return;
    isPollingRef.current = true;

    timeoutRef.current = setTimeout(() => {
      stopPolling();
      onBotResponse("Adi is taking longer than usual. Make sure the Discovery worker is running.");
    }, POLL_TIMEOUT_MS);

    intervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${getBaseApiUrl()}/api/discovery/status/${projectId}`);

        if (!res.ok) {
          if (res.status === 404) {
            stopPolling();
            onBotResponse("Discovery session not found. Please refresh and try again.");
          }
          return;
        }

        const data = await res.json();

        // Update live coverage panel
        if (data.coverage) setCoverage(data.coverage as Coverage);
        if (data.turn_count !== undefined) setTurnCount(data.turn_count);

        // Redirect to recommendation when complete
        if (data.is_complete || data.status === "COMPLETE") {
          stopPolling();
          router.push(`/${companySlug}/${userSlug}/recommendation?projectId=${projectId}`);
          return;
        }

        const botText = (data.bot_response || data.message || "").trim();
        const isNewResponse =
          botText &&
          botText !== "Thinking..." &&
          botText !== "Connecting to Adi..." &&
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
        step:       currentStep,
        message:    userMessage,
      });

      const lastAssistant = messages.filter((m) => m.role === "assistant").pop();
      const lastContent   = lastAssistant?.content ?? "";

      pollForResponse((botText) => {
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === "assistant") {
            next[next.length - 1] = { ...last, content: botText };
          } else {
            next.push({
              id:        `adi-${Date.now()}`,
              role:      "assistant",
              content:   botText,
              timestamp: new Date(),
            });
          }
          return next;
        });
      }, lastContent);

      return "Thinking...";
    } catch (error) {
      console.error("Chat Error:", error);
      return "Error connecting to Adi.";
    }
  };

  return (
    <div style={{ display: "flex", height: "100%", width: "100%", background: "var(--bg-void)" }}>
      {/* Main chat */}
      <div style={{ flex: 1, overflow: "hidden", minWidth: 0 }}>
        <ChatInterface
          messages={messages}
          setMessages={setMessages}
          onSendMessage={handleDiscoveryMessage}
        />
      </div>

      {/* Live coverage panel */}
      <CoveragePanel coverage={coverage} turnCount={turnCount} />
    </div>
  );
}
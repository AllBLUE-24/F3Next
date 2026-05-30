"use client";

import React, {
  useState, useEffect, useRef, useCallback, type ReactNode,
} from "react";
import {
  submitCommand, pollStatus, fetchResult,
  confirmCommand, answerClarification,
  type AgentStep, type ConfirmationRequest,
} from "@/lib/api/os-api";

import PipelineStatus     from "@/components/OS/PipelineStatus";
import OutputLog          from "@/components/OS/OutputLog";
import TerminalInput, { type CommandMode } from "@/components/OS/TerminalInput";
import ClarificationBlock from "@/components/OS/ClarificationBlock";
import ConfirmationBlock  from "@/components/OS/ConfirmationBlock";
import { clarificationFromConfirmationRequest } from "@/lib/api/gate-mappers";
import { friendlyNetworkError } from "@/lib/copy/gate-copy";

import {
  uid, type LogEntry, type UiPhase, TERMINAL_PHASES,
} from "@/types/types";

export interface OSShellProps {
  projectId: string;
  companyId: string;
  userId:    string;
  erpType?:  "erpnext" | "odoo";
}

const POLL_MS = 1500;

function entry(role: LogEntry["role"], content: string, meta?: LogEntry["meta"]): LogEntry {
  return { id: uid(), role, content, timestamp: new Date(), meta };
}

function buildCtxJson(log: LogEntry[]): string {
  return JSON.stringify(
    log.filter((e) => e.role === "user" || e.role === "assistant").slice(-6)
       .map((e) => ({ role: e.role, content: e.content }))
  );
}

export default function OSShell({
  projectId, companyId, userId, erpType = "erpnext",
}: OSShellProps): React.JSX.Element {
  const [phase,       setPhase]       = useState<UiPhase>("idle");
  const [log,         setLog]         = useState<LogEntry[]>([]);
  const [agentStep,   setAgentStep]   = useState<AgentStep>("");
  const [confirmReq,  setConfirmReq]  = useState<ConfirmationRequest | null>(null);
  const [inputLocked, setInputLocked] = useState<boolean>(false);
  const [gateSubmitting, setGateSubmitting] = useState<boolean>(false);

  const wfRef   = useRef<string | null>(null);
  const logRef  = useRef<LogEntry[]>([]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { logRef.current = log; }, [log]);

  const addEntry = useCallback((e: LogEntry): void => {
    setLog((prev: LogEntry[]) => [...prev, e]);
  }, []);

  const stopPolling = useCallback((): void => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback((wfId: string): void => {
    stopPolling();
    pollRef.current = setInterval(async (): Promise<void> => {
      try {
        const data = await pollStatus(wfId);
        const step = data.status;
        setAgentStep(step);

        if (
          step === "awaiting_clarification"
          || step === "awaiting_confirmation"
          || step === "awaiting_semantic_confirmation"
        ) {
          const cr = data.confirmation_request ?? null;
          const needsClarificationUi = step === "awaiting_clarification";
          const needsConfirmUi =
            step === "awaiting_confirmation" || step === "awaiting_semantic_confirmation";
          if (needsClarificationUi && !cr) {
            return;
          }
          if (needsConfirmUi && !cr) {
            return;
          }
          setConfirmReq(cr);
          setPhase(needsClarificationUi ? "awaiting_clarification" : "awaiting_confirmation");
          setInputLocked(true);
          stopPolling();
          return;
        }

        if (TERMINAL_PHASES.includes(step as UiPhase) || step === "validation_failed") {
          stopPolling();
          const pollResponse = data.response ?? null;

          if (step === "done") {
            if (pollResponse) {
              addEntry(entry("assistant", pollResponse));
            } else {
              try {
                const result = await fetchResult(wfId);
                addEntry(entry("assistant", result.response ?? "✓ Done."));
              } catch {
                addEntry(entry("assistant", "✓ Command completed."));
              }
            }
            setPhase("done");
          } else if (step === "error" || step === "validation_failed") {
            addEntry(entry("error", pollResponse ?? "Command failed — check details above and try again."));
            setPhase("error");
          } else if (step === "cancelled") {
            addEntry(entry("system", pollResponse ?? "Command cancelled. No changes were made."));
            setPhase("cancelled");
          }

          setInputLocked(false);
          setAgentStep("");
        }
      } catch (err: unknown) {
        console.error("OS poll:", err);
      }
    }, POLL_MS);
  }, [stopPolling, addEntry]);

  useEffect(() => (): void => { stopPolling(); }, [stopPolling]);

  // ── Submit ─────────────────────────────────────────────────────────────────

  const handleSubmit = useCallback(async (prompt: string, mode: CommandMode): Promise<void> => {
    const trimmed = prompt.trim();
    if (!trimmed || inputLocked) return;

    setInputLocked(true);
    setPhase("submitting");
    setAgentStep("clarity");
    
    addEntry(entry("user", trimmed));

    try {
      const res = await submitCommand({
        prompt:          trimmed,          // 🔴 FIX: Clean prompt, no more wrapper text!
        project_id:      projectId,
        company_id:      companyId,
        user_id:         userId,
        erp_type:        erpType,
        session_context: buildCtxJson(logRef.current),
        mode:            mode,             // 🔴 FIX: Passing the mode directly as a property!
      });

      wfRef.current = res.workflow_id;
      setPhase("polling");
      startPolling(res.workflow_id);
    } catch (err: unknown) {
      const raw = err instanceof Error ? err.message : "Failed to connect to OS backend";
      addEntry(entry("error", friendlyNetworkError("command", raw)));
      setPhase("error");
      setInputLocked(false);
      setAgentStep("");
    }
  }, [inputLocked, projectId, companyId, userId, erpType, addEntry, startPolling]);

  const handleConfirm = useCallback(async (decision: "confirm" | "cancel"): Promise<void> => {
    const wfId = wfRef.current;
    if (!wfId || gateSubmitting) return;

    if (decision === "cancel") {
      setConfirmReq(null);
      try { await confirmCommand(wfId, "cancel"); } catch { /* best-effort */ }
      addEntry(entry("system", "Cancelled — no changes made."));
      setPhase("cancelled");
      setInputLocked(false);
      setAgentStep("");
      return;
    }

    setGateSubmitting(true);
    try {
      await confirmCommand(wfId, "confirm");
      setConfirmReq(null);
      setPhase("polling");
      setAgentStep("executing");
      startPolling(wfId);
    } catch (err: unknown) {
      const raw = err instanceof Error ? err.message : "Failed to send confirmation";
      addEntry(entry("error", friendlyNetworkError("confirm", raw)));
      setPhase("awaiting_confirmation");
    } finally {
      setGateSubmitting(false);
    }
  }, [addEntry, startPolling, gateSubmitting]);

  const handleAnswer = useCallback(async (answer: string): Promise<void> => {
    const wfId = wfRef.current;
    if (!wfId || gateSubmitting) return;
    addEntry(entry("user", answer));
    setGateSubmitting(true);

    try {
      await answerClarification(wfId, answer);
      setConfirmReq(null);
      setPhase("polling");
      setAgentStep("clarity");
      startPolling(wfId);
    } catch (err: unknown) {
      const raw = err instanceof Error ? err.message : "Failed to send answer";
      addEntry(entry("error", friendlyNetworkError("answer", raw)));
      setPhase("awaiting_clarification");
    } finally {
      setGateSubmitting(false);
    }
  }, [addEntry, startPolling, gateSubmitting]);

  const handleDismiss = useCallback((): void => {
    setPhase("idle");
    setInputLocked(false);
    setAgentStep("");
  }, []);

  const isProcessing =
    phase === "submitting"
    || phase === "polling"
    || phase === "awaiting_clarification"
    || phase === "awaiting_confirmation";

  const clarificationUi = clarificationFromConfirmationRequest(confirmReq);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <PipelineStatus step={agentStep} visible={isProcessing} />
      <div style={{ flex: 1, overflow: "hidden", minHeight: 0 }}>
        <OutputLog entries={log} companyId={companyId} phase={phase} />
      </div>
      {phase === "awaiting_clarification" && clarificationUi && (
        <ClarificationBlock
          question={clarificationUi.question}
          round={clarificationUi.round}
          field={clarificationUi.field}
          candidates={clarificationUi.candidates}
          lockedContext={clarificationUi.lockedContext}
          onAnswer={handleAnswer}
          submitting={gateSubmitting}
        />
      )}
      {phase === "awaiting_confirmation" && confirmReq && (
        <ConfirmationBlock
          request={confirmReq}
          onDecide={handleConfirm}
          submitting={gateSubmitting}
        />
      )}
      {phase !== "awaiting_clarification" && phase !== "awaiting_confirmation" && (
        <TerminalInput companyId={companyId} onSubmit={handleSubmit} disabled={inputLocked} phase={phase} onDismissError={phase === "error" ? handleDismiss : undefined} />
      )}
    </div>
  );
}
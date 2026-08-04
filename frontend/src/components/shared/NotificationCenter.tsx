"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Bell, Loader2, Send } from "lucide-react";
import { createClient } from "@/utils/supabase/client";
import { getAuthUser } from "@/utils/auth-user";
import { isDevAuthBypassEnabled } from "@/utils/dev-auth";
import { departmentLabel } from "@/lib/departments";
import {
  fetchNotifications,
  markNotificationRead,
  replyToNotification,
  resolveProjectId,
  type NotificationRow,
} from "@/lib/api/notifications-api";

const POLL_MS = 8000;

interface Props {
  companySlug: string;
}

function riskColor(tier: string): string {
  if (tier === "critical") return "#ef4444";
  if (tier === "high") return "#f97316";
  if (tier === "medium") return "#eab308";
  return "#71717a";
}

export function NotificationCenter({ companySlug }: Props) {
  const supabase = createClient();
  const [open, setOpen] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [items, setItems] = useState<NotificationRow[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [replyText, setReplyText] = useState<Record<string, string>>({});
  const [replyBusy, setReplyBusy] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (isDevAuthBypassEnabled()) {
      getAuthUser().then(({ user }) => setUserId(user?.id ?? null));
      return;
    }
    supabase.auth.getUser().then(({ data: { user } }) => setUserId(user?.id ?? null));
  }, [supabase]);

  useEffect(() => {
    if (!companySlug) return;
    resolveProjectId(companySlug)
      .then(setProjectId)
      .catch(() => setProjectId(null));
  }, [companySlug]);

  const load = useCallback(async () => {
    if (!projectId || !userId) return;
    setLoading(true);
    setError("");
    try {
      const data = await fetchNotifications(projectId, userId);
      setItems(data.notifications);
      setUnread(data.unread_count);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load notifications");
    } finally {
      setLoading(false);
    }
  }, [projectId, userId]);

  useEffect(() => {
    if (!projectId || !userId) return;
    load();
    pollRef.current = setInterval(load, POLL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [projectId, userId, load]);

  const handleOpen = () => {
    setOpen((v) => !v);
    if (!open) load();
  };

  const handleMarkRead = async (id: string) => {
    if (!userId) return;
    await markNotificationRead(id, userId);
    await load();
  };

  const handleReply = async (notif: NotificationRow) => {
    if (!userId || !projectId) return;
    const prompt = (replyText[notif.id] || "").trim();
    if (!prompt) return;
    setReplyBusy(notif.id);
    setError("");
    try {
      const result = await replyToNotification(notif.id, {
        user_id: userId,
        company_id: companySlug,
        prompt,
      });
      setReplyText((prev) => ({ ...prev, [notif.id]: "" }));
      await load();
      setError(`Command dispatched (${result.workflow_id.slice(0, 12)}…)`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Reply failed");
    } finally {
      setReplyBusy(null);
    }
  };

  if (!userId || !projectId) return null;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={handleOpen}
        className="relative p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] transition-colors"
        aria-label="Notifications"
      >
        <Bell className="w-4 h-4" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-amber-500 text-black text-[10px] font-bold flex items-center justify-center">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div
          className="absolute right-0 top-full mt-2 w-[min(420px,calc(100vw-2rem))] max-h-[70vh] overflow-hidden flex flex-col rounded-xl border border-[var(--border-default)] bg-[var(--bg-shell)] shadow-2xl z-50"
          style={{ fontFamily: "var(--font-sans), system-ui, sans-serif" }}
        >
          <div className="px-4 py-3 border-b border-[var(--border-subtle)] flex items-center justify-between">
            <span className="text-sm font-semibold text-zinc-200">Operations inbox</span>
            {loading && <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-500" />}
          </div>

          {error && (
            <div className="px-4 py-2 text-xs text-amber-400/90 border-b border-[var(--border-subtle)]">
              {error}
            </div>
          )}

          <div className="overflow-y-auto flex-1 divide-y divide-[var(--border-subtle)]">
            {items.length === 0 && !loading ? (
              <p className="px-4 py-8 text-xs text-zinc-600 text-center">
                No notifications yet. ERPNext events will appear here after go-live.
              </p>
            ) : (
              items.map((n) => (
                <div key={n.id} className="px-4 py-3 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-zinc-200 truncate">{n.title}</p>
                      <p className="text-xs text-zinc-500 mt-0.5 leading-relaxed">{n.body}</p>
                    </div>
                    <span
                      className="shrink-0 text-[10px] uppercase font-bold tracking-wide"
                      style={{ color: riskColor(n.risk_tier) }}
                    >
                      {n.risk_tier}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-zinc-600">
                    {n.department && (
                      <span className="px-1.5 py-0.5 rounded bg-white/[0.04]">
                        {departmentLabel(n.department)}
                      </span>
                    )}
                    <span>{n.status}</span>
                    {n.created_at && (
                      <span>{new Date(n.created_at).toLocaleString()}</span>
                    )}
                  </div>
                  {n.status !== "actioned" && (
                    <div className="flex gap-2 pt-1">
                      <input
                        type="text"
                        value={replyText[n.id] || ""}
                        onChange={(e) =>
                          setReplyText((prev) => ({ ...prev, [n.id]: e.target.value }))
                        }
                        placeholder="Reply with an ERP command…"
                        className="flex-1 px-2.5 py-1.5 text-xs rounded-lg border border-[var(--border-default)] bg-[var(--bg-void)] text-zinc-200 outline-none focus:ring-1 focus:ring-amber-500/40"
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleReply(n);
                        }}
                      />
                      <button
                        type="button"
                        disabled={replyBusy === n.id}
                        onClick={() => handleReply(n)}
                        className="p-1.5 rounded-lg bg-amber-500 text-black hover:bg-amber-400 disabled:opacity-50"
                        title="Send to OS"
                      >
                        {replyBusy === n.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Send className="w-3.5 h-3.5" />
                        )}
                      </button>
                      {n.status !== "read" && (
                        <button
                          type="button"
                          onClick={() => handleMarkRead(n.id)}
                          className="px-2 py-1 text-[10px] text-zinc-500 hover:text-zinc-300"
                        >
                          Mark read
                        </button>
                      )}
                    </div>
                  )}
                  {n.related_os_workflow_id && (
                    <p className="text-[10px] text-zinc-600 font-mono truncate">
                      OS: {n.related_os_workflow_id}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

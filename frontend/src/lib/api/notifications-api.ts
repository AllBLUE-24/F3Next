/**
 * lib/api/notifications-api.ts
 */

import { getBaseApiUrl } from "@/lib/config";

export interface NotificationRow {
  id: string;
  title: string;
  body: string;
  department: string | null;
  risk_tier: string;
  status: string;
  channel: string;
  payload: Record<string, unknown>;
  related_os_workflow_id: string | null;
  created_at: string | null;
  read_at: string | null;
}

export interface NotificationListResponse {
  notifications: NotificationRow[];
  unread_count: number;
}

export interface NotificationReplyResponse {
  workflow_id: string;
  session_id: string;
  notification_id: string;
}

async function call<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${getBaseApiUrl()}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.text();
    let detail: string;
    try {
      detail = (JSON.parse(body) as { detail?: string }).detail ?? body;
    } catch {
      detail = body;
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export async function fetchNotifications(
  projectId: string,
  userId: string,
  limit = 30,
): Promise<NotificationListResponse> {
  const qs = new URLSearchParams({ user_id: userId, limit: String(limit) });
  return call<NotificationListResponse>(`/api/notifications/${projectId}?${qs}`);
}

export async function markNotificationRead(
  notificationId: string,
  userId: string,
): Promise<void> {
  await call(`/api/notifications/${notificationId}/read`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId }),
  });
}

export async function replyToNotification(
  notificationId: string,
  body: { user_id: string; company_id: string; prompt: string; mode?: string },
): Promise<NotificationReplyResponse> {
  return call<NotificationReplyResponse>(`/api/notifications/${notificationId}/reply`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function resolveProjectId(companySlug: string): Promise<string> {
  const data = await call<{ project_id: string }>(`/api/resolve/slug/${companySlug}`);
  return data.project_id;
}

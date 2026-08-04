"use client";

import { useCallback, useEffect, useState } from "react";
import { Copy, Loader2, Trash2, UserPlus, CheckCircle2 } from "lucide-react";
import { createClient } from "@/utils/supabase/client";
import { getAuthUser } from "@/utils/auth-user";
import { isDevAuthBypassEnabled } from "@/utils/dev-auth";
import { getBaseApiUrl } from "@/lib/config";
import { DEPARTMENTS, departmentLabel } from "@/lib/departments";

type InviteRow = {
  id: string;
  invite_code: string;
  invite_url: string;
  email: string | null;
  department: string | null;
  department_label?: string | null;
  status: string;
  created_at: string | null;
  expires_at: string | null;
};

type MemberRow = {
  client_id: string;
  full_name: string | null;
  email: string | null;
  role: string | null;
  department: string | null;
  department_label?: string | null;
  is_owner: boolean;
};

interface Props {
  companySlug: string;
}

export function TeamInvitesPanel({ companySlug }: Props) {
  const supabase = createClient();
  const [userId, setUserId] = useState<string | null>(null);
  const [invites, setInvites] = useState<InviteRow[]>([]);
  const [members, setMembers] = useState<MemberRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [forbidden, setForbidden] = useState(false);
  const [error, setError] = useState("");
  const [email, setEmail] = useState("");
  const [department, setDepartment] = useState("");
  const [busy, setBusy] = useState(false);
  const [copyId, setCopyId] = useState<string | null>(null);

  const loadInvites = useCallback(async (uid: string) => {
    setLoading(true);
    setError("");
    try {
      const [invRes, memRes] = await Promise.all([
        fetch(
          `${getBaseApiUrl()}/api/invites/list?company_slug=${encodeURIComponent(companySlug)}&user_id=${encodeURIComponent(uid)}`
        ),
        fetch(
          `${getBaseApiUrl()}/api/invites/members?company_slug=${encodeURIComponent(companySlug)}&user_id=${encodeURIComponent(uid)}`
        ),
      ]);
      if (invRes.status === 403) {
        setForbidden(true);
        return;
      }
      if (!invRes.ok) {
        const data = await invRes.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to load invites");
      }
      const invData = await invRes.json();
      setInvites(Array.isArray(invData.invites) ? invData.invites : []);

      if (memRes.ok) {
        const memData = await memRes.json();
        setMembers(Array.isArray(memData.members) ? memData.members : []);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load invites");
    } finally {
      setLoading(false);
    }
  }, [companySlug]);

  useEffect(() => {
    if (isDevAuthBypassEnabled()) {
      getAuthUser().then(({ user }) => {
        if (user) {
          setUserId(user.id);
          loadInvites(user.id);
        } else {
          setLoading(false);
        }
      });
      return;
    }

    supabase.auth.getUser().then(({ data: { user } }) => {
      if (user) {
        setUserId(user.id);
        loadInvites(user.id);
      } else {
        setLoading(false);
      }
    });
  }, [supabase, loadInvites]);

  const createInvite = async () => {
    if (!userId) return;
    setBusy(true);
    setError("");
    try {
      const res = await fetch(`${getBaseApiUrl()}/api/invites/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          company_slug: companySlug,
          email: email.trim() || undefined,
          department: department || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create invite");
      setEmail("");
      setDepartment("");
      await loadInvites(userId);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create invite");
    } finally {
      setBusy(false);
    }
  };

  const updateMemberDepartment = async (memberClientId: string, nextDept: string) => {
    if (!userId) return;
    setBusy(true);
    setError("");
    try {
      const res = await fetch(`${getBaseApiUrl()}/api/invites/members/department`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          company_slug: companySlug,
          member_client_id: memberClientId,
          department: nextDept || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to update department");
      await loadInvites(userId);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update department");
    } finally {
      setBusy(false);
    }
  };

  const revokeInvite = async (inviteId: string) => {
    if (!userId) return;
    setBusy(true);
    setError("");
    try {
      const res = await fetch(`${getBaseApiUrl()}/api/invites/revoke`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, invite_id: inviteId }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to revoke invite");
      await loadInvites(userId);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to revoke invite");
    } finally {
      setBusy(false);
    }
  };

  const copyLink = async (invite: InviteRow) => {
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    await navigator.clipboard.writeText(`${origin}${invite.invite_url}`);
    setCopyId(invite.id);
    setTimeout(() => setCopyId(null), 2000);
  };

  if (forbidden) return null;

  return (
    <section className="space-y-3 md:col-span-2">
      <div className="flex items-center gap-2.5 border-b border-[var(-border-subtle)] pb-2">
        <UserPlus className="h-4 w-4 text-amber-500" />
        <h2 className="text-sm font-bold text-white">Team invites</h2>
      </div>

      <div className="surface-card p-5 space-y-4" style={{ borderRadius: "var(--radius-lg)" }}>
        {error && (
          <div className="p-3 text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl">
            {error}
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-2">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="colleague@company.com (optional)"
            className="flex-1 px-3.5 py-2.5 border border-[var(--border-default)] rounded-xl text-sm text-zinc-200 bg-[var(--bg-void)] outline-none focus:ring-2 focus:ring-amber-500/30"
          />
          <select
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            className="px-3.5 py-2.5 border border-[var(--border-default)] rounded-xl text-sm text-zinc-200 bg-[var(--bg-void)] outline-none focus:ring-2 focus:ring-amber-500/30 min-w-[160px]"
          >
            <option value="">Department (optional)</option>
            {DEPARTMENTS.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            disabled={busy || !userId}
            onClick={createInvite}
            className="px-4 py-2.5 rounded-xl text-sm font-bold text-black bg-amber-500 hover:bg-amber-400 disabled:opacity-50 whitespace-nowrap"
          >
            {busy ? "Creating…" : "New invite link"}
          </button>
        </div>

        {members.length > 0 && (
          <div className="space-y-2 pt-2 border-t border-[var(--border-subtle)]">
            <p className="text-[11px] font-bold uppercase tracking-wider text-zinc-500">Team members</p>
            <ul className="divide-y divide-[var(--border-subtle)]">
              {members.map((m) => (
                <li key={m.client_id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 py-2">
                  <div className="min-w-0">
                    <p className="text-sm text-zinc-300 truncate">
                      {m.full_name || m.email || m.client_id}
                      {m.is_owner ? " (owner)" : ""}
                    </p>
                    <p className="text-[11px] text-zinc-600">{m.role || "Member"}</p>
                  </div>
                  {m.is_owner ? (
                    <span className="text-xs text-zinc-500">{departmentLabel(m.department)}</span>
                  ) : (
                    <select
                      value={m.department || ""}
                      disabled={busy}
                      onChange={(e) => updateMemberDepartment(m.client_id, e.target.value)}
                      className="px-2.5 py-1.5 border border-[var(--border-default)] rounded-lg text-xs text-zinc-200 bg-[var(--bg-void)]"
                    >
                      <option value="">Unassigned</option>
                      {DEPARTMENTS.map((d) => (
                        <option key={d.value} value={d.value}>
                          {d.label}
                        </option>
                      ))}
                    </select>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {loading ? (
          <div className="flex items-center gap-2 text-sm text-zinc-500 py-4">
            <Loader2 className="w-4 h-4 animate-spin text-amber-500" /> Loading invites…
          </div>
        ) : invites.length === 0 ? (
          <p className="text-xs text-zinc-600">No active invites. Create a link to share with colleagues.</p>
        ) : (
          <ul className="divide-y divide-[var(--border-subtle)]">
            {invites.map((inv) => (
              <li key={inv.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                <div className="min-w-0">
                  <p className="text-sm text-zinc-300 font-mono truncate">{inv.invite_url}</p>
                  <p className="text-[11px] text-zinc-600 mt-0.5">
                    {inv.email ? `For ${inv.email} · ` : ""}
                    {inv.department ? `${departmentLabel(inv.department)} · ` : ""}
                    {inv.status}
                    {inv.expires_at ? ` · expires ${new Date(inv.expires_at).toLocaleDateString()}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => copyLink(inv)}
                    className="p-2 rounded-lg border border-[var(--border-default)] text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
                    title="Copy link"
                  >
                    {copyId === inv.id ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => revokeInvite(inv.id)}
                    className="p-2 rounded-lg border border-red-500/20 text-red-400/80 hover:text-red-400 hover:bg-red-500/10 disabled:opacity-50"
                    title="Revoke invite"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/utils/supabase/client";

// Helper for slug generation
const slugify = (text: string) => {
  return text
    .toString()
    .toLowerCase()
    .trim()
    .replace(/\s+/g, "-")
    .replace(/[^\w\-]+/g, "")
    .replace(/\-\-+/g, "-");
};

interface PageProps {
  params: Promise<{ companySlug: string; inviteCode: string }>;
}

function InviteForm({ companySlug, inviteCode }: { companySlug: string; inviteCode: string }) {
  const router = useRouter();
  const supabase = createClient();
  
  const [user, setUser] = useState<any>(null);
  const [authLoading, setAuthLoading] = useState(true);

  // State
  const [isValidating, setIsValidating] = useState(true);
  const [inviteData, setInviteData] = useState<any>(null);
  const [error, setError] = useState("");
  
  // Onboarding Form State
  const [formData, setFormData] = useState({
    fullName: "",
    userSlug: "",
    role: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Auth Effect
  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user);
      setAuthLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => {
      subscription?.unsubscribe();
    };
  }, [supabase]);

  // 2. Validate Invite Code on Load
  useEffect(() => {
    const checkInvite = async () => {
      try {
        const API_URL = "";
        
        // Mocking the validation API call
        // In real backend, check if code exists and matches companySlug
        const res = await fetch(`${API_URL}/api/invites/validate?code=${inviteCode}&slug=${companySlug}`);
        
        if (!res.ok) {
          throw new Error("This invite link is invalid or has expired.");
        }

        const data = await res.json();
        setInviteData(data); // { company_name: "Tesla Motors", ... }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setIsValidating(false);
      }
    };

    checkInvite();
  }, [inviteCode, companySlug]);

  // 3. Handle Form Logic
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => {
      const next = { ...prev, [name]: value };
      if (name === "fullName") next.userSlug = slugify(value);
      return next;
    });
  };

  const handleSlugChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, [e.target.name]: slugify(e.target.value) }));
  };

  const handleJoinTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setIsSubmitting(true);

    try {
      const API_URL = "";
      
      const res = await fetch(`${API_URL}/api/invites/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          invite_code: inviteCode,
          user_id: user.id, // Supabase UID
          full_name: formData.fullName,
          user_slug: formData.userSlug,
          role: formData.role
        }),
      });

      if (!res.ok) throw new Error("Failed to join team. Please try again.");

      // Success: Redirect to their new workspace
      router.push(`/${companySlug}/${formData.userSlug}/home`);
      
    } catch (err: any) {
      setError(err.message);
      setIsSubmitting(false);
    }
  };

  // 4. Render States
  
  if (isValidating || authLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-950 text-white">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent mx-auto mb-4"></div>
          <p>Verifying invitation...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-950 p-4">
        <div className="max-w-md text-center">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-red-900/20 mb-6">
            <svg className="h-8 w-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Invite Invalid</h1>
          <p className="text-zinc-400 mb-6">{error}</p>
          <Link href="/" className="text-blue-400 hover:text-blue-300">
            Return to Home
          </Link>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex h-screen items-center justify-center bg-zinc-950 p-4">
        <div className="w-full max-w-md rounded-xl border border-zinc-800 bg-zinc-900/50 p-8 text-center backdrop-blur-sm">
          <div className="mb-6">
            <h1 className="text-2xl font-bold text-white">You've been invited!</h1>
            <p className="mt-2 text-zinc-400">
              Join <strong className="text-white">{inviteData?.company_name || companySlug}</strong> on F3Next.
            </p>
          </div>
          
          <div className="space-y-4">
            <p className="text-sm text-zinc-500">Please log in to accept this invitation.</p>
            <Link 
              href={`/login?redirect=/${companySlug}/invite/${inviteCode}`}
              className="block w-full rounded-md bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-500"
            >
              Log In or Sign Up
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 p-4">
      <div className="w-full max-w-lg rounded-xl border border-zinc-800 bg-zinc-900/50 p-8 shadow-xl backdrop-blur-sm">
        
        <div className="mb-8 border-b border-zinc-800 pb-6">
          <span className="mb-2 inline-block rounded-full bg-blue-500/10 px-3 py-1 text-xs font-medium text-blue-400">
            Team Invitation
          </span>
          <h1 className="text-2xl font-bold text-white">
            Join {inviteData?.company_name || companySlug}
          </h1>
          <p className="mt-2 text-sm text-zinc-400">
            Set up your profile for this workspace.
          </p>
        </div>

        <form onSubmit={handleJoinTeam} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-zinc-500 mb-1">Signed in as</label>
            <div className="flex items-center space-x-2 text-zinc-300">
              <div className="h-2 w-2 rounded-full bg-green-500"></div>
              <span>{user.email}</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-1">Full Name</label>
            <input
              name="fullName"
              type="text"
              required
              placeholder="Jane Doe"
              value={formData.fullName}
              onChange={handleChange}
              className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-white placeholder-zinc-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">Your Role</label>
              <input
                name="role"
                type="text"
                required
                placeholder="Engineer"
                value={formData.role}
                onChange={handleChange}
                className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-white focus:border-blue-500 focus:outline-none"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1">User Handle</label>
              <div className="flex items-center rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2">
                 <span className="mr-1 text-zinc-500">@</span>
                 <input
                  name="userSlug"
                  type="text"
                  required
                  value={formData.userSlug}
                  onChange={handleSlugChange}
                  className="w-full bg-transparent text-white placeholder-zinc-500 focus:outline-none"
                />
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-4 rounded-md bg-white px-4 py-3 text-sm font-bold text-black shadow hover:bg-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? "Joining Workspace..." : "Confirm & Join Team"}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function InvitePage({ params }: PageProps) {
  const { companySlug, inviteCode } = use(params);
  return <InviteForm companySlug={companySlug} inviteCode={inviteCode} />;
}
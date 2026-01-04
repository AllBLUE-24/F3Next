"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/firebase"; // Import your firebase config
import { useAuthState } from "react-firebase-hooks/auth"; // You might need to install this: npm i react-firebase-hooks

// Helper to turn "Tesla Motors" -> "tesla-motors"
const slugify = (text: string) => {
  return text
    .toString()
    .toLowerCase()
    .trim()
    .replace(/\s+/g, "-")     // Replace spaces with -
    .replace(/[^\w\-]+/g, "") // Remove all non-word chars
    .replace(/\-\-+/g, "-");  // Replace multiple - with single -
};

export default function OnboardingPage() {
  const router = useRouter();
  const [user, loading] = useAuthState(auth);

  // Form State
  const [formData, setFormData] = useState({
    fullName: "",
    userSlug: "",
    role: "",
    companyName: "",
    companySlug: "",
  });

  // UI State
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Redirect if not logged in
  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  // Handle Input Changes
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;

    setFormData((prev) => {
      const newData = { ...prev, [name]: value };

      // Auto-generate slugs if the user hasn't manually edited them yet
      if (name === "fullName") {
        newData.userSlug = slugify(value);
      }
      if (name === "companyName") {
        newData.companySlug = slugify(value);
      }
      return newData;
    });

    // Clear errors when typing
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }));
    }
  };

  // Specific handler for manual slug editing (to prevent auto-overwrite)
  const handleSlugChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: slugify(e.target.value) });
  };

  // Submit Handler
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrors({});

    try {
      if (!user) return;

      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      
      const res = await fetch(`${API_URL}/api/onboarding/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user.uid,
          full_name: formData.fullName,
          user_slug: formData.userSlug,
          role: formData.role,
          company_name: formData.companyName,
          company_slug: formData.companySlug,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Something went wrong");
      }

      // Success! Redirect to the dynamic URL
      router.push(`/${formData.companySlug}/${formData.userSlug}/home`);
      
    } catch (error: any) {
      console.error(error);
      setErrors({ form: error.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) return <div className="p-8 text-white">Loading...</div>;

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 p-4">
      <div className="w-full max-w-md space-y-8 rounded-xl border border-zinc-800 bg-zinc-900/50 p-8 shadow-xl backdrop-blur-sm">
        
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Welcome to F3Next
          </h1>
          <p className="mt-2 text-sm text-zinc-400">
            Let's set up your workspace context.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          
          {/* USER SECTION */}
          <div className="space-y-4">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
              Personal Profile
            </h2>
            
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-300">
                Your Full Name
              </label>
              <input
                name="fullName"
                type="text"
                required
                value={formData.fullName}
                onChange={handleChange}
                placeholder="e.g. Parth Patel"
                className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-white placeholder-zinc-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
               <div>
                <label className="mb-1 block text-sm font-medium text-zinc-300">
                  Your Role
                </label>
                <input
                  name="role"
                  type="text"
                  required
                  value={formData.role}
                  onChange={handleChange}
                  placeholder="e.g. CTO"
                  className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-white placeholder-zinc-500 focus:border-blue-500 focus:outline-none"
                />
              </div>
              
              <div>
                <label className="mb-1 block text-sm font-medium text-zinc-300">
                  User Handle
                </label>
                <div className="flex items-center rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2">
                   <span className="mr-1 text-zinc-500">/</span>
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
          </div>

          <div className="h-px bg-zinc-800" />

          {/* COMPANY SECTION */}
          <div className="space-y-4">
             <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
              Company Workspace
            </h2>
            
            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-300">
                Company Name
              </label>
              <input
                name="companyName"
                type="text"
                required
                value={formData.companyName}
                onChange={handleChange}
                placeholder="e.g. Tesla Motors"
                className="w-full rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-white placeholder-zinc-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-zinc-300">
                Workspace URL
              </label>
              <div className="flex items-center rounded-md border border-zinc-700 bg-zinc-800 px-3 py-2 text-zinc-400">
                <span className="hidden sm:inline">f3next.in/</span>
                <input
                  name="companySlug"
                  type="text"
                  required
                  value={formData.companySlug}
                  onChange={handleSlugChange}
                  className="w-full bg-transparent text-white focus:outline-none ml-1"
                />
              </div>
              <p className="mt-1 text-xs text-zinc-500">
                This will be your permanent workspace link.
              </p>
            </div>
          </div>

          {/* ERROR DISPLAY */}
          {errors.form && (
            <div className="rounded-md bg-red-500/10 p-3 text-sm text-red-400 border border-red-500/20">
              {errors.form}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-md bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? "Setting up..." : "Complete Setup"}
          </button>
        </form>
      </div>
    </div>
  );
}
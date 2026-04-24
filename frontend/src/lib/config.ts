/**
 * lib/config.ts — Central API Router
 *
 * Split-brain routing: the correct base URL is determined by execution context.
 *  - Browser (client components):  NEXT_PUBLIC_API_URL  (e.g. "" for relative, or "https://yourdomain.com")
 *  - Node.js SSR / Server Actions: INTERNAL_API_URL     (e.g. "http://backend_api:8000" in Docker, "http://127.0.0.1:8000" locally)
 *
 * DO NOT hardcode "http://backend_api:8000" anywhere else in the codebase.
 * Import and call getBaseApiUrl() instead.
 */
export function getBaseApiUrl(): string {
  if (typeof window !== "undefined") {
    // Running in the browser — use the public-facing URL (or empty string for relative paths)
    return process.env.NEXT_PUBLIC_API_URL || "";
  }
  // Running on the server (SSR, Server Components, Server Actions, Route Handlers)
  return process.env.INTERNAL_API_URL || "http://127.0.0.1:8000";
}

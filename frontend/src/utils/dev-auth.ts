/**
 * Local dev auth bypass — skips Supabase Auth when Supabase is restricted.
 *
 * Enable in frontend/.env.local (or root .env for Docker):
 *   NEXT_PUBLIC_DEV_AUTH_BYPASS=true
 *   NEXT_PUBLIC_DEV_AUTH_USER_ID=dev-user-local-001
 *   NEXT_PUBLIC_DEV_AUTH_EMAIL=dev@f3next.local
 *
 * Only active when NODE_ENV=development. Never enable in production builds.
 */

export type DevAuthUser = {
  id: string;
  email: string;
};

const DEFAULT_DEV_USER_ID = 'dev-user-local-001';
const DEFAULT_DEV_EMAIL = 'dev@f3next.local';

export function isDevAuthBypassEnabled(): boolean {
  if (process.env.NODE_ENV !== 'development') {
    return false;
  }
  return process.env.NEXT_PUBLIC_DEV_AUTH_BYPASS === 'true';
}

export function getDevAuthUser(): DevAuthUser {
  return {
    id: process.env.NEXT_PUBLIC_DEV_AUTH_USER_ID || DEFAULT_DEV_USER_ID,
    email: process.env.NEXT_PUBLIC_DEV_AUTH_EMAIL || DEFAULT_DEV_EMAIL,
  };
}

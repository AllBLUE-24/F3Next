import { createClient } from '@/utils/supabase/client';
import { getDevAuthUser, isDevAuthBypassEnabled, type DevAuthUser } from '@/utils/dev-auth';

export type AuthUser = DevAuthUser;

/**
 * Returns the current user — dev bypass user in local test mode, else Supabase session.
 */
export async function getAuthUser(): Promise<{ user: AuthUser | null; error: Error | null }> {
  if (isDevAuthBypassEnabled()) {
    return { user: getDevAuthUser(), error: null };
  }

  const supabase = createClient();
  const { data, error } = await supabase.auth.getUser();
  if (error) {
    return { user: null, error };
  }
  if (!data.user) {
    return { user: null, error: null };
  }

  return {
    user: {
      id: data.user.id,
      email: data.user.email || '',
    },
    error: null,
  };
}

export async function signOutAuth(): Promise<void> {
  if (isDevAuthBypassEnabled()) {
    return;
  }
  const supabase = createClient();
  await supabase.auth.signOut();
}

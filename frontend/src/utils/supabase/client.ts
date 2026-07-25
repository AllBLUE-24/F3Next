import { createBrowserClient } from '@supabase/ssr'

import { getSupabaseAnonKey, getSupabaseUrl } from '@/utils/supabase/config'

export function createClient() {
  return createBrowserClient(getSupabaseUrl(), getSupabaseAnonKey())
}

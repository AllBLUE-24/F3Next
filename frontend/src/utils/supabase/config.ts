import { isDevAuthBypassEnabled } from '@/utils/dev-auth'

/** Non-routable placeholders so @supabase/ssr can construct a client without real credentials. */
const DEV_PLACEHOLDER_URL = 'http://127.0.0.1:54321'
const DEV_PLACEHOLDER_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dev-bypass-placeholder'

function trimEnv(value: string | undefined): string {
  return value?.trim() ?? ''
}

export function getSupabaseUrl(): string {
  const url = trimEnv(process.env.NEXT_PUBLIC_SUPABASE_URL)
  if (url) return url
  if (isDevAuthBypassEnabled()) return DEV_PLACEHOLDER_URL
  return ''
}

export function getSupabaseAnonKey(): string {
  const key = trimEnv(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY)
  if (key) return key
  if (isDevAuthBypassEnabled()) return DEV_PLACEHOLDER_ANON_KEY
  return ''
}

export function hasRealSupabaseConfig(): boolean {
  return Boolean(
    trimEnv(process.env.NEXT_PUBLIC_SUPABASE_URL) &&
      trimEnv(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY)
  )
}

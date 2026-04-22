import { createServerClient } from '@supabase/ssr'
import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const code = searchParams.get('code')
  // After OAuth, route to /auth/resolve which handles slug lookup + routing
  const next = searchParams.get('next') ?? '/auth/resolve'

  // Get a reliable base URL using headers to prevent Next.js standalone
  // from resolving to 0.0.0.0:3000 when behind a reverse proxy.
  const host = request.headers.get('x-forwarded-host') || request.headers.get('host')
  const protocol = request.headers.get('x-forwarded-proto') || 'https'
  const baseUrl = host ? `${protocol}://${host}` : new URL(request.url).origin

  if (code) {
    const cookieStore = await cookies()
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() {
            return cookieStore.getAll()
          },
          setAll(cookiesToSet) {
            try {
              cookiesToSet.forEach(({ name, value, options }) =>
                cookieStore.set(name, value, options)
              )
            } catch {
              // Ignored in Server Components — middleware refreshes sessions
            }
          },
        },
      }
    )

    const { error } = await supabase.auth.exchangeCodeForSession(code)
    if (!error) {
      console.log('[Callback] Code exchanged successfully, redirecting to', next)
      return NextResponse.redirect(`${baseUrl}${next}`)
    }
    console.error('[Callback] Code exchange failed:', error)
  }

  // Code exchange failed — redirect to login with error
  return NextResponse.redirect(`${baseUrl}/login?error=auth_callback_failed`)
}

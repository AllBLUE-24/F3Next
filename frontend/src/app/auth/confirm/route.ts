import { createServerClient } from '@supabase/ssr'
import type { EmailOtpType } from '@supabase/supabase-js'
import { NextResponse } from 'next/server'
import { cookies } from 'next/headers'

function getBaseUrl(request: Request) {
  const url = new URL(request.url)
  const host =
    request.headers.get('x-forwarded-host') ||
    request.headers.get('host') ||
    url.host

  const isLocalHost =
    host.startsWith('localhost') || host.startsWith('127.0.0.1')

  const protocol =
    request.headers.get('x-forwarded-proto') ||
    (isLocalHost ? 'http' : 'https')

  return `${protocol}://${host}`
}

function normalizeNextPath(next: string | null, fallback = '/auth/resolve') {
  if (next && next.startsWith('/')) {
    return next
  }

  return fallback
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const tokenHash = searchParams.get('token_hash')
  const type = searchParams.get('type')
  const next = normalizeNextPath(searchParams.get('next'))
  const baseUrl = getBaseUrl(request)

  if (tokenHash && type) {
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

    const { error } = await supabase.auth.verifyOtp({
      type: type as EmailOtpType,
      token_hash: tokenHash,
    })

    if (!error) {
      return NextResponse.redirect(`${baseUrl}${next}`)
    }

    console.error('[Confirm] OTP verification failed:', error)
  }

  return NextResponse.redirect(`${baseUrl}/login?error=email_confirmation_failed`)
}

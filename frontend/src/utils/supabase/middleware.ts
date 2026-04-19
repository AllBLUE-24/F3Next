import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

// Public routes that don't require authentication
const PUBLIC_ROUTES = [
  '/login',
  '/signup',
  '/auth/callback',
  '/auth/resolve',
  '/landing',
  '/landing_page',
  '/onboarding',
  '/dev/test',
  '/api',
]

function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some((route) => pathname.startsWith(route))
}

// Auth routes that authenticated users should NOT see
const AUTH_ROUTES = ['/login', '/signup']

function isAuthRoute(pathname: string): boolean {
  return AUTH_ROUTES.some((route) => pathname.startsWith(route))
}

/**
 * Create a redirect response that preserves Supabase session cookies.
 * This is CRITICAL — without this, session cookies set during getUser()
 * token refresh are lost on redirect, causing the infinite loop.
 */
function createRedirectWithCookies(
  url: URL,
  supabaseResponse: NextResponse
): NextResponse {
  const redirectResponse = NextResponse.redirect(url)
  supabaseResponse.cookies.getAll().forEach((cookie) => {
    redirectResponse.cookies.set(cookie)
  })
  return redirectResponse
}

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          )
          supabaseResponse = NextResponse.next({ request })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  // IMPORTANT: Do not add logic between createServerClient and getUser().
  const {
    data: { user },
  } = await supabase.auth.getUser()

  const pathname = request.nextUrl.pathname
  console.log(`[Middleware] path=${pathname} user=${user?.id ?? 'null'}`)

  // 1. Root URL → always redirect to /landing
  if (pathname === '/') {
    const url = request.nextUrl.clone()
    url.pathname = '/landing'
    return createRedirectWithCookies(url, supabaseResponse)
  }

  // 2. Authenticated user on an auth page → send to /auth/resolve
  if (user && isAuthRoute(pathname)) {
    console.log(`[Middleware] Authed user on ${pathname} → /auth/resolve`)
    const url = request.nextUrl.clone()
    url.pathname = '/auth/resolve'
    return createRedirectWithCookies(url, supabaseResponse)
  }

  // 3. Unauthenticated user on a protected page → send to /login
  if (!user && !isPublicRoute(pathname) && pathname !== '/') {
    console.log(`[Middleware] Unauthed access to ${pathname} → /login`)
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return createRedirectWithCookies(url, supabaseResponse)
  }

  // 4. Everything else → pass through with refreshed cookies
  return supabaseResponse
}

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
  return PUBLIC_ROUTES.some((route) => {
    // Exact match for /auth/callback — don't let /auth/callback/home slip through
    if (route === '/auth/callback') return pathname === '/auth/callback'
    return pathname.startsWith(route)
  })
}

// Auth routes that authenticated users should NOT see
const AUTH_ROUTES = ['/login', '/signup']

function isAuthRoute(pathname: string): boolean {
  return AUTH_ROUTES.some((route) => pathname.startsWith(route))
}

// Known top-level routes that are NOT [companySlug]/[userSlug] workspaces
const KNOWN_TOP_ROUTES = [
  'login', 'signup', 'auth', 'landing', 'landing_page',
  'onboarding', 'dev', 'api', '_next', 'favicon.ico',
]

/**
 * Check if a path looks like a workspace route: /[companySlug]/[userSlug]/...
 */
function isWorkspaceRoute(pathname: string): boolean {
  const segments = pathname.split('/').filter(Boolean)
  if (segments.length < 2) return false
  return !KNOWN_TOP_ROUTES.includes(segments[0])
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

  // 2. Authenticated user on an auth page or onboarding → SSR check
  if (user && (isAuthRoute(pathname) || pathname === '/onboarding' || pathname === '/auth/resolve')) {
    console.log(`[Middleware] Authed user on ${pathname} → checking onboarding status`)
    
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://backend_api:8000'
    try {
      const res = await fetch(`${API_URL}/api/resolve/user/${user.id}`)
      if (res.ok) {
        const data = await res.json()
        if (data.company_slug && data.user_slug) {
          // Fully onboarded → redirect to home SSR
          const homeUrl = request.nextUrl.clone()
          homeUrl.pathname = `/${data.company_slug}/${data.user_slug}/home`
          return createRedirectWithCookies(homeUrl, supabaseResponse)
        }
      }
      
      // Not onboarded (or missing slugs) → redirect to onboarding
      if (pathname !== '/onboarding') {
        const url = request.nextUrl.clone()
        url.pathname = '/onboarding'
        return createRedirectWithCookies(url, supabaseResponse)
      }
      
      // If already on /onboarding, just let them pass through
      return supabaseResponse
    } catch (e) {
      console.error('[Middleware] Backend fetch error:', e)
      // Fallback behavior if the backend is unreachable
      if (pathname !== '/auth/resolve' && pathname !== '/onboarding') {
        const url = request.nextUrl.clone()
        url.pathname = '/auth/resolve'
        return createRedirectWithCookies(url, supabaseResponse)
      }
    }
  }

  // 3. Unauthenticated user on a protected page → send to /login
  if (!user && !isPublicRoute(pathname) && pathname !== '/') {
    console.log(`[Middleware] Unauthed access to ${pathname} → /login`)
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return createRedirectWithCookies(url, supabaseResponse)
  }

  // 4. Workspace route validation: /[companySlug]/[userSlug]/...
  //    Verify that the slugs actually exist in the database
  if (user && isWorkspaceRoute(pathname)) {
    const segments = pathname.split('/').filter(Boolean)
    const companySlug = segments[0]
    const userSlug = segments[1]

    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://backend_api:8000'
    try {
      const res = await fetch(`${API_URL}/api/resolve/slug/${companySlug}`)
      if (!res.ok) {
        // Company slug doesn't exist → redirect to auth/resolve to find correct workspace
        console.log(`[Middleware] Invalid companySlug '${companySlug}' → /auth/resolve`)
        const url = request.nextUrl.clone()
        url.pathname = '/auth/resolve'
        return createRedirectWithCookies(url, supabaseResponse)
      }
    } catch (e) {
      // Backend unreachable — let it pass through, page will handle the error
      console.error('[Middleware] Workspace validation fetch error:', e)
    }
  }

  // 5. Everything else → pass through with refreshed cookies
  return supabaseResponse
}

import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

const PUBLIC_ROUTES = [
  '/login',
  '/signup',
  '/auth/callback',
  '/auth/confirm',
  '/auth/resolve',
  '/landing',
  '/dev/test',
  '/api',
]

function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some((route) => {
    if (route === '/auth/callback' || route === '/auth/confirm') {
      return pathname === route
    }

    return pathname.startsWith(route)
  })
}

function getRedirectUrl(request: NextRequest, targetPath: string): URL {
  const host =
    request.headers.get('x-forwarded-host') ||
    request.headers.get('host') ||
    request.nextUrl.host

  const isLocalHost =
    host.startsWith('localhost') || host.startsWith('127.0.0.1')

  const protocol =
    request.headers.get('x-forwarded-proto') ||
    (isLocalHost ? 'http' : 'https')

  return new URL(targetPath, `${protocol}://${host}`)
}

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

  const {
    data: { user },
  } = await supabase.auth.getUser()

  const pathname = request.nextUrl.pathname

  if (pathname === '/') {
    if (request.nextUrl.searchParams.has('code')) {
      const url = getRedirectUrl(request, '/auth/callback')

      request.nextUrl.searchParams.forEach((value, key) => {
        url.searchParams.set(key, value)
      })

      return createRedirectWithCookies(url, supabaseResponse)
    }

    return createRedirectWithCookies(
      getRedirectUrl(request, '/landing'),
      supabaseResponse
    )
  }

  if (user && (pathname === '/login' || pathname === '/signup')) {
    return createRedirectWithCookies(
      getRedirectUrl(request, '/auth/resolve'),
      supabaseResponse
    )
  }

  if (!user && !isPublicRoute(pathname)) {
    return createRedirectWithCookies(
      getRedirectUrl(request, '/login'),
      supabaseResponse
    )
  }

  return supabaseResponse
}

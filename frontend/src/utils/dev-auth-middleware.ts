import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

import { isDevAuthBypassEnabled } from '@/utils/dev-auth';

const PUBLIC_ROUTES = [
  '/login',
  '/signup',
  '/auth/callback',
  '/auth/confirm',
  '/auth/resolve',
  '/landing',
  '/dev/test',
  '/api',
];

function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some((route) => {
    if (route === '/auth/callback' || route === '/auth/confirm') {
      return pathname === route;
    }
    return pathname.startsWith(route);
  });
}

function getRedirectUrl(request: NextRequest, targetPath: string): URL {
  const host =
    request.headers.get('x-forwarded-host') ||
    request.headers.get('host') ||
    request.nextUrl.host;

  const isLocalHost =
    host.startsWith('localhost') || host.startsWith('127.0.0.1');

  const protocol =
    request.headers.get('x-forwarded-proto') ||
    (isLocalHost ? 'http' : 'https');

  return new URL(targetPath, `${protocol}://${host}`);
}

/**
 * Skip Supabase session checks — treat all routes as authenticated in dev test mode.
 */
export function handleDevAuthBypass(request: NextRequest): NextResponse | null {
  if (!isDevAuthBypassEnabled()) {
    return null;
  }

  const pathname = request.nextUrl.pathname;

  if (pathname === '/') {
    return NextResponse.redirect(getRedirectUrl(request, '/landing'));
  }

  if (pathname === '/login' || pathname === '/signup') {
    return NextResponse.redirect(getRedirectUrl(request, '/auth/resolve'));
  }

  if (!isPublicRoute(pathname)) {
    return NextResponse.next({ request });
  }

  return NextResponse.next({ request });
}

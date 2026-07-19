import type { NextRequest } from 'next/server'
import { updateSession } from '@/utils/supabase/middleware'
import { handleDevAuthBypass } from '@/utils/dev-auth-middleware'

export async function middleware(request: NextRequest) {
  const bypassResponse = handleDevAuthBypass(request)
  if (bypassResponse) {
    return bypassResponse
  }

  return await updateSession(request)
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}

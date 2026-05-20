import { type NextRequest, NextResponse } from 'next/server'

const PUBLIC_PATHS = new Set(['/login'])

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Allow public routes through without checking auth
  if (PUBLIC_PATHS.has(pathname)) {
    return NextResponse.next()
  }

  // Allow Next.js internals and static assets
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname === '/favicon.ico'
  ) {
    return NextResponse.next()
  }

  const token = request.cookies.get('mt_token')?.value

  if (!token) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('next', pathname)
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  // Run on all routes except static files and Next.js internals
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}

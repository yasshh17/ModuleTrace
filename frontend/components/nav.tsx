'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'

import { useAuth } from '@/app/lib/auth'
import type { Role } from '@/app/lib/types'
import { cn } from '@/lib/utils'

interface NavLink {
  label: string
  href: string
  roles: Role[]
}

const NAV_LINKS: NavLink[] = [
  { label: 'Scan', href: '/scan', roles: ['operator', 'engineer', 'admin'] },
  { label: 'Lookup', href: '/lookup', roles: ['engineer', 'quality', 'admin'] },
  { label: 'Dashboard', href: '/dashboard', roles: ['engineer', 'admin'] },
  { label: 'RMA', href: '/rma', roles: ['quality', 'admin'] },
]

export function Nav() {
  const { user, logout } = useAuth()
  const pathname = usePathname()
  const router = useRouter()

  if (!user) return null

  const visibleLinks = NAV_LINKS.filter((link) =>
    link.roles.includes(user.role),
  )

  function handleLogout() {
    logout()
    router.push('/login')
  }

  return (
    <header className="h-12 border-b border-border bg-card flex items-center px-4 gap-6 shrink-0">
      {/* Logo */}
      <Link
        href="/dashboard"
        className="flex items-center gap-2 shrink-0"
      >
        <span className="flex h-6 w-6 items-center justify-center rounded bg-primary text-primary-foreground text-xs font-bold">
          MT
        </span>
        <span className="text-sm font-semibold tracking-tight hidden sm:block">
          ModuleTrace
        </span>
      </Link>

      {/* Nav links */}
      <nav className="flex items-center gap-1 flex-1">
        {visibleLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
              pathname === link.href || pathname.startsWith(link.href + '/')
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted',
            )}
          >
            {link.label}
          </Link>
        ))}
      </nav>

      {/* User + logout */}
      <div className="flex items-center gap-3 shrink-0">
        <span className="text-sm text-muted-foreground hidden md:block">
          {user.full_name}
        </span>
        <button
          onClick={handleLogout}
          className="text-xs text-muted-foreground hover:text-foreground border border-border rounded-md px-2.5 py-1 transition-colors hover:bg-muted"
        >
          Sign out
        </button>
      </div>
    </header>
  )
}

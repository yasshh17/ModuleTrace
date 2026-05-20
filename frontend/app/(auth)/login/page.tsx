'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

import { useAuth } from '@/app/lib/auth'
import type { Role } from '@/app/lib/types'
import { ApiError } from '@/app/lib/api'

const ROLE_REDIRECTS: Record<Role, string> = {
  operator: '/scan',
  engineer: '/lookup',
  quality: '/rma',
  admin: '/dashboard',
}

const DEMO_HINTS = [
  { label: 'Operator', email: 'operator@ew.com' },
  { label: 'Engineer', email: 'engineer@ew.com' },
  { label: 'Quality', email: 'quality@ew.com' },
]

export default function LoginPage() {
  const { login } = useAuth()
  const router = useRouter()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSubmitting(true)

    try {
      const role = await login(email, password)
      router.push(ROLE_REDIRECTS[role] ?? '/dashboard')
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Unable to reach server. Check your connection.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/40 px-4">
      <div className="w-full max-w-sm">
        {/* Logo + tagline */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground text-sm font-bold">
              MT
            </span>
            <span className="text-xl font-semibold tracking-tight">
              ModuleTrace
            </span>
          </div>
          <p className="text-sm text-muted-foreground">
            Manufacturing quality traceability platform
          </p>
        </div>

        {/* Card */}
        <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
          <h1 className="text-base font-semibold mb-5">Sign in to your account</h1>

          {error && (
            <div className="mb-4 rounded-md bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label
                htmlFor="email"
                className="block text-sm font-medium text-foreground"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="block w-full rounded-lg border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent disabled:opacity-50"
                disabled={submitting}
              />
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="password"
                className="block text-sm font-medium text-foreground"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="block w-full rounded-lg border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent disabled:opacity-50"
                disabled={submitting}
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {submitting && (
                <svg
                  className="animate-spin h-4 w-4"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v8z"
                  />
                </svg>
              )}
              {submitting ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>

        {/* Demo credential hints */}
        <div className="mt-6 rounded-lg border border-border bg-card/50 p-4">
          <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
            Demo accounts — password: <span className="font-mono">demo1234</span>
          </p>
          <div className="space-y-1">
            {DEMO_HINTS.map(({ label, email: hint }) => (
              <button
                key={label}
                type="button"
                onClick={() => {
                  setEmail(hint)
                  setPassword('demo1234')
                }}
                className="w-full flex items-center justify-between rounded-md px-2 py-1 text-xs hover:bg-muted transition-colors text-left"
              >
                <span className="text-muted-foreground font-medium">{label}</span>
                <span className="font-mono text-foreground/70">{hint}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

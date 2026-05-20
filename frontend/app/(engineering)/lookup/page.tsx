'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'

import { getModule, ApiError } from '@/app/lib/api'
import { useAuth } from '@/app/lib/auth'
import type { ModuleDetailResponse } from '@/app/lib/types'
import {
  BuildContextCard,
  ModuleCard,
  TestHistoryTable,
} from '@/components/module-detail-cards'
import { cn } from '@/lib/utils'

const ALLOWED_ROLES = new Set(['engineer', 'quality', 'admin'] as const)

// ── Skeleton ──────────────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-muted', className)} />
}

function ResultSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {[4, 5].map((rows, i) => (
          <div key={i} className="rounded-xl border border-border bg-card p-5 space-y-3">
            <Skeleton className="h-4 w-24" />
            {[...Array(rows)].map((_, j) => (
              <div key={j} className="space-y-1">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-5 w-40" />
              </div>
            ))}
          </div>
        ))}
      </div>
      <div className="rounded-xl border border-border bg-card p-5 space-y-3">
        <Skeleton className="h-4 w-32" />
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    </div>
  )
}

// ── Empty / not-found states ──────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center gap-4">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl border-2 border-dashed border-border">
        <svg className="h-7 w-7 text-muted-foreground" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 15.803 7.5 7.5 0 0016.803 15.803z" />
        </svg>
      </div>
      <div>
        <p className="text-sm font-medium">No module selected</p>
        <p className="text-sm text-muted-foreground mt-1 max-w-xs">
          Search by PCBA serial or IMEI to see full module genealogy
        </p>
      </div>
    </div>
  )
}

function NotFound({ identifier }: { identifier: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center gap-3">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
        <svg className="h-6 w-6 text-muted-foreground" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
        </svg>
      </div>
      <div>
        <p className="text-sm font-medium">No module found</p>
        <p className="text-sm text-muted-foreground mt-0.5">
          <span className="font-mono">{identifier}</span> is not in the database
        </p>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function LookupPage() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)

  const [inputValue, setInputValue] = useState('EW2025C-000001')
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    if (!loading && user && !ALLOWED_ROLES.has(user.role as 'engineer' | 'quality' | 'admin')) {
      router.replace('/login')
    }
  }, [user, loading, router])

  const { data: module, isFetching, isError, error } = useQuery<ModuleDetailResponse, ApiError>({
    queryKey: ['module', searchTerm],
    queryFn: () => getModule(searchTerm),
    enabled: !!searchTerm,
    retry: (_, err) => !(err instanceof ApiError && err.status === 404),
  })

  function triggerSearch() {
    const t = inputValue.trim()
    if (t) setSearchTerm(t)
  }

  const is404 = isError && error instanceof ApiError && error.status === 404

  if (loading || !user) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="px-4 py-6 max-w-5xl mx-auto space-y-6">
      {/* Search */}
      <div className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && triggerSearch()}
          placeholder="PCBA serial or IMEI — e.g. EW2025C-000001"
          className="flex-1 rounded-lg border border-border bg-background px-4 py-2.5 text-sm font-mono placeholder:text-muted-foreground placeholder:font-sans focus:outline-none focus:ring-2 focus:ring-ring"
          autoComplete="off"
          spellCheck={false}
        />
        <button
          onClick={triggerSearch}
          disabled={isFetching || !inputValue.trim()}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isFetching ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
          ) : (
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 15.803 7.5 7.5 0 0016.803 15.803z" />
            </svg>
          )}
          {isFetching ? 'Searching…' : 'Search'}
        </button>
      </div>

      {!searchTerm && <EmptyState />}
      {searchTerm && isFetching && <ResultSkeleton />}
      {searchTerm && !isFetching && is404 && <NotFound identifier={searchTerm} />}
      {searchTerm && !isFetching && isError && !is404 && (
        <div className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-950/30 dark:border-red-900 px-4 py-3 text-sm text-red-600 dark:text-red-400">
          {error instanceof Error ? error.message : 'An error occurred'}
        </div>
      )}

      {module && !isFetching && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <ModuleCard module={module} />
            <BuildContextCard module={module} />
          </div>
          <TestHistoryTable rows={module.test_history} />
        </div>
      )}
    </div>
  )
}

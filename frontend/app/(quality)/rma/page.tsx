'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError, createRMA, getModule, getRMA, updateRMA } from '@/app/lib/api'
import { useAuth } from '@/app/lib/auth'
import type { ModuleDetailResponse, RMAResponse } from '@/app/lib/types'
import {
  BuildContextCard,
  ModuleCard,
  TestHistoryTable,
} from '@/components/module-detail-cards'
import { cn } from '@/lib/utils'

// ── RMA status pill ───────────────────────────────────────────────────────────

const RMA_STATUS_STYLES: Record<string, string> = {
  open:          'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400',
  investigating: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400',
  closed:        'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400',
}

function RmaStatusPill({ status }: { status: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize',
        RMA_STATUS_STYLES[status] ?? 'bg-muted text-muted-foreground',
      )}
    >
      {status}
    </span>
  )
}

// ── Toast ─────────────────────────────────────────────────────────────────────

interface ToastData {
  kind: 'success' | 'error'
  message: string
}

function Toast({ toast, onDismiss }: { toast: ToastData; onDismiss: () => void }) {
  return (
    <div
      className={cn(
        'fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-lg border-l-4 bg-card px-4 py-3 shadow-lg max-w-sm',
        toast.kind === 'success' ? 'border-l-emerald-500' : 'border-l-red-500',
      )}
    >
      <span className={cn('text-base', toast.kind === 'success' ? 'text-emerald-500' : 'text-red-500')}>
        {toast.kind === 'success' ? '✓' : '✗'}
      </span>
      <p className="text-sm font-medium flex-1">{toast.message}</p>
      <button onClick={onDismiss} className="text-muted-foreground hover:text-foreground ml-2 text-xs">✕</button>
    </div>
  )
}

function useToast() {
  const [toast, setToast] = useState<ToastData | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  function show(data: ToastData) {
    if (timerRef.current) clearTimeout(timerRef.current)
    setToast(data)
    timerRef.current = setTimeout(() => setToast(null), 4000)
  }

  return { toast, show, dismiss: () => setToast(null) }
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-muted', className)} />
}

function PageSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {[0, 1].map((i) => (
          <div key={i} className="rounded-xl border border-border bg-card p-5 space-y-3">
            <Skeleton className="h-4 w-24" />
            {[...Array(4)].map((_, j) => (
              <div key={j} className="space-y-1">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-5 w-36" />
              </div>
            ))}
          </div>
        ))}
      </div>
      <div className="rounded-xl border border-border bg-card p-5 space-y-3">
        <Skeleton className="h-4 w-24" />
        {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
      </div>
      <div className="rounded-xl border border-border bg-card p-5 space-y-3">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-9 w-36" />
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
          <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
        </svg>
      </div>
      <div>
        <p className="text-sm font-medium">No module selected</p>
        <p className="text-sm text-muted-foreground mt-1 max-w-xs">
          Search by PCBA serial or IMEI to look up a returned module
        </p>
      </div>
    </div>
  )
}

function ModuleNotFound({ identifier }: { identifier: string }) {
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

// ── Open RMA form ─────────────────────────────────────────────────────────────

function OpenRmaForm({
  serial,
  onSuccess,
}: {
  serial: string
  onSuccess: () => void
}) {
  const [issue, setIssue] = useState('')
  const { show } = useToast()

  const mutation = useMutation({
    mutationFn: () => createRMA({ module_serial: serial, issue: issue.trim() }),
    onSuccess: () => {
      onSuccess()
    },
    onError: (err) => {
      show({
        kind: 'error',
        message: err instanceof ApiError ? err.message : 'Failed to open RMA',
      })
    },
  })

  return (
    <div className="rounded-xl border border-border bg-card p-5 space-y-4">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Open RMA case
      </h2>
      <p className="text-sm text-muted-foreground">
        No RMA exists for this module. Describe the customer-reported issue to open one.
      </p>
      <textarea
        value={issue}
        onChange={(e) => setIssue(e.target.value)}
        placeholder="Customer-reported issue (e.g. No cellular connection in field after 3 weeks)"
        rows={3}
        className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring placeholder:text-muted-foreground"
      />
      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending || !issue.trim()}
        className="inline-flex items-center gap-2 rounded-lg bg-red-600 hover:bg-red-700 px-4 py-2 text-sm font-semibold text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {mutation.isPending && (
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
        )}
        Open RMA case
      </button>
    </div>
  )
}

// ── Existing RMA panel ────────────────────────────────────────────────────────

const RMA_STATUSES = ['open', 'investigating', 'closed'] as const

function ExistingRmaPanel({
  rma,
  serial,
  showToast,
}: {
  rma: RMAResponse
  serial: string
  showToast: (t: ToastData) => void
}) {
  const queryClient = useQueryClient()
  const [rootCause, setRootCause] = useState(rma.root_cause ?? '')
  const [newStatus, setNewStatus] = useState(rma.status)

  // Sync if RMA data refreshes (e.g. after save)
  useEffect(() => {
    setRootCause(rma.root_cause ?? '')
    setNewStatus(rma.status)
  }, [rma.root_cause, rma.status])

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['rma', serial] })
  }

  const rootCauseMutation = useMutation({
    mutationFn: () => updateRMA(serial, { root_cause: rootCause.trim() || null }),
    onSuccess: () => {
      invalidate()
      showToast({ kind: 'success', message: 'Root cause saved' })
    },
    onError: (err) => {
      showToast({
        kind: 'error',
        message: err instanceof ApiError ? err.message : 'Save failed',
      })
    },
  })

  const statusMutation = useMutation({
    mutationFn: () => updateRMA(serial, { status: newStatus }),
    onSuccess: () => {
      invalidate()
      showToast({ kind: 'success', message: `Status updated to "${newStatus}"` })
    },
    onError: (err) => {
      showToast({
        kind: 'error',
        message: err instanceof ApiError ? err.message : 'Update failed',
      })
    },
  })

  const openedDate = new Date(rma.opened_at).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <div className="rounded-xl border border-border bg-card p-5 space-y-5">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        RMA case
      </h2>

      {/* Status + dates */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div>
          <p className="text-xs text-muted-foreground mb-1">Status</p>
          <RmaStatusPill status={rma.status} />
        </div>
        <div>
          <p className="text-xs text-muted-foreground mb-1">Opened</p>
          <p className="text-sm font-medium">{openedDate}</p>
        </div>
      </div>

      {/* Customer issue */}
      <div>
        <p className="text-xs text-muted-foreground mb-1">Customer-reported issue</p>
        <p className="text-sm bg-muted/50 rounded-lg px-3 py-2.5 leading-relaxed">
          {rma.issue}
        </p>
      </div>

      {/* Divider */}
      <hr className="border-border" />

      {/* Root cause */}
      <div className="space-y-2">
        <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Root cause (FA engineer)
        </label>
        <textarea
          value={rootCause}
          onChange={(e) => setRootCause(e.target.value)}
          placeholder="Describe the root cause identified during failure analysis…"
          rows={3}
          className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring placeholder:text-muted-foreground"
        />
        <button
          onClick={() => rootCauseMutation.mutate()}
          disabled={rootCauseMutation.isPending}
          className="inline-flex items-center gap-2 rounded-lg bg-primary hover:opacity-90 px-4 py-2 text-sm font-semibold text-primary-foreground transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {rootCauseMutation.isPending && (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
          )}
          Save root cause
        </button>
      </div>

      {/* Divider */}
      <hr className="border-border" />

      {/* Status update */}
      <div className="space-y-2">
        <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Update status
        </label>
        <div className="flex gap-2 items-center">
          <select
            value={newStatus}
            onChange={(e) => setNewStatus(e.target.value)}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {RMA_STATUSES.map((s) => (
              <option key={s} value={s} className="capitalize">
                {s}
              </option>
            ))}
          </select>
          <button
            onClick={() => statusMutation.mutate()}
            disabled={statusMutation.isPending || newStatus === rma.status}
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-background hover:bg-muted px-4 py-2 text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {statusMutation.isPending && (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-foreground border-t-transparent" />
            )}
            Update status
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function RmaPage() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const queryClient = useQueryClient()
  const { toast, show: showToast, dismiss } = useToast()

  const [inputValue, setInputValue] = useState('EW2025C-000001')
  const [searchTerm, setSearchTerm] = useState('')

  // Auth guard
  useEffect(() => {
    if (!loading && user && user.role !== 'quality' && user.role !== 'admin') {
      router.replace('/login')
    }
  }, [user, loading, router])

  // Module query — always fetch when a serial is searched
  const moduleQuery = useQuery<ModuleDetailResponse, ApiError>({
    queryKey: ['module', searchTerm],
    queryFn: () => getModule(searchTerm),
    enabled: !!searchTerm,
    retry: (_, err) => !(err instanceof ApiError && err.status === 404),
  })

  // RMA query — run in parallel; 404 = no RMA (not an error we surface as error UI)
  const rmaQuery = useQuery<RMAResponse, ApiError>({
    queryKey: ['rma', searchTerm],
    queryFn: () => getRMA(searchTerm),
    enabled: !!searchTerm && !!moduleQuery.data,
    retry: false,
  })

  function triggerSearch() {
    const t = inputValue.trim()
    if (!t) return
    // Invalidate stale RMA data for this serial before refetching
    queryClient.removeQueries({ queryKey: ['rma', t] })
    setSearchTerm(t)
  }

  function refreshAfterCreate() {
    queryClient.invalidateQueries({ queryKey: ['rma', searchTerm] })
    queryClient.invalidateQueries({ queryKey: ['module', searchTerm] })
  }

  const isSearching = moduleQuery.isFetching
  const moduleNotFound =
    moduleQuery.isError &&
    moduleQuery.error instanceof ApiError &&
    moduleQuery.error.status === 404
  const moduleError =
    moduleQuery.isError && !moduleNotFound

  const module = moduleQuery.data
  const rma = rmaQuery.data
  const rmaNotFound =
    rmaQuery.isError &&
    rmaQuery.error instanceof ApiError &&
    rmaQuery.error.status === 404
  // Still loading: module fetched but RMA query hasn't settled yet
  const rmaLoading = rmaQuery.isFetching

  if (loading || !user) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="px-4 py-6 max-w-5xl mx-auto space-y-6">
      {/* ── Search bar ──────────────────────────────────────────────────────── */}
      <div className="flex gap-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && triggerSearch()}
          placeholder="PCBA serial or IMEI"
          className="flex-1 rounded-lg border border-border bg-background px-4 py-2.5 text-sm font-mono placeholder:text-muted-foreground placeholder:font-sans focus:outline-none focus:ring-2 focus:ring-ring"
          autoComplete="off"
          spellCheck={false}
        />
        <button
          onClick={triggerSearch}
          disabled={isSearching || !inputValue.trim()}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSearching ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
          ) : (
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 15.803 7.5 7.5 0 0016.803 15.803z" />
            </svg>
          )}
          {isSearching ? 'Searching…' : 'Search'}
        </button>
      </div>

      {/* ── Body ────────────────────────────────────────────────────────────── */}
      {!searchTerm && <EmptyState />}

      {searchTerm && isSearching && <PageSkeleton />}

      {searchTerm && !isSearching && moduleNotFound && (
        <ModuleNotFound identifier={searchTerm} />
      )}

      {searchTerm && !isSearching && moduleError && (
        <div className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-950/30 dark:border-red-900 px-4 py-3 text-sm text-red-600 dark:text-red-400">
          {moduleQuery.error instanceof Error
            ? moduleQuery.error.message
            : 'An error occurred'}
        </div>
      )}

      {module && !isSearching && (
        <div className="space-y-4">
          {/* Module + build context cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <ModuleCard module={module} />
            <BuildContextCard module={module} />
          </div>

          {/* Test history — compact (no measurements column) */}
          <TestHistoryTable rows={module.test_history} compact />

          {/* RMA section */}
          {rmaLoading && (
            <div className="rounded-xl border border-border bg-card p-5 space-y-3">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-9 w-40" />
            </div>
          )}

          {!rmaLoading && rmaNotFound && (
            <OpenRmaForm
              serial={searchTerm}
              onSuccess={refreshAfterCreate}
            />
          )}

          {!rmaLoading && rma && (
            <ExistingRmaPanel
              rma={rma}
              serial={searchTerm}
              showToast={showToast}
            />
          )}
        </div>
      )}

      {/* ── Toast ───────────────────────────────────────────────────────────── */}
      {toast && <Toast toast={toast} onDismiss={dismiss} />}
    </div>
  )
}

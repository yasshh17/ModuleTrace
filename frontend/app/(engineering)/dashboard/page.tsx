'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { getFailures, getYield } from '@/app/lib/api'
import { useAuth } from '@/app/lib/auth'
import type { ParetoItem, YieldItem } from '@/app/lib/types'
import { cn } from '@/lib/utils'
import { useState } from 'react'

// ── Types ─────────────────────────────────────────────────────────────────────

type Days = 7 | 14 | 30 | 730

const DAYS_OPTIONS: { label: string; value: Days }[] = [
  { label: 'Last 7 days', value: 7 },
  { label: 'Last 14 days', value: 14 },
  { label: 'Last 30 days', value: 30 },
  { label: 'All data (2 yr)', value: 730 },
]

// ── Color helpers ─────────────────────────────────────────────────────────────

function fpyColor(pct: number): string {
  if (pct >= 95) return '#10b981' // emerald-500
  if (pct >= 90) return '#f59e0b' // amber-500
  return '#ef4444'                // red-500
}

function fpyTextClass(pct: number): string {
  if (pct >= 95) return 'text-emerald-600 dark:text-emerald-400'
  if (pct >= 90) return 'text-amber-600 dark:text-amber-400'
  return 'text-red-600 dark:text-red-400'
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse rounded-md bg-muted', className)} />
}

// ── Metric card ───────────────────────────────────────────────────────────────

function MetricCard({
  label,
  value,
  valueClass,
  loading,
}: {
  label: string
  value: React.ReactNode
  valueClass?: string
  loading?: boolean
}) {
  return (
    <div className="rounded-xl border border-border bg-card px-5 py-4 flex flex-col gap-1">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      {loading ? (
        <Skeleton className="h-8 w-24 mt-1" />
      ) : (
        <p className={cn('text-3xl font-bold tabular-nums', valueClass)}>
          {value}
        </p>
      )}
    </div>
  )
}

// ── Recharts custom tooltip ───────────────────────────────────────────────────

function YieldTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: { payload: YieldItem }[]
}) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  return (
    <div className="rounded-lg border border-border bg-card shadow-lg px-3 py-2 text-xs space-y-1">
      <p className="font-semibold">{row.product_name}</p>
      <p>FPY: <span className="font-mono">{row.fpy_pct.toFixed(1)}%</span></p>
      <p>Tested: <span className="font-mono">{row.total_tested}</span></p>
      <p>Passed: <span className="font-mono">{row.total_passed}</span></p>
    </div>
  )
}

// ── FPY bar chart ─────────────────────────────────────────────────────────────

function FpyChart({ rows, loading }: { rows: YieldItem[]; loading: boolean }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 flex flex-col gap-4">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        First-pass yield by product
      </h2>
      {loading ? (
        <div className="flex gap-4 items-end h-48 px-2">
          {[68, 82, 55, 72].map((h, i) => (
            <div
              key={i}
              className="flex-1 rounded-sm animate-pulse bg-muted"
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <div className="flex items-center justify-center h-48 text-sm text-muted-foreground">
          No data for this period
        </div>
      ) : (
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={rows}
              margin={{ top: 4, right: 4, left: -16, bottom: 0 }}
            >
              <XAxis
                dataKey="sku"
                tick={{ fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={[80, 100]}
                ticks={[80, 85, 90, 95, 100]}
                tickFormatter={(v) => `${v}%`}
                tick={{ fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={40}
              />
              <Tooltip content={<YieldTooltip />} cursor={{ fill: 'transparent' }} />
              <Bar dataKey="fpy_pct" radius={[4, 4, 0, 0]}>
                {rows.map((row, i) => (
                  <Cell key={i} fill={fpyColor(row.fpy_pct)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

// ── Pareto chart (div-based, horizontal) ──────────────────────────────────────

function ParetoChart({
  rows,
  loading,
}: {
  rows: ParetoItem[]
  loading: boolean
}) {
  const barColor = (i: number) => {
    if (i === 0) return 'bg-red-500'
    if (i === 1) return 'bg-amber-500'
    return 'bg-zinc-400'
  }

  return (
    <div className="rounded-xl border border-border bg-card p-5 flex flex-col gap-4">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Failure mode pareto
      </h2>
      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex gap-3 items-center">
              <Skeleton className="h-3 w-32 shrink-0" />
              <Skeleton className="h-5 flex-1" />
              <Skeleton className="h-3 w-8" />
            </div>
          ))}
        </div>
      ) : rows.length === 0 ? (
        <div className="flex items-center justify-center h-48 text-sm text-muted-foreground">
          No failures in this period
        </div>
      ) : (
        <div className="space-y-3">
          {rows.map((row, i) => (
            <div key={row.failure_mode} className="flex items-center gap-3">
              <span className="font-mono text-[11px] text-muted-foreground w-36 shrink-0 truncate">
                {row.failure_mode}
              </span>
              <div className="flex-1 h-5 bg-muted rounded-sm overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-sm transition-all',
                    barColor(i),
                  )}
                  style={{ width: `${Math.max(row.pct, 1)}%` }}
                />
              </div>
              <span className="text-xs font-mono tabular-nums w-8 text-right shrink-0">
                {row.count}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Recent failures table (static demo data) ──────────────────────────────────

const DEMO_FAILURES = [
  {
    serial: 'EW2025C-000041',
    product: 'Eagle 5G Module M100',
    failure_mode: 'GPS_FIX_TIMEOUT',
    operator: 'Maria Santos',
    time: '09:47',
  },
  {
    serial: 'EW2025C-000038',
    product: 'Eagle 5G Module M100',
    failure_mode: 'RF_TX_POWER_LOW',
    operator: 'James Nguyen',
    time: '09:12',
  },
  {
    serial: 'EW2025B-004719',
    product: 'Eagle LTE Advanced A200',
    failure_mode: 'CURRENT_DRAW_HIGH',
    operator: 'Priya Sharma',
    time: '08:53',
  },
  {
    serial: 'EW2025C-000029',
    product: 'Eagle 5G Module M100',
    failure_mode: 'GPS_FIX_TIMEOUT',
    operator: 'Carlos Vega',
    time: '08:21',
  },
  {
    serial: 'EW2025A-002103',
    product: 'Eagle CAT-1 S50',
    failure_mode: 'FLASH_VERIFY_FAIL',
    operator: 'Maria Santos',
    time: '07:44',
  },
]

function RecentFailuresTable() {
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="px-5 py-4 border-b border-border">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Recent failures
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/40">
              {['Serial', 'Product', 'Failure mode', 'Operator', 'Time'].map(
                (h) => (
                  <th
                    key={h}
                    className="px-4 py-2.5 text-left text-xs font-semibold text-muted-foreground whitespace-nowrap"
                  >
                    {h}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {DEMO_FAILURES.map((row) => (
              <tr
                key={row.serial}
                className="hover:bg-muted/30 transition-colors"
              >
                <td className="px-4 py-3 font-mono text-xs">{row.serial}</td>
                <td className="px-4 py-3 text-sm">{row.product}</td>
                <td className="px-4 py-3 font-mono text-xs text-red-600 dark:text-red-400">
                  {row.failure_mode}
                </td>
                <td className="px-4 py-3 text-sm text-muted-foreground">
                  {row.operator}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                  {row.time}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { user, loading } = useAuth()
  const router = useRouter()
  const [days, setDays] = useState<Days>(730)

  // Auth guard
  useEffect(() => {
    if (!loading && user && user.role !== 'engineer' && user.role !== 'admin') {
      router.replace('/login')
    }
  }, [user, loading, router])

  const { data: yieldData, isFetching: yieldFetching } = useQuery({
    queryKey: ['yield', days],
    queryFn: () => getYield(days),
    enabled: !!user,
  })

  const { data: failureData, isFetching: failureFetching } = useQuery({
    queryKey: ['failures', days],
    queryFn: () => getFailures(days),
    enabled: !!user,
  })

  // Derived metrics
  const yieldRows: YieldItem[] = yieldData?.rows ?? []
  const failureRows: ParetoItem[] = failureData?.rows ?? []

  const totalTested = yieldRows.reduce((s, r) => s + r.total_tested, 0)
  const totalPassed = yieldRows.reduce((s, r) => s + r.total_passed, 0)
  const totalFailed = totalTested - totalPassed
  const overallFpy =
    totalTested > 0 ? (totalPassed / totalTested) * 100 : null

  const anyLoading = yieldFetching || failureFetching

  if (loading || !user) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="px-4 py-6 max-w-6xl mx-auto space-y-6">

      {/* ── Header row ────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-lg font-semibold">Yield dashboard</h1>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value) as Days)}
          className="rounded-lg border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        >
          {DAYS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {/* ── Metric cards ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <MetricCard
          label="Overall FPY"
          loading={yieldFetching}
          value={overallFpy != null ? `${overallFpy.toFixed(1)}%` : '—'}
          valueClass={overallFpy != null ? fpyTextClass(overallFpy) : undefined}
        />
        <MetricCard
          label="Modules tested"
          loading={yieldFetching}
          value={totalTested.toLocaleString()}
        />
        <MetricCard
          label="Failed units"
          loading={yieldFetching}
          value={totalFailed.toLocaleString()}
          valueClass={totalFailed > 0 ? 'text-red-600 dark:text-red-400' : undefined}
        />
        <MetricCard
          label="Open RMAs"
          loading={false}
          value={2}
          valueClass="text-amber-600 dark:text-amber-400"
        />
      </div>

      {/* ── Charts row ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <FpyChart rows={yieldRows} loading={yieldFetching} />
        <ParetoChart rows={failureRows} loading={failureFetching} />
      </div>

      {/* ── Recent failures ──────────────────────────────────────────────── */}
      <RecentFailuresTable />

    </div>
  )
}

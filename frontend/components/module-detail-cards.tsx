import type { ModuleDetailResponse, TestRunSummary } from '@/app/lib/types'
import { cn } from '@/lib/utils'

// ── Date helpers ──────────────────────────────────────────────────────────────

export function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

// ── Status pill (module status) ───────────────────────────────────────────────

const MODULE_STATUS_STYLES: Record<string, string> = {
  pass:        'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400',
  fail:        'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
  rma:         'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400',
  in_progress: 'bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400',
  shipped:     'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400',
}

export function ModuleStatusPill({ status }: { status: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize',
        MODULE_STATUS_STYLES[status] ?? 'bg-muted text-muted-foreground',
      )}
    >
      {status.replace(/_/g, ' ')}
    </span>
  )
}

// ── Result pill (test run result) ─────────────────────────────────────────────

const RESULT_STYLES: Record<string, string> = {
  PASS:   'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400',
  FAIL:   'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
  RETEST: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400',
}

export function ResultPill({ result }: { result: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold',
        RESULT_STYLES[result] ?? 'bg-muted text-muted-foreground',
      )}
    >
      {result}
    </span>
  )
}

// ── Measurements cell ─────────────────────────────────────────────────────────

export function MeasurementsCell({
  data,
}: {
  data: Record<string, unknown> | null
}) {
  if (!data || Object.keys(data).length === 0) {
    return <span className="text-muted-foreground">—</span>
  }
  return (
    <div className="space-y-0.5">
      {Object.entries(data).map(([k, v]) => (
        <div key={k} className="font-mono text-[11px] leading-tight">
          <span className="text-muted-foreground">{k}:</span>{' '}
          <span>{String(v)}</span>
        </div>
      ))}
    </div>
  )
}

// ── Table primitives ──────────────────────────────────────────────────────────

export function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-4 py-2.5 text-left text-xs font-semibold text-muted-foreground whitespace-nowrap">
      {children}
    </th>
  )
}

export function Td({
  children,
  mono,
}: {
  children: React.ReactNode
  mono?: boolean
}) {
  return (
    <td className={cn('px-4 py-3 align-top text-sm', mono && 'font-mono text-xs')}>
      {children}
    </td>
  )
}

// ── Info row ──────────────────────────────────────────────────────────────────

export function InfoRow({
  label,
  value,
  mono = false,
}: {
  label: string
  value: React.ReactNode
  mono?: boolean
}) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground mb-0.5">{label}</dt>
      <dd className={cn('text-sm font-medium', mono && 'font-mono')}>{value}</dd>
    </div>
  )
}

// ── Module card ───────────────────────────────────────────────────────────────

export function ModuleCard({ module }: { module: ModuleDetailResponse }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-4">
        Module
      </h2>
      <dl className="space-y-3">
        <InfoRow label="PCBA serial" value={module.pcba_serial} mono />
        <InfoRow
          label="IMEI"
          value={
            module.imei ?? (
              <span className="text-muted-foreground">not assigned</span>
            )
          }
          mono
        />
        <InfoRow label="Status" value={<ModuleStatusPill status={module.status} />} />
        <InfoRow label="Produced" value={formatDate(module.produced_at)} />
        {module.shipped_at && (
          <InfoRow label="Shipped" value={formatDate(module.shipped_at)} />
        )}
      </dl>
    </div>
  )
}

// ── Build context card ────────────────────────────────────────────────────────

export function BuildContextCard({ module }: { module: ModuleDetailResponse }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-4">
        Build context
      </h2>
      <dl className="space-y-3">
        <InfoRow label="Work order" value={module.wo_number} mono />
        <InfoRow label="Product" value={module.product_name} />
        <InfoRow label="SKU" value={module.sku} mono />
        <InfoRow
          label="HW revision"
          value={
            module.hw_revision ?? (
              <span className="text-muted-foreground">—</span>
            )
          }
        />
        <InfoRow
          label="FW version"
          value={
            module.fw_version ?? (
              <span className="text-muted-foreground">—</span>
            )
          }
          mono
        />
      </dl>
    </div>
  )
}

// ── Test history table ────────────────────────────────────────────────────────

export function TestHistoryTable({
  rows,
  compact = false,
}: {
  rows: TestRunSummary[]
  compact?: boolean
}) {
  const sorted = [...rows].sort(
    (a, b) => new Date(a.tested_at).getTime() - new Date(b.tested_at).getTime(),
  )

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="px-5 py-4 border-b border-border flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Test history
        </h2>
        <span className="text-xs text-muted-foreground">{rows.length} runs</span>
      </div>

      {sorted.length === 0 ? (
        <div className="px-5 py-8 text-center text-sm text-muted-foreground">
          No test runs recorded.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40">
                <Th>Station</Th>
                <Th>Result</Th>
                <Th>Failure mode</Th>
                {!compact && <Th>Measurements</Th>}
                <Th>Operator</Th>
                <Th>Time</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {sorted.map((run, idx) => (
                <tr
                  key={run.id ?? idx}
                  className={cn(
                    'transition-colors',
                    run.result === 'FAIL' && 'bg-red-50/50 dark:bg-red-950/10',
                    run.result === 'RETEST' &&
                      'bg-amber-50/50 dark:bg-amber-950/10',
                  )}
                >
                  <Td mono>{run.station}</Td>
                  <Td>
                    <ResultPill result={run.result} />
                  </Td>
                  <Td>
                    {run.failure_mode ? (
                      <span className="font-mono text-xs text-red-600 dark:text-red-400">
                        {run.failure_mode}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </Td>
                  {!compact && (
                    <Td>
                      <MeasurementsCell data={run.measurements} />
                    </Td>
                  )}
                  <Td>
                    {run.operator_name ?? (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </Td>
                  <Td mono>{formatTime(run.tested_at)}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

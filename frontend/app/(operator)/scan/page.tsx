'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'

import { postTestRun } from '@/app/lib/api'
import { useAuth } from '@/app/lib/auth'
import { ApiError } from '@/app/lib/api'
import { cn } from '@/lib/utils'

// ── Types ─────────────────────────────────────────────────────────────────────

type Station = 'FCT' | 'AOI' | 'RF_TX' | 'RF_RX' | 'GPS' | 'FLASH'
type Phase = 'result' | 'fail_mode' | 'submitted'

const STATIONS: { id: Station; label: string }[] = [
  { id: 'FCT',   label: 'FCT'   },
  { id: 'AOI',   label: 'AOI'   },
  { id: 'RF_TX', label: 'RF TX' },
  { id: 'RF_RX', label: 'RF RX' },
  { id: 'GPS',   label: 'GPS'   },
  { id: 'FLASH', label: 'Flash' },
]

const FAILURE_MODES = [
  'GPS_FIX_TIMEOUT',
  'RF_TX_POWER_LOW',
  'CURRENT_DRAW_HIGH',
  'AOI_SOLDER_BRIDGE',
  'FLASH_VERIFY_FAIL',
]

// ── Demo serial generation ────────────────────────────────────────────────────

const DEMO_START = 416
const DEMO_PREFIX = 'EW2025C'
const DEMO_PRODUCT = 'Eagle 5G Module M100'
const DEMO_WO = 'WO-2025-0047'

function makeSerial(n: number) {
  return `${DEMO_PREFIX}-${String(n).padStart(6, '0')}`
}

// ── Shift summary (static demo) ───────────────────────────────────────────────

const SHIFT_START_PASSED = 34
const SHIFT_START_FAILED = 3

// ── Step indicator ────────────────────────────────────────────────────────────

function StepDot({
  n,
  label,
  state,
}: {
  n: number
  label: string
  state: 'done' | 'current' | 'pending'
}) {
  return (
    <div className="flex flex-col items-center gap-1 flex-1">
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold border-2 transition-colors',
          state === 'done' &&
            'bg-emerald-500 border-emerald-500 text-white',
          state === 'current' &&
            'bg-primary border-primary text-primary-foreground',
          state === 'pending' &&
            'bg-background border-border text-muted-foreground',
        )}
      >
        {state === 'done' ? (
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            strokeWidth={2.5}
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        ) : (
          n
        )}
      </div>
      <span
        className={cn(
          'text-xs font-medium',
          state === 'current' ? 'text-foreground' : 'text-muted-foreground',
        )}
      >
        {label}
      </span>
    </div>
  )
}

function StepIndicator({ phase }: { phase: Phase }) {
  const step1: 'done' | 'current' | 'pending' = 'done'
  const step2: 'done' | 'current' | 'pending' =
    phase === 'submitted' ? 'done' : 'current'
  const step3: 'done' | 'current' | 'pending' =
    phase === 'submitted' ? 'current' : 'pending'

  return (
    <div className="flex items-start gap-0 w-full">
      <StepDot n={1} label="Station" state={step1} />
      {/* connector */}
      <div
        className={cn(
          'flex-1 h-0.5 mt-4 transition-colors',
          step2 === 'done' || step2 === 'current'
            ? 'bg-primary'
            : 'bg-border',
        )}
      />
      <StepDot n={2} label="Log result" state={step2} />
      {/* connector */}
      <div
        className={cn(
          'flex-1 h-0.5 mt-4 transition-colors',
          step3 === 'current' ? 'bg-primary' : 'bg-border',
        )}
      />
      <StepDot n={3} label="Next module" state={step3} />
    </div>
  )
}

// ── Toast ─────────────────────────────────────────────────────────────────────

interface ToastData {
  kind: 'pass' | 'fail'
  message: string
}

function Toast({ toast }: { toast: ToastData }) {
  return (
    <div
      className={cn(
        'rounded-lg border-l-4 bg-card px-4 py-3 shadow-sm flex items-center gap-3',
        toast.kind === 'pass'
          ? 'border-l-emerald-500'
          : 'border-l-red-500',
      )}
    >
      <span
        className={cn(
          'text-lg',
          toast.kind === 'pass' ? 'text-emerald-500' : 'text-red-500',
        )}
      >
        {toast.kind === 'pass' ? '✓' : '✗'}
      </span>
      <span className="text-sm font-medium">{toast.message}</span>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ScanPage() {
  const { user, loading } = useAuth()
  const router = useRouter()

  // ── Auth guard ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!loading && user && user.role !== 'operator' && user.role !== 'engineer') {
      router.replace('/login')
    }
  }, [user, loading, router])

  // ── State ─────────────────────────────────────────────────────────────────
  const [station, setStation] = useState<Station>('FCT')
  const [phase, setPhase] = useState<Phase>('result')
  const [serialCounter, setSerialCounter] = useState(DEMO_START)
  const [failureMode, setFailureMode] = useState(FAILURE_MODES[0])
  const [submitting, setSubmitting] = useState(false)
  const [toast, setToast] = useState<ToastData | null>(null)
  const [apiError, setApiError] = useState<string | null>(null)
  const [shiftPassed, setShiftPassed] = useState(SHIFT_START_PASSED)
  const [shiftFailed, setShiftFailed] = useState(SHIFT_START_FAILED)

  const currentSerial = makeSerial(serialCounter)

  // ── Handlers ──────────────────────────────────────────────────────────────

  async function submitResult(result: 'PASS' | 'FAIL', fm?: string) {
    setSubmitting(true)
    setApiError(null)
    try {
      await postTestRun({
        module_serial: currentSerial,
        station,
        result,
        failure_mode: fm ?? null,
      })

      const msg =
        result === 'PASS'
          ? `${station} Pass — ${currentSerial} logged`
          : `${station} Fail — ${fm} recorded`

      setToast({ kind: result === 'PASS' ? 'pass' : 'fail', message: msg })
      setPhase('submitted')

      if (result === 'PASS') {
        setShiftPassed((p) => p + 1)
      } else {
        setShiftFailed((f) => f + 1)
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setApiError(err.message)
      } else {
        setApiError('Network error — check connection')
      }
    } finally {
      setSubmitting(false)
    }
  }

  function handlePass() {
    submitResult('PASS')
  }

  function handleFailClick() {
    setPhase('fail_mode')
  }

  function handleSubmitFail() {
    submitResult('FAIL', failureMode)
  }

  function handleNextModule() {
    setSerialCounter((n) => n + 1)
    setPhase('result')
    setToast(null)
    setApiError(null)
    setFailureMode(FAILURE_MODES[0])
  }

  // ── Render guards ─────────────────────────────────────────────────────────
  if (loading || !user) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }

  const shiftTotal = shiftPassed + shiftFailed

  return (
    <div className="py-6 px-4 flex justify-center">
      <div className="w-full max-w-[480px] space-y-5">

        {/* ── Step indicator ──────────────────────────────────────────────── */}
        <StepIndicator phase={phase} />

        {/* ── Station selector ─────────────────────────────────────────────── */}
        <section className="rounded-xl border border-border bg-card p-4 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Test station
          </p>
          <div className="grid grid-cols-3 gap-2">
            {STATIONS.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setStation(id)}
                disabled={phase === 'submitted'}
                className={cn(
                  'h-14 rounded-lg text-sm font-semibold border-2 transition-all active:scale-95',
                  station === id
                    ? 'bg-primary border-primary text-primary-foreground shadow-sm'
                    : 'bg-background border-border text-foreground hover:border-primary/50 hover:bg-primary/5',
                  phase === 'submitted' && 'opacity-50 cursor-not-allowed',
                )}
              >
                {label}
              </button>
            ))}
          </div>
        </section>

        {/* ── Module serial card ───────────────────────────────────────────── */}
        <section className="rounded-xl border border-border bg-card px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
            Module
          </p>
          <p className="font-mono text-2xl font-bold tracking-tight leading-none">
            {currentSerial}
          </p>
          <p className="text-xs text-muted-foreground mt-1.5">
            {DEMO_PRODUCT} · {DEMO_WO}
          </p>
        </section>

        {/* ── API error ───────────────────────────────────────────────────── */}
        {apiError && (
          <div className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-950/30 dark:border-red-900 px-4 py-3 text-sm text-red-600 dark:text-red-400">
            {apiError}
          </div>
        )}

        {/* ── Result buttons / fail mode / toast ──────────────────────────── */}
        {phase === 'result' && (
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={handlePass}
              disabled={submitting}
              className="h-20 rounded-xl bg-emerald-500 hover:bg-emerald-600 active:bg-emerald-700 text-white font-bold text-xl transition-colors active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm flex items-center justify-center gap-2"
            >
              <span className="text-2xl">✓</span>
              Pass
            </button>
            <button
              onClick={handleFailClick}
              disabled={submitting}
              className="h-20 rounded-xl bg-red-500 hover:bg-red-600 active:bg-red-700 text-white font-bold text-xl transition-colors active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm flex items-center justify-center gap-2"
            >
              <span className="text-2xl">✗</span>
              Fail
            </button>
          </div>
        )}

        {phase === 'fail_mode' && (
          <section className="rounded-xl border border-red-200 dark:border-red-900 bg-card p-4 space-y-3">
            <p className="text-sm font-semibold text-red-600 dark:text-red-400">
              Select failure mode
            </p>
            <select
              value={failureMode}
              onChange={(e) => setFailureMode(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {FAILURE_MODES.map((fm) => (
                <option key={fm} value={fm}>
                  {fm}
                </option>
              ))}
            </select>
            <button
              onClick={handleSubmitFail}
              disabled={submitting}
              className="w-full h-14 rounded-xl bg-red-500 hover:bg-red-600 active:bg-red-700 text-white font-bold text-base transition-colors active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm flex items-center justify-center gap-2"
            >
              {submitting ? (
                <span className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                '✗ Submit fail'
              )}
            </button>
          </section>
        )}

        {phase === 'submitted' && (
          <div className="space-y-3">
            {toast && <Toast toast={toast} />}
            <button
              onClick={handleNextModule}
              className="w-full h-14 rounded-xl bg-primary hover:bg-primary/90 active:scale-95 text-primary-foreground font-semibold text-base transition-all shadow-sm flex items-center justify-center gap-2"
            >
              Next module
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5-5 5M6 12h12" />
              </svg>
            </button>
          </div>
        )}

        {/* ── Shift summary ─────────────────────────────────────────────────── */}
        <section className="rounded-xl border border-border bg-card px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
            Today&apos;s shift
          </p>
          <div className="grid grid-cols-4 gap-2 text-center">
            <div>
              <p className="text-[11px] text-muted-foreground leading-tight mb-1">Operator</p>
              <p className="text-xs font-semibold truncate">{user.full_name.split(' ')[0]}</p>
            </div>
            <div>
              <p className="text-[11px] text-muted-foreground leading-tight mb-1">Scanned</p>
              <p className="text-xl font-bold tabular-nums">{shiftTotal}</p>
            </div>
            <div>
              <p className="text-[11px] text-muted-foreground leading-tight mb-1">Passed</p>
              <p className="text-xl font-bold tabular-nums text-emerald-600 dark:text-emerald-400">
                {shiftPassed}
              </p>
            </div>
            <div>
              <p className="text-[11px] text-muted-foreground leading-tight mb-1">Failed</p>
              <p className="text-xl font-bold tabular-nums text-red-500">
                {shiftFailed}
              </p>
            </div>
          </div>
        </section>

      </div>
    </div>
  )
}

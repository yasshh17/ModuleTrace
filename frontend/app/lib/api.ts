import type {
  ModuleDetailResponse,
  ModuleListParams,
  ModuleListResponse,
  ParetoResponse,
  RMACreate,
  RMAResponse,
  RMAUpdate,
  TestRunCreate,
  TestRunResponse,
  TokenResponse,
  UserResponse,
  YieldResponse,
} from './types'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function apiClient<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token =
    typeof window !== 'undefined' ? localStorage.getItem('mt_token') : null

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  if (!res.ok) {
    let message = `HTTP ${res.status}`
    try {
      const body = await res.json()
      message = body?.detail ?? body?.message ?? message
    } catch {
      // non-JSON error body — keep default message
    }
    throw new ApiError(res.status, message)
  }

  return res.json() as Promise<T>
}

export { ApiError }

// ── Auth ─────────────────────────────────────────────────────────────────────

export function login(email: string, password: string): Promise<TokenResponse> {
  return apiClient<TokenResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function getMe(): Promise<UserResponse> {
  return apiClient<UserResponse>('/api/v1/auth/me')
}

// ── Modules ───────────────────────────────────────────────────────────────────

export function getModule(identifier: string): Promise<ModuleDetailResponse> {
  return apiClient<ModuleDetailResponse>(
    `/api/v1/modules/${encodeURIComponent(identifier)}`,
  )
}

export function listModules(params: ModuleListParams = {}): Promise<ModuleListResponse> {
  const qs = new URLSearchParams()
  if (params.status) qs.set('status', params.status)
  if (params.product_sku) qs.set('product_sku', params.product_sku)
  if (params.page != null) qs.set('page', String(params.page))
  if (params.size != null) qs.set('size', String(params.size))
  const query = qs.toString() ? `?${qs.toString()}` : ''
  return apiClient<ModuleListResponse>(`/api/v1/modules${query}`)
}

// ── Test runs ─────────────────────────────────────────────────────────────────

export function postTestRun(data: TestRunCreate): Promise<TestRunResponse> {
  return apiClient<TestRunResponse>('/api/v1/test-runs/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export function getYield(days: number = 7): Promise<YieldResponse> {
  return apiClient<YieldResponse>(`/api/v1/analytics/yield?days=${days}`)
}

export function getFailures(days: number = 7): Promise<ParetoResponse> {
  return apiClient<ParetoResponse>(`/api/v1/analytics/failures?days=${days}`)
}

// ── RMA ───────────────────────────────────────────────────────────────────────

export function getRMA(serial: string): Promise<RMAResponse> {
  return apiClient<RMAResponse>(`/api/v1/rma/${encodeURIComponent(serial)}`)
}

export function createRMA(data: RMACreate): Promise<RMAResponse> {
  return apiClient<RMAResponse>('/api/v1/rma/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateRMA(serial: string, data: RMAUpdate): Promise<RMAResponse> {
  return apiClient<RMAResponse>(`/api/v1/rma/${encodeURIComponent(serial)}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

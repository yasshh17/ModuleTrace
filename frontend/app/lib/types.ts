export type Role = 'operator' | 'engineer' | 'quality' | 'admin'

export interface UserResponse {
  id: number
  email: string
  full_name: string
  role: Role
}

export interface TokenResponse {
  access_token: string
  token_type: string
  role: Role
}

export interface ModuleListItem {
  id: number
  pcba_serial: string
  imei: string | null
  status: string
  produced_at: string
  sku: string
  wo_number: string
}

export interface ModuleListResponse {
  items: ModuleListItem[]
  total: number
  page: number
  size: number
}

export interface TestRunSummary {
  id: number
  station: string
  result: string
  failure_mode: string | null
  measurements: Record<string, unknown> | null
  tested_at: string
  operator_name: string | null
}

export interface ModuleDetailResponse {
  id: number
  pcba_serial: string
  imei: string | null
  status: string
  produced_at: string
  shipped_at: string | null
  sku: string
  product_name: string
  hw_revision?: string
  fw_version?: string | null
  wo_number: string
  test_history: TestRunSummary[]
}

export interface YieldItem {
  sku: string
  product_name: string
  total_tested: number
  total_passed: number
  fpy_pct: number
}

export interface YieldResponse {
  from_date: string
  to_date: string
  rows: YieldItem[]
}

export interface ParetoItem {
  failure_mode: string
  count: number
  pct: number
}

export interface ParetoResponse {
  from_date: string
  to_date: string
  rows: ParetoItem[]
}

export interface RMAResponse {
  id: number
  module_serial: string
  issue: string
  root_cause: string | null
  status: string
  opened_at: string
}

export interface TestRunResponse {
  id: number
  module_id: number
  station: string
  result: string
  failure_mode: string | null
  measurements: Record<string, unknown> | null
  tested_at: string
  operator_id: number | null
}

// Request payload shapes
export interface TestRunCreate {
  module_serial: string
  station: string
  result: string
  failure_mode?: string | null
  measurements?: Record<string, unknown> | null
  operator_id?: number | null
}

export interface RMACreate {
  module_serial: string
  issue: string
}

export interface RMAUpdate {
  root_cause?: string | null
  status?: string | null
}

export interface ModuleListParams {
  status?: string
  product_sku?: string
  page?: number
  size?: number
}

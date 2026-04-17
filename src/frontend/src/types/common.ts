// 後端錯誤回應採 RFC 7807 Problem Details 格式（Content-Type: application/problem+json），
// 成功回應則直接為 DRF 原生序列化資料，不額外包裝信封。
// 參考：apps/core/exceptions.py 與 docs/adr/ADR-001-drf-native-response-format.md。
export interface ProblemDetails {
  type: string
  title: string
  status: number
  detail?: string
  errors?: FieldError[]
}

export interface FieldError {
  field: string
  message: string
}

// DRF 分頁使用 PageNumberPagination，回應格式為 { count, next, previous, results }。
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface PaginationQuery {
  page?: number
  page_size?: number
  search?: string
}

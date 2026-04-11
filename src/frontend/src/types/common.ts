// ApiResponse 是後端所有 API 回應的統一信封格式。
// success=true 時 data 有值、errors 為 null；
// success=false 時 data 為 null，errors 存放欄位層級的驗證錯誤，message 存放全域錯誤訊息。
// 兩者不會同時有值，呼叫端應先判斷 success 再存取對應欄位。
export interface ApiResponse<T = unknown> {
  success: boolean
  data: T | null
  message: string | null
  errors: FieldError[] | null
  meta: PaginationMeta | null
}

export interface FieldError {
  field: string
  message: string
}

export interface PaginationMeta {
  total: number
  page: number
  limit: number
  totalPages: number
}

export interface PaginationQuery {
  page?: number
  limit?: number
  search?: string
}

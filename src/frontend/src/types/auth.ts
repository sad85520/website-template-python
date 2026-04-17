export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  display_name: string
}

export interface LoginResponse {
  access_token: string
  // expires_in 單位為秒，對應後端 SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]，
  // 可用於前端主動在 token 到期前排程 silent refresh（若有需要），目前版本由 interceptor 被動觸發。
  expires_in: number
}

export interface UserDto {
  id: string
  email: string
  display_name: string
  role: 'admin' | 'user'
  created_at: string
}

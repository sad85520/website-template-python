export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  displayName: string
}

export interface LoginResponse {
  accessToken: string
  // expiresIn 單位為秒，對應後端 SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]，
  // 可用於前端主動在 token 到期前排程 silent refresh（若有需要），目前版本由 interceptor 被動觸發。
  expiresIn: number
}

export interface UserDto {
  id: string
  email: string
  displayName: string
  role: 'admin' | 'user'
  createdAt: string
}

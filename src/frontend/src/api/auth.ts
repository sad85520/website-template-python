import apiClient from './client'
import type { ApiResponse, LoginRequest, LoginResponse, RegisterRequest, UserDto } from '@/types'

export const authApi = {
  login(data: LoginRequest) {
    return apiClient.post<ApiResponse<LoginResponse>>('/v1/auth/login', data)
  },

  register(data: RegisterRequest) {
    return apiClient.post<ApiResponse<UserDto>>('/v1/auth/register', data)
  },

  refresh() {
    // refresh token 由瀏覽器自動帶入 HttpOnly cookie（apiClient 設定 withCredentials: true），
    // 不需要也不應該在 request body 傳送，因此此處不帶任何 payload。
    return apiClient.post<ApiResponse<LoginResponse>>('/v1/auth/refresh')
  },

  logout() {
    return apiClient.post<ApiResponse<null>>('/v1/auth/logout')
  },

  getMe() {
    return apiClient.get<ApiResponse<UserDto>>('/v1/users/me')
  },
}

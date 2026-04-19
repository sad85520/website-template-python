import apiClient from './client'
import type { LoginRequest, LoginResponse, RegisterRequest, UserDto } from '@/types'

// 契約分層說明：本層 (authApi) 直接對應 DRF endpoint 的 raw response shape，
// 泛型代表後端回傳的 DTO 型別；auth.store 才會將它轉為 AuthResult（成功/失敗統一封包）。
// 若改回 store 暴露的 AuthResult，會模糊兩層職責：下游直接呼叫 authApi.register()
// 的人會以為拿到 AuthResult，實際得到 AxiosResponse<UserDto>。
export const authApi = {
  login(data: LoginRequest) {
    return apiClient.post<LoginResponse>('/v1/auth/login', data)
  },

  register(data: RegisterRequest) {
    // /register 成功時後端回傳 UserDto；store.register() 會丟棄 data 欄位、
    // 僅依賴 success/message 給 UI 顯示，保留完整型別讓未來需要立即展示新使用者時不用再查。
    return apiClient.post<UserDto>('/v1/auth/register', data)
  },

  refresh() {
    // refresh token 由瀏覽器自動帶入 HttpOnly cookie（apiClient 設定 withCredentials: true），
    // 不需要也不應該在 request body 傳送，因此此處不帶任何 payload。
    return apiClient.post<LoginResponse>('/v1/auth/refresh')
  },

  logout() {
    return apiClient.post<void>('/v1/auth/logout')
  },

  getMe() {
    return apiClient.get<UserDto>('/v1/users/me')
  },
}

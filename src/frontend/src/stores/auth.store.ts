import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { isAxiosError } from 'axios'
import { authApi } from '@/api'
import type { UserDto, LoginRequest, RegisterRequest, ProblemDetails, FieldError } from '@/types'

export interface AuthResult {
  success: boolean
  message?: string
  errors?: FieldError[]
}

function extractProblem(error: unknown): AuthResult {
  if (isAxiosError<ProblemDetails>(error) && error.response?.data) {
    const problem = error.response.data
    return {
      success: false,
      message: problem.detail ?? problem.title,
      errors: problem.errors,
    }
  }
  return { success: false, message: '網路錯誤，請稍後再試' }
}

export const useAuthStore = defineStore('auth', () => {
  // access token 僅保存在記憶體（ref）中，不存入 localStorage，
  // 防止 XSS 攻擊透過腳本讀取。頁面重新整理後由 tryRefreshToken() 重新取得。
  const accessToken = ref<string | null>(null)
  const currentUser = ref<UserDto | null>(null)
  const isLoading = ref(false)

  const isAuthenticated = computed(() => !!accessToken.value)

  function setAccessToken(token: string): void {
    accessToken.value = token
  }

  function clearAuth(): void {
    accessToken.value = null
    currentUser.value = null
  }

  async function login(credentials: LoginRequest): Promise<AuthResult> {
    isLoading.value = true
    try {
      const response = await authApi.login(credentials)
      accessToken.value = response.data.access_token
      // 登入回應僅包含 token，不包含使用者資料；
      // 需額外呼叫 /users/me 以取得 currentUser，才能讓 UI 顯示姓名、角色等資訊。
      await fetchCurrentUser()
      return { success: true }
    } catch (error: unknown) {
      return extractProblem(error)
    } finally {
      isLoading.value = false
    }
  }

  async function register(data: RegisterRequest): Promise<AuthResult> {
    isLoading.value = true
    try {
      await authApi.register(data)
      return { success: true }
    } catch (error: unknown) {
      return extractProblem(error)
    } finally {
      isLoading.value = false
    }
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } finally {
      // 無論 API 呼叫是否成功，都必須清除本地狀態；
      // 即使網路斷線也能讓使用者從前端登出，下次使用時 refresh token cookie 仍會由後端驗證拒絕。
      clearAuth()
    }
  }

  async function fetchCurrentUser(): Promise<void> {
    const response = await authApi.getMe()
    // DRF 的 /me 200 理論上必回傳 UserDto，但 backend 若因為 schema 調整暫時回空或
    // 異常結構時，先以 null guard 保護前端 currentUser 狀態不被污染。
    if (response.data) {
      currentUser.value = response.data
    }
  }

  async function tryRefreshToken(): Promise<boolean> {
    // 此方法在 router navigation guard 中被呼叫，用於頁面重整後靜默恢復登入狀態。
    // 成功時回傳 true（代表使用者仍有效登入），失敗時清除殘留狀態並回傳 false。
    try {
      const response = await authApi.refresh()
      accessToken.value = response.data.access_token
      await fetchCurrentUser()
      return true
    } catch {
      clearAuth()
      return false
    }
  }

  return {
    accessToken,
    currentUser,
    isLoading,
    isAuthenticated,
    setAccessToken,
    clearAuth,
    login,
    register,
    logout,
    fetchCurrentUser,
    tryRefreshToken,
  }
})

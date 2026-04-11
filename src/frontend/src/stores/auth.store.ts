import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'
import type { UserDto, LoginRequest, RegisterRequest } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  // access token 僅保存在記憶體（ref）中，不存入 localStorage，
  // 防止 XSS 攻擊透過腳本讀取。頁面重新整理後由 tryRefreshToken() 重新取得。
  const accessToken = ref<string | null>(null)
  const currentUser = ref<UserDto | null>(null)
  const isLoading = ref(false)

  const isAuthenticated = computed(() => !!accessToken.value)

  function setAccessToken(token: string) {
    accessToken.value = token
  }

  function clearAuth() {
    accessToken.value = null
    currentUser.value = null
  }

  async function login(credentials: LoginRequest) {
    isLoading.value = true
    try {
      const response = await authApi.login(credentials)
      if (response.data.success && response.data.data) {
        accessToken.value = response.data.data.accessToken
        await fetchCurrentUser()
      }
      return response.data
    } finally {
      isLoading.value = false
    }
  }

  async function register(data: RegisterRequest) {
    isLoading.value = true
    try {
      const response = await authApi.register(data)
      return response.data
    } finally {
      isLoading.value = false
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      // 無論 API 呼叫是否成功，都必須清除本地狀態；
      // 即使網路斷線也能讓使用者從前端登出，下次使用時 refresh token cookie 仍會由後端驗證拒絕。
      clearAuth()
    }
  }

  async function fetchCurrentUser() {
    const response = await authApi.getMe()
    if (response.data.success && response.data.data) {
      currentUser.value = response.data.data
    }
  }

  async function tryRefreshToken(): Promise<boolean> {
    // 此方法在 router navigation guard 中被呼叫，用於頁面重整後靜默恢復登入狀態。
    // 成功時回傳 true（代表使用者仍有效登入），失敗時清除殘留狀態並回傳 false。
    try {
      const response = await authApi.refresh()
      if (response.data.success && response.data.data) {
        accessToken.value = response.data.data.accessToken
        await fetchCurrentUser()
        return true
      }
      return false
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

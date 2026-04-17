import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores'
import { useNotificationStore } from '@/stores'
import type { LoginRequest, RegisterRequest } from '@/types'

// 僅允許同源的相對路徑作為登入後的重導向目標，
// 防止攻擊者透過 ?redirect=//evil.example 進行 Open Redirect 攻擊。
// 必須以單一 "/" 開頭、且不得以 "//" 或 "/\\" 開頭（後者為 protocol-relative URL）。
function safeRedirect(raw: unknown): string {
  if (typeof raw !== 'string' || raw.length === 0) return '/'
  if (!raw.startsWith('/')) return '/'
  if (raw.startsWith('//') || raw.startsWith('/\\')) return '/'
  return raw
}

export function useAuth() {
  const router = useRouter()
  const route = useRoute()
  const authStore = useAuthStore()
  const notificationStore = useNotificationStore()

  async function login(credentials: LoginRequest) {
    const result = await authStore.login(credentials)

    if (result.success) {
      notificationStore.success('登入成功')
      // 優先重導向至使用者原本嘗試訪問的頁面（由 router guard 附加的 redirect 參數），
      // 若無則導向首頁。
      await router.push(safeRedirect(route.query.redirect))
    } else {
      notificationStore.error(result.message ?? '登入失敗，請確認帳號密碼')
    }

    return result
  }

  async function register(data: RegisterRequest) {
    const result = await authStore.register(data)

    if (result.success) {
      notificationStore.success('註冊成功，請登入')
      await router.push({ name: 'login' })
    } else {
      notificationStore.error(result.message ?? '註冊失敗，請稍後再試')
    }

    return result
  }

  async function logout() {
    await authStore.logout()
    notificationStore.info('已登出')
    await router.push({ name: 'login' })
  }

  return {
    // 直接回傳 store 的 computed/ref 以保持響應性；
    // 若改為解構賦值（const { isAuthenticated } = authStore），會失去響應性連結。
    isAuthenticated: authStore.isAuthenticated,
    currentUser: authStore.currentUser,
    isLoading: authStore.isLoading,
    login,
    register,
    logout,
  }
}

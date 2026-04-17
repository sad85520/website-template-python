import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/stores/auth.store'
import type { LoginResponse } from '@/types'

// isRefreshing 旗標搭配 refreshQueue 實作「token 刷新去重」機制：
// 當多個請求同時收到 401 時，只讓第一個請求實際發起 refresh，
// 其餘請求排隊等候新 token，避免對 /refresh 端點發起多次並發呼叫（可能造成舊 refresh token 被多次使用）。
let isRefreshing = false
let refreshQueue: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

function processRefreshQueue(token: string | null, error: unknown = null): void {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (token) {
      resolve(token)
    } else {
      reject(error)
    }
  })
  refreshQueue = []
}

const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
  withCredentials: true, // 讓 httpOnly cookie (refresh token) 自動帶入
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor：自動附加 JWT access token
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const authStore = useAuthStore()
  if (authStore.accessToken) {
    config.headers.Authorization = `Bearer ${authStore.accessToken}`
  }
  return config
})

// Response interceptor：401 時自動 refresh token
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // _retry 旗標防止無限循環：若 refresh 本身也收到 401（如 refresh token 失效），
    // 則 originalRequest._retry 已為 true，直接拒絕而不再嘗試刷新。
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        refreshQueue.push({ resolve, reject })
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`
        return apiClient(originalRequest)
      })
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      // 這裡刻意使用原始 axios 而非 apiClient 來呼叫 refresh 端點，
      // 避免 apiClient 的 response interceptor 對此請求再次觸發（造成無限遞迴）。
      const response = await axios.post<LoginResponse>(
        `${import.meta.env.VITE_API_BASE_URL}/v1/auth/refresh`,
        {},
        { withCredentials: true }
      )

      const newToken = response.data.access_token
      const authStore = useAuthStore()
      authStore.setAccessToken(newToken)

      processRefreshQueue(newToken)
      originalRequest.headers.Authorization = `Bearer ${newToken}`
      return apiClient(originalRequest)
    } catch (refreshError) {
      processRefreshQueue(null, refreshError)
      const authStore = useAuthStore()
      authStore.clearAuth()
      // 使用 window.location.href 強制全頁跳轉而非 router.push，
      // 是為了清除所有 Vue 元件狀態與 Pinia store，確保登出後不留殘存的記憶體狀態。
      window.location.href = '/login'
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  }
)

export default apiClient

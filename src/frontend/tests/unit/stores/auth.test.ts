import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth.store'
import { authApi } from '@/api'

vi.mock('@/api', () => ({
  authApi: {
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
    getMe: vi.fn(),
  },
}))

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('初始狀態：未認證', () => {
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(false)
    expect(store.accessToken).toBeNull()
    expect(store.currentUser).toBeNull()
  })

  it('登入成功後更新 token 與使用者', async () => {
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      display_name: 'Test',
      role: 'user' as const,
      created_at: '2024-01-01',
    }

    vi.mocked(authApi.login).mockResolvedValue({
      data: { access_token: 'token123', expires_in: 900 },
    } as any)

    vi.mocked(authApi.getMe).mockResolvedValue({
      data: mockUser,
    } as any)

    const store = useAuthStore()
    const result = await store.login({ email: 'test@example.com', password: 'password' })

    expect(result.success).toBe(true)
    expect(store.isAuthenticated).toBe(true)
    expect(store.accessToken).toBe('token123')
    expect(store.currentUser).toEqual(mockUser)
  })

  it('clearAuth 清除認證狀態', () => {
    const store = useAuthStore()
    store.setAccessToken('sometoken')
    store.clearAuth()

    expect(store.isAuthenticated).toBe(false)
    expect(store.accessToken).toBeNull()
  })

  it('登出後清除狀態', async () => {
    vi.mocked(authApi.logout).mockResolvedValue({ data: undefined } as any)

    const store = useAuthStore()
    store.setAccessToken('sometoken')
    await store.logout()

    expect(store.isAuthenticated).toBe(false)
  })
})

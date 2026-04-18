import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AxiosError, AxiosHeaders, type AxiosResponse } from 'axios'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth.store'
import { authApi } from '@/api'

function makeAxiosError<T>(data: T, status = 400): AxiosError<T> {
  const headers = new AxiosHeaders()
  const response: AxiosResponse<T> = {
    data,
    status,
    statusText: '',
    headers,
    config: { headers } as AxiosResponse<T>['config'],
  }
  const error = new AxiosError<T>('request failed', String(status), undefined, undefined, response)
  return error
}

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

  it('登入失敗時回傳 ProblemDetails 欄位', async () => {
    vi.mocked(authApi.login).mockRejectedValue(
      makeAxiosError(
        { title: 'Bad Request', detail: '帳號或密碼錯誤', errors: [{ field: 'email', message: '無效' }] },
        401,
      ),
    )

    const store = useAuthStore()
    const result = await store.login({ email: 'x@example.com', password: 'bad' })

    expect(result.success).toBe(false)
    expect(result.message).toBe('帳號或密碼錯誤')
    expect(result.errors).toEqual([{ field: 'email', message: '無效' }])
    expect(store.isAuthenticated).toBe(false)
  })

  it('登入非 axios 錯誤時回傳預設網路錯誤訊息', async () => {
    vi.mocked(authApi.login).mockRejectedValue(new Error('boom'))

    const store = useAuthStore()
    const result = await store.login({ email: 'x@example.com', password: 'bad' })

    expect(result.success).toBe(false)
    expect(result.message).toBe('網路錯誤，請稍後再試')
  })

  it('註冊成功', async () => {
    vi.mocked(authApi.register).mockResolvedValue({ data: { id: '1' } } as any)

    const store = useAuthStore()
    const result = await store.register({
      email: 'new@example.com',
      password: 'Password123!',
      display_name: 'New',
    })

    expect(result.success).toBe(true)
  })

  it('註冊失敗時回傳錯誤', async () => {
    vi.mocked(authApi.register).mockRejectedValue(
      makeAxiosError({ title: 'conflict', detail: 'email exists' }, 409),
    )

    const store = useAuthStore()
    const result = await store.register({
      email: 'dup@example.com',
      password: 'Password123!',
      display_name: 'Dup',
    })

    expect(result.success).toBe(false)
    expect(result.message).toBe('email exists')
  })

  it('tryRefreshToken 成功時恢復認證狀態', async () => {
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      display_name: 'Test',
      role: 'user' as const,
      created_at: '2024-01-01',
    }

    vi.mocked(authApi.refresh).mockResolvedValue({
      data: { access_token: 'new-token', expires_in: 900 },
    } as any)
    vi.mocked(authApi.getMe).mockResolvedValue({ data: mockUser } as any)

    const store = useAuthStore()
    const ok = await store.tryRefreshToken()

    expect(ok).toBe(true)
    expect(store.accessToken).toBe('new-token')
    expect(store.currentUser).toEqual(mockUser)
  })

  it('tryRefreshToken 失敗時清除狀態並回 false', async () => {
    vi.mocked(authApi.refresh).mockRejectedValue(new Error('expired'))

    const store = useAuthStore()
    store.setAccessToken('stale')
    const ok = await store.tryRefreshToken()

    expect(ok).toBe(false)
    expect(store.isAuthenticated).toBe(false)
  })

  it('fetchCurrentUser 在 data 為空時不污染狀態', async () => {
    vi.mocked(authApi.getMe).mockResolvedValue({ data: null } as any)

    const store = useAuthStore()
    await store.fetchCurrentUser()

    expect(store.currentUser).toBeNull()
  })
})

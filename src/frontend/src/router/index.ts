import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    children: [
      {
        path: '',
        name: 'home',
        component: () => import('@/views/HomeView.vue'),
      },
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { requiresAuth: true },
      },
    ],
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    // guestOnly: true 表示「僅限未登入使用者」，與 requiresAuth 互斥；
    // navigation guard 會將已登入使用者重導向首頁，避免重複登入。
    meta: { guestOnly: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // 頁面刷新時 accessToken 會從記憶體中消失，因此每次導航時都嘗試靜默刷新。
  // 若 accessToken 已存在（同一 session 內的路由跳轉），則跳過此步驟以節省請求。
  if (!authStore.isAuthenticated) {
    await authStore.tryRefreshToken()
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    // 保存原始目標路徑，登入完成後可導回，提升使用者體驗。
    return next({ name: 'login', query: { redirect: to.fullPath } })
  }

  // guestOnly 路由（如登入、註冊頁）對已登入使用者應重導向首頁，
  // 防止已登入使用者看到登入表單造成混淆。
  if (to.meta.guestOnly && authStore.isAuthenticated) {
    return next({ name: 'home' })
  }

  next()
})

export default router

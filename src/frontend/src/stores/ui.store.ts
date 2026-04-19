import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUiStore = defineStore('ui', () => {
  const sidebarOpen = ref(false)
  const globalLoading = ref(false)
  const theme = ref<'light' | 'dark'>('light')

  function toggleSidebar() {
    sidebarOpen.value = !sidebarOpen.value
  }

  function setTheme(newTheme: 'light' | 'dark') {
    theme.value = newTheme
    // 透過操作 <html> 元素的 class 切換 Tailwind CSS 的 dark mode，
    // 必須同步更新 DOM（而非僅更新 store），因為 Tailwind 的 dark variant 依賴此 class 的存在。
    // SSR guard：若未來此 template 改用 SSR（Nuxt / vite-ssg）首次 render 於 Node，
    // 直接存 document 會 ReferenceError。typeof 守門後 client hydrate 時會再觸發一次。
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', newTheme === 'dark')
    }
  }

  function setLoading(loading: boolean) {
    globalLoading.value = loading
  }

  return {
    sidebarOpen,
    globalLoading,
    theme,
    toggleSidebar,
    setTheme,
    setLoading,
  }
})

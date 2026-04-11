import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './assets/styles/main.css'

const app = createApp(App)

// Pinia 必須在 router 之前安裝，因為 router 的 navigation guard（beforeEach）
// 會呼叫 useAuthStore()，而 Pinia 必須已初始化才能使用 store。
app.use(createPinia())
app.use(router)
app.mount('#app')

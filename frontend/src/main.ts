import { createApp } from 'vue'
import './main.css'
import App from './App.vue'
import { onUnauthorized } from './api'
import { i18n } from './i18n'
import { loginRoute, router } from './router'
import { useSession } from './session'

onUnauthorized(() => {
  useSession().clearUser()
  const current = router.currentRoute.value
  if (!current.meta.public) router.replace(loginRoute(current))
})

const app = createApp(App).use(i18n).use(router)
router.isReady().then(() => app.mount('#app'))

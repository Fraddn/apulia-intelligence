import { createApp } from 'vue'
import './main.css'
import App from './App.vue'
import { i18n } from './i18n'
import { router } from './router'

createApp(App).use(i18n).use(router).mount('#app')

<template>
  <header class="app-header">
    <div class="app-header__inner">
      <RouterLink to="/" class="app-header__brand" :aria-label="t('app.name')">
        <span class="app-header__mark">
          <svg viewBox="0 0 32 32" width="24" height="24" fill="currentColor" aria-hidden="true">
            <circle cx="16" cy="4.5" r="1.8" /><rect x="13.5" y="7.5" width="5" height="2.5" rx="1" /><rect x="11.5" y="11" width="9" height="2.5" rx="1" /><rect x="9.5" y="14.5" width="13" height="2.5" rx="1" /><rect x="7" y="18" width="18" height="2.5" rx="1" /><path fill-rule="evenodd" d="M8.5 21.5h15v7.5h-15z M14 29v-3a2 2 0 0 1 4 0v3z" />
          </svg>
        </span>
        <span class="app-header__title">Puglia<span class="app-header__title-accent">Imprese</span></span>
        <span v-if="version" class="app-header__version" :title="t('app.version', { version })">
          {{ version === 'dev' ? 'dev' : `v${version}` }}
        </span>
      </RouterLink>
      <nav class="app-header__nav">
        <RouterLink to="/" class="app-header__link" exact-active-class="app-header__link--active">
          <AppIcon name="dashboard" />
          {{ t('nav.dashboard') }}
        </RouterLink>
        <RouterLink to="/companies" class="app-header__link" active-class="app-header__link--active">
          <AppIcon name="companies" />
          {{ t('nav.companies') }}
        </RouterLink>
      </nav>
      <div class="app-header__controls">
        <UserMenu />
        <LanguageSwitch />
        <ThemeToggle />
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '../api'
import AppIcon from './AppIcon.vue'
import LanguageSwitch from './LanguageSwitch.vue'
import ThemeToggle from './ThemeToggle.vue'
import UserMenu from './UserMenu.vue'

const { t } = useI18n()
const version = ref('')

onMounted(async () => {
  try {
    version.value = (await api.health()).version
  } catch {
    version.value = ''
  }
})
</script>

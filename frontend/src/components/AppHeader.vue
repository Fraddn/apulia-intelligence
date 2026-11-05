<template>
  <header class="app-header">
    <div class="app-header__inner">
      <RouterLink to="/" class="app-header__brand">
        <span class="app-header__mark">
          <svg viewBox="0 0 32 32" width="20" height="20" aria-hidden="true">
            <path d="M9 23V15M16 23V9M23 23V18" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" />
          </svg>
        </span>
        <span class="app-header__titles">
          <span class="app-header__title-row">
            <span class="app-header__title">{{ t('app.name') }}</span>
            <span v-if="version" class="app-header__version" :title="t('app.version', { version })">
              {{ version === 'dev' ? 'dev' : `v${version}` }}
            </span>
          </span>
          <span class="app-header__tagline">{{ t('app.tagline') }}</span>
        </span>
      </RouterLink>
      <nav class="app-header__nav">
        <RouterLink to="/" class="app-header__link" exact-active-class="app-header__link--active">
          {{ t('nav.dashboard') }}
        </RouterLink>
        <RouterLink to="/companies" class="app-header__link" active-class="app-header__link--active">
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

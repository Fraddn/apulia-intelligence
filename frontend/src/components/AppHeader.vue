<template>
  <header class="app-header">
    <div class="app-header__inner">
      <RouterLink to="/" class="app-header__brand" :aria-label="t('app.name')">
        <span class="app-header__mark">
          <BrandMark />
        </span>
        <span class="app-header__title">Puglia<span class="app-header__title-accent">Imprese</span></span>
        <span v-if="version" class="app-header__version" :title="t('app.version', { version })">
          {{ version === 'dev' ? 'dev' : `v${version}` }}
        </span>
      </RouterLink>
      <nav v-if="user" class="app-header__nav">
        <RouterLink to="/" class="app-header__link" exact-active-class="app-header__link--active">
          <AppIcon name="dashboard" />
          {{ t('nav.dashboard') }}
        </RouterLink>
        <RouterLink to="/companies" class="app-header__link" active-class="app-header__link--active">
          <AppIcon name="companies" />
          {{ t('nav.companies') }}
        </RouterLink>
        <RouterLink to="/compare" class="app-header__link" active-class="app-header__link--active">
          <AppIcon name="compare" />
          {{ t('nav.compare') }}
        </RouterLink>
        <RouterLink to="/library" class="app-header__link" active-class="app-header__link--active">
          <AppIcon name="bookmark" />
          {{ t('nav.library') }}
        </RouterLink>
        <RouterLink to="/info" class="app-header__link" active-class="app-header__link--active">
          <AppIcon name="info" />
          {{ t('nav.glossary') }}
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
import { useSession } from '../session'
import AppIcon from './AppIcon.vue'
import BrandMark from './BrandMark.vue'
import LanguageSwitch from './LanguageSwitch.vue'
import ThemeToggle from './ThemeToggle.vue'
import UserMenu from './UserMenu.vue'

const { t } = useI18n()
const version = ref('')
const { user } = useSession()

onMounted(async () => {
  try {
    version.value = (await api.health()).version
  } catch {
    version.value = ''
  }
})
</script>

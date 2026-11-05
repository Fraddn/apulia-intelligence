<template>
  <button type="button" class="theme-toggle" :aria-label="label" :title="label" @click="toggleTheme">
    <svg v-if="theme === 'dark'" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <circle cx="12" cy="12" r="4.5" fill="none" stroke="currentColor" stroke-width="2" />
      <path
        d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
      />
    </svg>
    <svg v-else viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path
        d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linejoin="round"
      />
    </svg>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTheme } from '../theme'

const { t } = useI18n()
const { theme, toggleTheme } = useTheme()

const label = computed(() => (theme.value === 'dark' ? t('settings.switchToLight') : t('settings.switchToDark')))
</script>

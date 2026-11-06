<template>
  <button type="button" class="theme-toggle" :aria-label="label" :title="label" @click="toggleTheme">
    <Transition name="spin" mode="out-in">
      <AppIcon :key="theme" :name="theme === 'dark' ? 'sun' : 'moon'" />
    </Transition>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTheme } from '../theme'
import AppIcon from './AppIcon.vue'

const { t } = useI18n()
const { theme, toggleTheme } = useTheme()

const label = computed(() => (theme.value === 'dark' ? t('settings.switchToLight') : t('settings.switchToDark')))
</script>

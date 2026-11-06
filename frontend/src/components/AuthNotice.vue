<template>
  <div class="auth-notice" :class="`auth-notice--${tone}`" :role="tone === 'error' ? 'alert' : 'status'">
    <AppIcon :name="tone === 'error' ? 'alert' : tone === 'success' ? 'check' : 'mail'" :size="18" />
    <div class="auth-notice__body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import AppIcon from './AppIcon.vue'

defineProps<{ tone: 'info' | 'success' | 'error' }>()
</script>

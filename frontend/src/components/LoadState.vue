<template>
  <div v-if="error" class="load-state card" role="alert">
    <p>{{ message ?? t('common.error') }}</p>
    <button v-if="retryable" type="button" class="btn" @click="emit('retry')">{{ t('common.retry') }}</button>
  </div>
  <div v-else-if="loading" class="load-state" aria-live="polite">
    <span class="load-state__spinner" aria-hidden="true" />
    <span class="muted">{{ t('common.loading') }}</span>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

withDefaults(defineProps<{ loading: boolean; error: boolean; message?: string; retryable?: boolean }>(), {
  message: undefined,
  retryable: true,
})
const emit = defineEmits<{ retry: [] }>()

const { t } = useI18n()
</script>

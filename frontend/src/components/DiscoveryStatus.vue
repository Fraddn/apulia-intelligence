<template>
  <p v-if="searching" class="website-status muted" aria-live="polite">
    <span class="load-state__spinner" aria-hidden="true" />
    {{ t('discovery.searching') }}
  </p>
  <p v-else-if="message" class="website-status muted">{{ message }}</p>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Discovery } from '../api'

const props = defineProps<{ searching: boolean; discovery: Discovery | null }>()

const { t } = useI18n()

const MESSAGES: Record<string, string> = {
  not_found: 'discovery.notFound',
  no_candidates: 'discovery.noCandidates',
  busy: 'discovery.busy',
  timeout: 'discovery.timeout',
}

const message = computed(() => {
  const key = props.discovery ? MESSAGES[props.discovery.status] : undefined
  return key ? t(key) : ''
})
</script>

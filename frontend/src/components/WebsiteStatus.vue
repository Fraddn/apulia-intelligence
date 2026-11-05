<template>
  <p v-if="message" class="website-status muted">
    {{ message }}
    <a v-if="check?.url && check.status === 'verified'" :href="check.url" target="_blank" rel="noopener">{{ t('website.open') }}</a>
  </p>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { WebsiteCheck } from '../api'
import { formatDate } from '../format'

const props = defineProps<{ check: WebsiteCheck | null }>()

const { t, locale } = useI18n()

const message = computed(() => {
  switch (props.check?.status) {
    case 'verified':
      return t('website.verified', { date: formatDate(props.check.checked_at, locale.value) })
    case 'vat_not_found':
      return t('website.vatNotFound')
    case 'unreachable':
      return t('website.unreachable')
    case 'blocked':
      return t('website.blocked')
    default:
      return ''
  }
})
</script>

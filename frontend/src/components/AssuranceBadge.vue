<template>
  <span class="badge" :class="`badge--${assurance}`">
    <svg class="badge__icon" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
      <path v-if="assurance === 'official'" d="M3.5 8.5l3 3 6-7" />
      <path v-else-if="assurance === 'derived'" d="M3 8h8M8 4.5L11.5 8 8 11.5" />
      <path v-else-if="assurance === 'inferred'" d="M8 2.5l1.4 3.6 3.6 1.4-3.6 1.4L8 12.5 6.6 8.9 3 7.5l3.6-1.4z" />
      <path v-else-if="assurance === 'company'" d="M3 13.5V5l5-2.5L13 5v8.5M6 13.5V9h4v4.5" />
      <path v-else d="M4 12l1-3 6-6 2 2-6 6z" />
    </svg>
    {{ t(`assurance.${assurance}`) }}
  </span>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { Assurance } from '../api'

defineProps<{ assurance: Assurance }>()

const { t } = useI18n()
</script>

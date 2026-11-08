<template>
  <ul class="aid-list">
    <li v-for="item in items" :key="item.cor" class="aid-list__item">
      <div class="aid-list__head">
        <span class="aid-list__title">{{ item.project_title || item.measure_title }}</span>
        <strong v-if="item.aid_amount !== null" class="aid-list__amount">{{ formatCurrency(item.aid_amount, locale) }}</strong>
        <span v-else class="aid-list__amount muted">{{ t('common.notAvailable') }}</span>
      </div>
      <p v-if="item.project_title && item.measure_title" class="aid-list__measure muted">{{ item.measure_title }}</p>
      <div class="meta-line">
        <span v-if="item.granting_body">{{ item.granting_body }}</span>
        <span v-if="item.procedures">{{ item.procedures }}</span>
        <span v-if="item.granted_on">{{ formatDate(item.granted_on, locale) }}</span>
        <a v-if="isWebLink(item.transparency_url)" :href="item.transparency_url" target="_blank" rel="noopener">{{ t('aid.details') }}</a>
      </div>
      <p v-if="item.objectives" class="aid-list__objectives">{{ item.objectives }}</p>
    </li>
  </ul>
  <p v-if="total > items.length" class="aid-list__more muted">
    {{ t('aid.showing', { shown: formatNumber(items.length, locale), total: formatNumber(total, locale) }) }}
  </p>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { StateAidItem } from '../api'
import { formatCurrency, formatDate, formatNumber, isWebLink } from '../format'

defineProps<{ items: StateAidItem[]; total: number }>()

const { t, locale } = useI18n()
</script>

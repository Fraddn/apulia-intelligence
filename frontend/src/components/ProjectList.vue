<template>
  <ul class="project-list">
    <li v-for="project in projects" :key="`${project.code}-${project.role}`" class="project-list__item">
      <div class="project-list__head">
        <a v-if="isWebLink(project.url)" :href="project.url" target="_blank" rel="noopener" class="project-list__title">{{ project.title }}</a>
        <span v-else class="project-list__title">{{ project.title }}</span>
        <span class="project-list__amount">
          <span class="project-list__amount-label">
            {{ project.role === 'beneficiary' ? t('funding.publicFunding') : t('funding.projectValue') }}
          </span>
          <strong v-if="project.public_funding !== null">{{ formatCurrency(project.public_funding, locale) }}</strong>
          <span v-else class="muted">{{ t('common.notAvailable') }}</span>
        </span>
      </div>
      <div class="meta-line">
        <span class="badge" :class="{ 'badge--official': project.role === 'beneficiary' }">
          {{ t(`funding.roles.${project.role}`) }}
        </span>
        <span v-if="project.role === 'beneficiary'">
          {{ project.beneficiaries_count > 1 ? t('funding.sharedBy', { count: project.beneficiaries_count }) : t('funding.soleBeneficiary') }}
        </span>
        <span v-if="project.theme_code || project.theme">{{ themeLabel(project) }}</span>
        <span>{{ t(`funding.statuses.${project.status}`) }}</span>
        <span v-if="project.start_date">
          {{ t('funding.period', { start: formatDate(project.start_date, locale), end: formatDate(project.actual_end_date ?? project.expected_end_date, locale) }) }}
        </span>
      </div>
      <p v-if="project.summary && project.summary !== project.title" class="project-list__summary">{{ project.summary }}</p>
    </li>
  </ul>
  <p v-if="total > projects.length" class="project-list__more muted">
    {{ t('funding.showing', { shown: formatNumber(projects.length, locale), total: formatNumber(total, locale) }) }}
  </p>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { FundedProject } from '../api'
import { formatCurrency, formatDate, formatNumber, isWebLink } from '../format'

defineProps<{ projects: FundedProject[]; total: number }>()

const { t, te, locale } = useI18n()

function themeLabel(project: FundedProject) {
  const key = `funding.themes.${project.theme_code}`
  return project.theme_code && te(key) ? t(key) : project.theme
}
</script>

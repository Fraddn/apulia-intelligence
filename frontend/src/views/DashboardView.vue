<template>
  <section class="dashboard">
    <h1 class="page-title">{{ t('dashboard.title') }}</h1>
    <LoadState :loading="loading" :error="failed" @retry="load">
      <template v-if="stats">
        <div class="dashboard__tiles">
          <StatTile hero :label="t('dashboard.totalCompanies')" :value="n(stats.total)" :hint="t('dashboard.heroHint', { source: stats.sources[0]?.name ?? '', date: dataDate })" />
          <StatTile
            :label="t('dashboard.withAteco')"
            :value="pct(stats.with_ateco, stats.total)"
            :hint="n(stats.with_ateco)"
          />
          <StatTile
            :label="t('dashboard.ictProfessional')"
            :value="n(ictProfessional)"
            :hint="t('dashboard.ictProfessionalHint')"
          />
          <StatTile
            :label="t('dashboard.sizeKnown')"
            :value="pct(stats.size_known, stats.total)"
            :hint="n(stats.size_known)"
          />
          <StatTile :label="t('dashboard.dataDate')" :value="dataDate" :hint="sourceNames" />
          <StatTile
            :label="t('dashboard.fundedCompanies')"
            :value="n(stats.funding.beneficiary_companies)"
            :hint="t('dashboard.fundedCompaniesHint', { share: pct(stats.funding.beneficiary_companies, stats.total) })"
          />
          <StatTile
            :label="t('dashboard.fundedProjects')"
            :value="n(stats.funding.beneficiary_projects)"
            :hint="t('dashboard.fundedProjectsHint')"
          />
          <StatTile
            class="dashboard__tile--wide"
            :label="t('dashboard.soleFunding')"
            :value="formatCurrency(stats.funding.sole_beneficiary_funding, locale, true)"
            :hint="t('dashboard.soleFundingHint')"
          />
          <StatTile
            class="dashboard__tile--wide"
            :label="t('dashboard.aidCompanies')"
            :value="n(stats.aid.companies)"
            :hint="t('dashboard.aidCompaniesHint', { grants: n(stats.aid.grants) })"
          />
          <StatTile
            class="dashboard__tile--wide"
            :label="t('dashboard.aidTotal')"
            :value="formatCurrency(stats.aid.total_amount, locale, true)"
            :hint="t('dashboard.aidTotalHint')"
          />
        </div>

        <div class="dashboard__charts">
          <div class="card">
            <BarChart :title="t('dashboard.byProvince')" :items="provinceItems" :total="stats.total" />
            <p class="dashboard__note muted">{{ t('dashboard.batNote') }}</p>
          </div>
          <div class="card">
            <BarChart
              :title="t('dashboard.bySector')"
              :subtitle="t('dashboard.bySectorHint', { count: TOP_SECTORS })"
              :items="sectorItems"
              :total="stats.total"
            />
          </div>
          <div class="card">
            <BarChart
              :title="t('dashboard.byTheme')"
              :subtitle="t('dashboard.byThemeHint')"
              :items="themeItems"
              :total="stats.funding.beneficiary_projects"
            />
          </div>
        </div>

        <aside class="card dashboard__coverage">
          <div>
            <h2>{{ t('dashboard.coverageTitle') }}</h2>
            <p>{{ t('dashboard.coverage') }}</p>
          </div>
          <RouterLink to="/companies" class="btn btn--primary">{{ t('dashboard.viewAll') }} →</RouterLink>
        </aside>
      </template>
    </LoadState>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api, type Stats } from '../api'
import BarChart, { type BarItem } from '../components/BarChart.vue'
import LoadState from '../components/LoadState.vue'
import StatTile from '../components/StatTile.vue'
import { formatCurrency, formatDate, formatNumber, formatPercent } from '../format'

const TOP_SECTORS = 10

const { t, te, locale } = useI18n()
const stats = ref<Stats | null>(null)
const loading = ref(true)
const failed = ref(false)

async function load() {
  loading.value = true
  failed.value = false
  try {
    stats.value = await api.stats()
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

onMounted(load)

const n = (value: number) => formatNumber(value, locale.value)
const pct = (part: number, total: number) => formatPercent(part, total, locale.value)

const ictProfessional = computed(
  () => stats.value?.by_section.filter((s) => s.section === 'J' || s.section === 'M').reduce((a, s) => a + s.count, 0) ?? 0,
)

const dataDate = computed(() => formatDate(stats.value?.sources[0]?.data_date ?? null, locale.value))
const sourceNames = computed(() => stats.value?.sources.map((s) => s.name).join(', ') ?? '')

const provinceItems = computed<BarItem[]>(
  () =>
    stats.value?.by_province.map((p) => ({
      key: p.province,
      label: t(`provinces.${p.province}`),
      value: p.count,
      to: { name: 'companies', query: { province: p.province } },
    })) ?? [],
)

const themeItems = computed<BarItem[]>(
  () =>
    stats.value?.funding.by_theme.map((theme) => ({
      key: theme.theme_code,
      label: te(`funding.themes.${theme.theme_code}`) ? t(`funding.themes.${theme.theme_code}`) : theme.theme,
      value: theme.count,
    })) ?? [],
)

const sectorItems = computed<BarItem[]>(
  () =>
    stats.value?.by_section.slice(0, TOP_SECTORS).map((s) => ({
      key: s.section,
      label: `${s.section} · ${t(`sections.${s.section}`)}`,
      value: s.count,
      to: { name: 'companies', query: { section: s.section } },
    })) ?? [],
)
</script>

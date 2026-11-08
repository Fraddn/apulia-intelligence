<template>
  <section class="dashboard">
    <PageHeader :title="t('dashboard.title')" :info-title="t('dashboard.infoTitle')" :items="INFO_KEYS.map((key) => t(`dashboard.${key}`))" />
    <LoadState :loading="loading && !stats" :error="failed" @retry="load">
      <template v-if="stats">
        <form class="card dashboard__scope" @submit.prevent>
          <span class="dashboard__scope-label">{{ t('dashboard.filterDashboard') }}</span>
          <select name="province" class="input" :value="scope.province" :aria-label="t('companies.province')" @change="setScope({ province: ($event.target as HTMLSelectElement).value })">
            <option value="">{{ t('companies.province') }}: {{ t('common.all') }}</option>
            <option v-for="code in PROVINCES" :key="code" :value="code">{{ t(`provinces.${code}`) }}</option>
          </select>
          <select name="section" class="input" :value="scope.section" :aria-label="t('companies.sector')" @change="setScope({ section: ($event.target as HTMLSelectElement).value })">
            <option value="">{{ t('companies.sector') }}: {{ t('common.all') }}</option>
            <option v-for="code in SECTIONS" :key="code" :value="code">{{ code }} · {{ t(`sections.${code}`) }}</option>
          </select>
          <button v-if="scopeLabel" type="button" class="btn btn--round" @click="setScope({ province: '', section: '' })">
            ✕ {{ t('dashboard.clearFilter') }}
          </button>
        </form>

        <div class="dashboard__body" :class="{ 'dashboard__body--busy': loading }">
          <div class="card dashboard__hero">
            <RouterLink :to="companiesLink()" class="dashboard__hero-main">
              <span class="dashboard__metric-label">{{ scopeLabel ? t('dashboard.companiesInScope') : t('dashboard.totalCompanies') }}</span>
              <AnimatedNumber class="dashboard__hero-value" :value="stats.total" :format="count" />
              <span class="dashboard__metric-hint">{{ t('dashboard.heroHint', { source: stats.sources[0]?.name ?? '', date: dataDate }) }}</span>
              <span class="dashboard__metric-cta">{{ t('dashboard.viewCompanies') }} →</span>
            </RouterLink>
            <dl class="dashboard__coverage-stats">
              <div v-for="item in coverageStats" :key="item.label" class="dashboard__metric">
                <dt class="dashboard__metric-label">{{ item.label }}</dt>
                <dd class="dashboard__metric-value">
                  <AnimatedNumber v-if="typeof item.value === 'number'" :value="item.value" :format="item.format!" />
                  <template v-else>{{ item.value }}</template>
                </dd>
                <dd class="dashboard__metric-hint">{{ item.hint }}</dd>
              </div>
            </dl>
          </div>

          <div class="dashboard__panels">
            <section v-for="panel in panels" :key="panel.title" class="card dashboard__panel">
              <h2 class="dashboard__panel-title">{{ panel.title }}</h2>
              <p class="dashboard__panel-source muted">{{ panel.source }}</p>
              <div class="dashboard__metrics">
                <component
                  :is="metric.to ? RouterLink : 'div'"
                  v-for="metric in panel.metrics"
                  :key="metric.label"
                  :to="metric.to"
                  class="dashboard__metric"
                  :class="{ 'dashboard__metric--link': metric.to }"
                >
                  <span class="dashboard__metric-label">{{ metric.label }}</span>
                  <AnimatedNumber class="dashboard__metric-value" :value="metric.value" :format="metric.format" />
                  <span class="dashboard__metric-hint">{{ metric.hint }}</span>
                  <span v-if="metric.to" class="dashboard__metric-cta">{{ t('dashboard.viewCompanies') }} →</span>
                </component>
              </div>
            </section>
          </div>

          <div class="dashboard__charts">
            <div class="card">
              <BarChart
                :title="t('dashboard.byProvince')"
                :items="provinceItems"
                :selected="scope.province"
              />
              <p class="dashboard__note muted">{{ t('dashboard.batNote') }}</p>
            </div>
            <div class="card">
              <BarChart :title="t('dashboard.bySize')" :subtitle="t('dashboard.bySizeHint')" :items="sizeItems" />
            </div>
            <div class="card">
              <BarChart
                :title="t('dashboard.bySector')"
                :subtitle="t('dashboard.bySectorHint', { count: TOP_SECTORS })"
                :items="sectorItems"
                :total="sectorTotal"
                :selected="scope.section"
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
        </div>
      </template>
    </LoadState>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter, type RouteLocationRaw } from 'vue-router'
import { api, type Stats } from '../api'
import AnimatedNumber from '../components/AnimatedNumber.vue'
import BarChart, { type BarItem } from '../components/BarChart.vue'
import LoadState from '../components/LoadState.vue'
import PageHeader from '../components/PageHeader.vue'
import { formatCurrency, formatDate, formatNumber, formatPercent } from '../format'

const TOP_SECTORS = 10
const INFO_KEYS = ['info1', 'info2', 'info3', 'info4', 'info5']
const PROVINCES = ['BA', 'BT', 'BR', 'FG', 'LE', 'TA']
const SECTIONS = 'ABCDEFGHIJKLMNOPQRSTU'.split('')
const SIZES = ['micro', 'small', 'medium', 'sme', 'large', 'unknown']

const { t, te, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const stats = ref<Stats | null>(null)
const loading = ref(true)
const failed = ref(false)

const scope = computed(() => ({
  province: String(route.query.province ?? ''),
  section: String(route.query.section ?? ''),
}))

const scopeQuery = computed(() => Object.fromEntries(Object.entries(scope.value).filter(([, v]) => v)))

const scopeLabel = computed(() =>
  [
    scope.value.province && t(`provinces.${scope.value.province}`),
    scope.value.section && `${scope.value.section} · ${t(`sections.${scope.value.section}`)}`,
  ]
    .filter(Boolean)
    .join(' · '),
)

let requestId = 0

async function load() {
  const id = ++requestId
  loading.value = true
  failed.value = false
  try {
    const result = await api.stats(scopeQuery.value)
    if (id === requestId) stats.value = result
  } catch {
    if (id === requestId) failed.value = true
  } finally {
    if (id === requestId) loading.value = false
  }
}

watch(scopeQuery, load, { immediate: true })

function setScope(changes: Partial<{ province: string; section: string }>) {
  const query = { ...scope.value, ...changes }
  router.replace({ query: Object.fromEntries(Object.entries(query).filter(([, v]) => v)) })
}

function companiesLink(extra: Record<string, string> = {}): RouteLocationRaw {
  return { name: 'companies', query: { ...scopeQuery.value, ...extra } }
}

const n = (value: number) => formatNumber(value, locale.value)
const pct = (part: number, total: number) => formatPercent(part, total, locale.value)
const money = (value: number) => formatCurrency(value, locale.value, true)
const count = (value: number) => n(Math.round(value))
const ratio = (value: number) => formatPercent(value, 1, locale.value)

const dataDate = computed(() => formatDate(stats.value?.sources[0]?.data_date ?? null, locale.value))

const coverageStats = computed(() => {
  const s = stats.value
  if (!s) return []
  const share = (part: number) => (s.total ? part / s.total : 0)
  return [
    { label: t('dashboard.withAteco'), value: share(s.with_ateco), format: ratio, hint: n(s.with_ateco) },
    { label: t('dashboard.sizeKnown'), value: share(s.size_known), format: ratio, hint: n(s.size_known) },
    {
      label: t('dashboard.dataDate'),
      value: dataDate.value,
      hint: t('dashboard.sourceCount', { count: n(s.sources.length) }, s.sources.length),
    },
  ] as { label: string; value: number | string; format?: (value: number) => string; hint: string }[]
})

const panels = computed(() => {
  const s = stats.value
  if (!s) return []
  return [
    {
      title: t('dashboard.fundingTitle'),
      source: t('dashboard.fundingSource'),
      metrics: [
        {
          label: t('dashboard.fundedCompanies'),
          value: s.funding.beneficiary_companies,
          format: count,
          hint: t('dashboard.fundedCompaniesHint', { share: pct(s.funding.beneficiary_companies, s.total) }),
          to: companiesLink({ min_projects: '1' }),
        },
        {
          label: t('dashboard.fundedProjects'),
          value: s.funding.beneficiary_projects,
          format: count,
          hint: t('dashboard.fundedProjectsHint'),
          to: companiesLink({ min_projects: '1', sort: 'projects' }),
        },
        {
          label: t('dashboard.soleFunding'),
          value: s.funding.sole_beneficiary_funding,
          format: money,
          hint: t('dashboard.soleFundingHint'),
          to: companiesLink({ min_projects: '1', sort: 'funding' }),
        },
      ],
    },
    {
      title: t('dashboard.aidTitle'),
      source: t('dashboard.aidSource'),
      metrics: [
        {
          label: t('dashboard.aidCompanies'),
          value: s.aid.companies,
          format: count,
          hint: t('dashboard.aidCompaniesHint', { grants: n(s.aid.grants) }),
        },
        { label: t('dashboard.aidTotal'), value: s.aid.total_amount, format: money, hint: t('dashboard.aidTotalHint') },
      ],
    },
  ] as { title: string; source: string; metrics: { label: string; value: number; format: (value: number) => string; hint: string; to?: RouteLocationRaw }[] }[]
})

const provinceItems = computed<BarItem[]>(
  () =>
    stats.value?.by_province.map((p) => ({
      key: p.province,
      label: t(`provinces.${p.province}`),
      value: p.count,
      to: companiesLink({ province: p.province }),
    })) ?? [],
)

const sizeItems = computed<BarItem[]>(() => {
  const counts = new Map(stats.value?.by_size.map((s) => [s.size, s.count]) ?? [])
  return SIZES.filter((size) => counts.get(size)).map((size) => ({
    key: size,
    label: size === 'sme' ? t('dashboard.smeUnspecified') : t(`size.${size}`),
    value: counts.get(size) ?? 0,
    to: size === 'sme' ? undefined : companiesLink({ size }),
  }))
})

const sectorTotal = computed(() => stats.value?.by_section.reduce((sum, s) => sum + s.count, 0) ?? 0)

const sectorItems = computed<BarItem[]>(() => {
  const all = stats.value?.by_section ?? []
  const top = all.slice(0, TOP_SECTORS)
  const selected = all.find((s) => s.section === scope.value.section)
  if (selected && !top.includes(selected)) top.push(selected)
  return top.map((s) => ({
    key: s.section,
    label: `${s.section} · ${t(`sections.${s.section}`)}`,
    value: s.count,
    to: companiesLink({ section: s.section }),
  }))
})

const themeItems = computed<BarItem[]>(
  () =>
    stats.value?.funding.by_theme.map((theme) => ({
      key: theme.theme_code,
      label: te(`funding.themes.${theme.theme_code}`) ? t(`funding.themes.${theme.theme_code}`) : theme.theme,
      value: theme.count,
      to: companiesLink({ theme: theme.theme_code }),
    })) ?? [],
)
</script>

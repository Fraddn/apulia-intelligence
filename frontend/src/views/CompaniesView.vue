<template>
  <section class="companies">
    <header class="companies__top">
      <h1 class="page-title">{{ t('companies.title') }}</h1>
      <p v-if="page" class="companies__count muted">{{ t('companies.results', { count: n(page.count) }, page.count) }}</p>
    </header>

    <form class="companies__filters card" role="search" @submit.prevent>
      <label class="companies__filter companies__filter--search">
        <span class="visually-hidden">{{ t('companies.searchLabel') }}</span>
        <input
          v-model="search"
          class="input"
          type="search"
          :placeholder="t('companies.searchPlaceholder')"
          :aria-label="t('companies.searchLabel')"
        >
      </label>
      <label class="companies__filter">
        <span class="visually-hidden">{{ t('companies.province') }}</span>
        <select class="input" :value="filters.province" :aria-label="t('companies.province')" @change="setFilter('province', $event)">
          <option value="">{{ t('companies.province') }}: {{ t('common.all') }}</option>
          <option v-for="code in PROVINCES" :key="code" :value="code">{{ t(`provinces.${code}`) }}</option>
        </select>
      </label>
      <label class="companies__filter">
        <span class="visually-hidden">{{ t('companies.sector') }}</span>
        <select name="section" class="input" :value="filters.section" :aria-label="t('companies.sector')" @change="setSection">
          <option value="">{{ t('companies.sector') }}: {{ t('common.all') }}</option>
          <option v-for="code in SECTIONS" :key="code" :value="code">{{ code }} · {{ t(`sections.${code}`) }}</option>
        </select>
      </label>
      <label v-if="divisions.length" class="companies__filter">
        <span class="visually-hidden">{{ t('companies.subsector') }}</span>
        <select name="division" class="input" :value="filters.division" :aria-label="t('companies.subsector')" @change="setFilter('division', $event)">
          <option value="">{{ t('companies.subsector') }}: {{ t('common.all') }}</option>
          <option v-for="code in divisions" :key="code" :value="code">{{ code }} · {{ t(`divisions.${code}`) }}</option>
        </select>
      </label>
      <label class="companies__filter">
        <span class="visually-hidden">{{ t('companies.theme') }}</span>
        <select name="theme" class="input" :value="filters.theme" :aria-label="t('companies.theme')" @change="setFilter('theme', $event)">
          <option value="">{{ t('companies.theme') }}: {{ t('common.all') }}</option>
          <option v-for="code in THEMES" :key="code" :value="code">{{ t(`funding.themes.${code}`) }}</option>
        </select>
      </label>
      <label class="companies__filter companies__check">
        <input name="funded" type="checkbox" :checked="filters.funded === 'true'" @change="setFunded">
        <span>{{ t('companies.fundedOnly') }}</span>
      </label>
      <label class="companies__filter companies__sort">
        <span>{{ t('companies.sortBy') }}</span>
        <select name="sort" class="input" :value="filters.sort || 'name'" @change="setSort">
          <option v-for="option in SORTS" :key="option" :value="option">{{ t(`companies.sort.${option}`) }}</option>
        </select>
      </label>
      <button v-if="hasFilters" type="button" class="btn" @click="reset">{{ t('companies.reset') }}</button>
    </form>

    <LoadState :loading="loading && !page" :error="failed" @retry="load">
      <div v-if="page" class="card companies__table-card" :class="{ 'companies__table-card--busy': loading }">
        <p v-if="!page.items.length" class="companies__empty muted">{{ t('companies.empty') }}</p>
        <div v-else class="companies__table-wrap">
          <table class="companies__table">
            <thead>
              <tr>
                <th scope="col">{{ t('companies.columns.name') }}</th>
                <th scope="col">{{ t('companies.columns.vat') }}</th>
                <th scope="col">{{ t('companies.columns.province') }}</th>
                <th scope="col">{{ t('companies.columns.sector') }}</th>
                <th scope="col">{{ t('companies.columns.size') }}</th>
                <th scope="col" class="companies__num">{{ t('companies.columns.projects') }}</th>
                <th scope="col" class="companies__num">{{ t('companies.columns.funding') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="company in page.items" :key="company.vat_number">
                <td>
                  <RouterLink :to="{ name: 'company', params: { vat: company.vat_number } }">{{ company.name }}</RouterLink>
                </td>
                <td class="mono">{{ company.vat_number }}</td>
                <td>{{ company.province ? t(`provinces.${company.province}`) : '–' }}</td>
                <td>
                  <span v-if="company.ateco_section" class="companies__sector" :title="t(`sections.${company.ateco_section}`)">
                    <span class="companies__section-letter">{{ company.ateco_section }}</span>
                    <span class="muted mono">{{ company.ateco_code }}</span>
                  </span>
                  <span v-else class="muted">–</span>
                </td>
                <td :class="{ muted: company.size_class === 'unknown' }">{{ t(`size.${company.size_class}`) }}</td>
                <td class="companies__num mono" :class="{ muted: !company.beneficiary_projects }">{{ n(company.beneficiary_projects) }}</td>
                <td class="companies__num mono">
                  <span v-if="company.sole_beneficiary_funding !== null">{{ formatCurrency(company.sole_beneficiary_funding, locale) }}</span>
                  <span v-else class="muted">–</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <nav v-if="page.count > PAGE_SIZE" class="companies__pager" :aria-label="t('companies.title')">
          <span class="muted">{{ t('companies.showing', { from: n(from), to: n(to), total: n(page.count) }) }}</span>
          <div class="companies__pager-buttons">
            <button type="button" class="btn" :disabled="currentPage <= 1" @click="goTo(currentPage - 1)">
              ← {{ t('companies.previous') }}
            </button>
            <button type="button" class="btn" :disabled="to >= page.count" @click="goTo(currentPage + 1)">
              {{ t('companies.next') }} →
            </button>
          </div>
        </nav>
      </div>
    </LoadState>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { api, type CompanyListItem, type CompanySort, type Page } from '../api'
import { divisionsFor } from '../ateco'
import LoadState from '../components/LoadState.vue'
import { formatCurrency, formatNumber } from '../format'

const PAGE_SIZE = 25
const PROVINCES = ['BA', 'BT', 'BR', 'FG', 'LE', 'TA'] as const
const SECTIONS = 'ABCDEFGHIJKLMNOPQRSTU'.split('')
const THEMES = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '11', '13']
const SORTS: CompanySort[] = ['name', 'funding', 'projects']
const FILTER_KEYS = ['search', 'province', 'section', 'division', 'theme', 'funded'] as const

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const page = ref<Page<CompanyListItem> | null>(null)
const loading = ref(false)
const failed = ref(false)

const filters = computed(() => ({
  search: String(route.query.search ?? ''),
  province: String(route.query.province ?? ''),
  section: String(route.query.section ?? ''),
  division: String(route.query.division ?? ''),
  theme: String(route.query.theme ?? ''),
  funded: String(route.query.funded ?? ''),
  sort: String(route.query.sort ?? ''),
}))
const divisions = computed(() => divisionsFor(filters.value.section))
const currentPage = computed(() => Math.max(1, Number(route.query.page) || 1))
const hasFilters = computed(() => FILTER_KEYS.some((key) => filters.value[key]))
const from = computed(() => (currentPage.value - 1) * PAGE_SIZE + 1)
const to = computed(() => Math.min(currentPage.value * PAGE_SIZE, page.value?.count ?? 0))

const search = ref(filters.value.search)
let searchTimer: ReturnType<typeof setTimeout> | undefined

watch(search, (value) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => updateQuery({ search: value.trim() }), 300)
})

watch(
  () => filters.value.search,
  (value) => {
    if (value !== search.value.trim()) search.value = value
  },
)

function updateQuery(changes: Record<string, string>, keepPage = false) {
  const query: Record<string, string> = { ...filters.value, page: keepPage ? String(currentPage.value) : '', ...changes }
  router.replace({ query: Object.fromEntries(Object.entries(query).filter(([, v]) => v)) })
}

function setFilter(key: 'province' | 'division' | 'theme', event: Event) {
  updateQuery({ [key]: (event.target as HTMLSelectElement).value })
}

function setSection(event: Event) {
  updateQuery({ section: (event.target as HTMLSelectElement).value, division: '' })
}

function setFunded(event: Event) {
  updateQuery({ funded: (event.target as HTMLInputElement).checked ? 'true' : '' })
}

function setSort(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  updateQuery({ sort: value === 'name' ? '' : value })
}

function goTo(target: number) {
  updateQuery({ page: target > 1 ? String(target) : '' }, true)
}

function reset() {
  search.value = ''
  router.replace({ query: filters.value.sort ? { sort: filters.value.sort } : {} })
}

let requestId = 0

async function load() {
  const id = ++requestId
  loading.value = true
  failed.value = false
  try {
    const { funded, sort, ...rest } = filters.value
    const result = await api.companies({
      ...rest,
      funded: funded === 'true' || undefined,
      sort: (sort || undefined) as CompanySort | undefined,
      page: currentPage.value,
      page_size: PAGE_SIZE,
    })
    if (id === requestId) page.value = result
  } catch {
    if (id === requestId) failed.value = true
  } finally {
    if (id === requestId) loading.value = false
  }
}

watch(() => route.query, load, { immediate: true })

const n = (value: number) => formatNumber(value, locale.value)
</script>

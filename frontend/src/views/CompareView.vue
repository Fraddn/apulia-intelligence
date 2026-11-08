<template>
  <section class="compare">
    <PageHeader :title="t('compare.title')" :info-title="t('compare.infoTitle')" :items="INFO_KEYS.map((key) => t(`compare.${key}`))" />

    <div class="card compare__picker">
      <div class="compare__search">
        <AppIcon name="search" class="compare__search-icon" />
        <input
          ref="input"
          v-model="query"
          class="input compare__input"
          type="search"
          role="combobox"
          autocomplete="off"
          :aria-label="t('compare.searchLabel')"
          :aria-expanded="showResults"
          :aria-controls="listId"
          :aria-activedescendant="activeIndex >= 0 ? `${listId}-${activeIndex}` : undefined"
          :placeholder="full ? t('compare.full', { max: MAX }) : t('compare.searchPlaceholder')"
          :disabled="full"
          @keydown.down.prevent="move(1)"
          @keydown.up.prevent="move(-1)"
          @keydown.enter.prevent="pickActive"
          @keydown.esc="query = ''"
          @blur="closeSoon"
          @focus="focused = true"
        >
        <ul v-if="showResults" :id="listId" class="compare__results" role="listbox">
          <li v-if="searching && !results.length" class="compare__result-note muted">{{ t('common.loading') }}</li>
          <li v-else-if="!results.length" class="compare__result-note muted">{{ t('compare.noResults') }}</li>
          <li
            v-for="(company, index) in results"
            :id="`${listId}-${index}`"
            :key="company.vat_number"
            class="compare__result"
            :class="{ 'compare__result--active': index === activeIndex }"
            role="option"
            :aria-selected="index === activeIndex"
            @mousedown.prevent="add(company.vat_number)"
            @mouseenter="activeIndex = index"
          >
            <span class="compare__result-name">{{ company.name }}</span>
            <span class="meta-line">
              <span class="mono">{{ company.vat_number }}</span>
              <span v-if="company.province">{{ company.city ? `${company.city} (${company.province})` : t(`provinces.${company.province}`) }}</span>
              <span v-if="company.ateco_section">{{ t(`sections.${company.ateco_section}`) }}</span>
            </span>
          </li>
        </ul>
      </div>
      <p class="muted compare__count">{{ t('compare.selected', { count: vats.length, max: MAX }) }}</p>
    </div>

    <div v-if="!vats.length" class="card compare__empty">
      <AppIcon name="compare" :size="28" />
      <p>{{ t('compare.empty', { max: MAX }) }}</p>
    </div>

    <LoadState v-else :loading="loading && !companies.length" :error="failed" @retry="load">
      <div class="card compare__table-card" :class="{ 'compare__table-card--busy': loading }">
        <div v-if="companies.length >= 2" class="compare__toolbar">
          <label class="compare__toggle">
            <input v-model="onlyDifferences" type="checkbox">
            {{ t('compare.onlyDifferences') }}
          </label>
          <span v-if="hiddenCount" class="muted">{{ t('compare.hiddenRows', { count: hiddenCount }, hiddenCount) }}</span>
        </div>
        <div class="compare__table-wrap">
          <table class="compare__table" :style="{ '--cols': columns }">
            <thead>
              <tr>
                <th scope="col" class="compare__corner" />
                <th v-for="company in companies" :key="company.vat_number" scope="col" class="compare__company">
                  <div class="compare__company-head">
                    <span class="compare__avatar" aria-hidden="true">{{ initials(company.name) }}</span>
                    <SaveButton :vat="company.vat_number" :name="company.name" icon-only class="compare__save" />
                    <button
                      type="button"
                      class="compare__remove"
                      :aria-label="t('compare.remove', { name: company.name })"
                      :title="t('compare.remove', { name: company.name })"
                      @click="remove(company.vat_number)"
                    >
                      <AppIcon name="close" :size="16" />
                    </button>
                  </div>
                  <RouterLink :to="{ name: 'company', params: { vat: company.vat_number } }" class="compare__company-name">
                    {{ company.name }}
                  </RouterLink>
                  <span class="meta-line compare__company-meta">
                    <span class="mono">{{ company.vat_number }}</span>
                    <span v-if="company.city || company.province">{{ company.city || t(`provinces.${company.province}`) }}</span>
                  </span>
                </th>
                <th v-if="!full" scope="col" class="compare__slot">
                  <button type="button" class="compare__slot-button" @click="focusSearch">
                    <AppIcon name="plus" :size="20" />
                    <span>{{ t('compare.addCompany') }}</span>
                    <span v-if="companies.length === 1" class="muted compare__slot-hint">{{ t('compare.addAnother') }}</span>
                  </button>
                </th>
              </tr>
            </thead>
            <tbody v-for="group in visibleGroups" :key="group.title">
              <tr class="compare__group">
                <th scope="colgroup" :colspan="columns + 1">{{ group.title }}</th>
              </tr>
              <tr v-for="row in group.rows" :key="row.label" class="compare__row">
                <th scope="row" class="compare__label">{{ row.label }}</th>
                <td
                  v-for="(company, index) in companies"
                  :key="company.vat_number"
                  :class="{ 'compare__best': row.best === index, 'compare__num': row.numeric }"
                  :title="row.best === index ? t('compare.highest') : undefined"
                >
                  <template v-if="row.value(company)">
                    <span class="compare__value">
                      <a v-if="row.href?.(company)" :href="row.href(company)" target="_blank" rel="noopener">{{ row.value(company) }}</a>
                      <template v-else>{{ row.value(company) }}</template>
                      <AppIcon v-if="row.best === index" name="check" :size="16" class="compare__best-icon" />
                    </span>
                    <span v-if="row.share" class="compare__bar" :style="{ '--fill': row.share(company) }" />
                  </template>
                  <span v-else class="muted">–</span>
                </td>
                <td v-if="!full" class="compare__slot-cell" />
              </tr>
            </tbody>
            <tbody v-if="onlyDifferences && !visibleGroups.length">
              <tr>
                <td :colspan="columns + 1" class="muted compare__same">{{ t('compare.allSame') }}</td>
              </tr>
            </tbody>
            <tbody>
              <tr class="compare__group">
                <th scope="colgroup" :colspan="columns + 1">{{ t('compare.data') }}</th>
              </tr>
              <tr class="compare__row">
                <th scope="row" class="compare__label">{{ t('compare.completeness') }}</th>
                <td v-for="company in companies" :key="company.vat_number">
                  {{ t('compare.fieldsFilled', { filled: filled(company), total: fieldCount }) }}
                  <span class="compare__bar compare__bar--muted" :style="{ '--fill': completeness(company) }" />
                </td>
                <td v-if="!full" class="compare__slot-cell" />
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </LoadState>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, useId, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { api, type CompanyDetail, type CompanyListItem } from '../api'
import AppIcon from '../components/AppIcon.vue'
import LoadState from '../components/LoadState.vue'
import PageHeader from '../components/PageHeader.vue'
import SaveButton from '../components/SaveButton.vue'
import { formatCurrency, formatDate, formatNumber, isWebLink } from '../format'

interface Row {
  label: string
  value: (c: CompanyDetail) => string
  number?: (c: CompanyDetail) => number | null
  href?: (c: CompanyDetail) => string
  numeric?: boolean
  best?: number
  share?: (c: CompanyDetail) => number
}

const MAX = 4
const INFO_KEYS = ['info1', 'info2', 'info3', 'info4']

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const listId = useId()
const input = useTemplateRef<HTMLInputElement>('input')

const vats = computed(() =>
  String(route.query.vats ?? '')
    .split(',')
    .map((vat) => vat.trim())
    .filter((vat, index, all) => /^\d{11}$/.test(vat) && all.indexOf(vat) === index)
    .slice(0, MAX),
)
const full = computed(() => vats.value.length >= MAX)

const cache = new Map<string, CompanyDetail>()
const companies = ref<CompanyDetail[]>([])
const loading = ref(false)
const failed = ref(false)

async function load() {
  const wanted = vats.value
  loading.value = true
  failed.value = false
  try {
    const details = await Promise.all(
      wanted.map(async (vat) => cache.get(vat) ?? (await api.company(vat).then((c) => (cache.set(vat, c), c)))),
    )
    if (wanted.join() === vats.value.join()) companies.value = details
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}

watch(vats, load, { immediate: true })

function setVats(list: string[]) {
  router.replace({ query: list.length ? { vats: list.join(',') } : {} })
}

function add(vat: string) {
  if (!vats.value.includes(vat) && !full.value) setVats([...vats.value, vat])
  query.value = ''
  results.value = []
  input.value?.focus()
}

function remove(vat: string) {
  setVats(vats.value.filter((v) => v !== vat))
}

const query = ref('')
const results = ref<CompanyListItem[]>([])
const searching = ref(false)
const focused = ref(false)
const activeIndex = ref(-1)
const showResults = computed(() => focused.value && query.value.trim().length >= 2)
let timer: ReturnType<typeof setTimeout> | undefined
let searchId = 0

watch(query, (value) => {
  clearTimeout(timer)
  activeIndex.value = -1
  const term = value.trim()
  if (term.length < 2) {
    results.value = []
    return
  }
  searching.value = true
  timer = setTimeout(async () => {
    const id = ++searchId
    try {
      const page = await api.companies({ search: term, page_size: 8 })
      if (id === searchId) results.value = page.items.filter((c) => !vats.value.includes(c.vat_number))
    } catch {
      if (id === searchId) results.value = []
    } finally {
      if (id === searchId) searching.value = false
    }
  }, 250)
})

function move(step: number) {
  if (!results.value.length) return
  activeIndex.value = (activeIndex.value + step + results.value.length) % results.value.length
}

function pickActive() {
  const company = results.value[activeIndex.value] ?? (results.value.length === 1 ? results.value[0] : undefined)
  if (company) add(company.vat_number)
}

function closeSoon() {
  setTimeout(() => (focused.value = false), 100)
}

const n = (value: number | null) => (value === null ? '' : formatNumber(value, locale.value))
const money = (value: number | null) => (value === null ? '' : formatCurrency(value, locale.value))
const date = (value: string | null) => (value ? formatDate(value, locale.value) : '')

function hostname(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

function initials(name: string) {
  const words = name.replace(/[^\p{L}\p{N} ]/gu, ' ').split(/\s+/).filter(Boolean)
  return words.slice(0, 2).map((w) => w[0]).join('').toUpperCase() || '?'
}

function focusSearch() {
  input.value?.focus()
}

function withBest(rows: Row[]): Row[] {
  return rows.map((row) => {
    if (!row.number) return row
    const values = companies.value.map((c) => row.number!(c))
    const known = values.filter((v): v is number => v !== null && v > 0)
    const top = Math.max(...known)
    const best = known.length >= 2 && known.some((v) => v !== top) ? values.indexOf(top) : undefined
    const share = known.length >= 2 ? (c: CompanyDetail) => (row.number!(c) ?? 0) / top : undefined
    return { ...row, numeric: true, best, share }
  })
}

const groups = computed<{ title: string; rows: Row[] }[]>(() => [
  {
    title: t('company.identity'),
    rows: [
      { label: t('company.fields.legal_form'), value: (c: CompanyDetail) => c.legal_form },
      { label: t('company.fields.status'), value: (c: CompanyDetail) => (c.status === 'unknown' ? '' : t(`status.${c.status}`)) },
      { label: t('company.fields.founded_on'), value: (c: CompanyDetail) => date(c.founded_on) },
      { label: t('company.fields.size_class'), value: (c: CompanyDetail) => (c.size_class === 'unknown' ? '' : t(`size.${c.size_class}`)) },
      { label: t('company.fields.employees_band'), value: (c: CompanyDetail) => c.employees_band },
    ],
  },
  {
    title: t('company.location'),
    rows: [
      { label: t('company.fields.province'), value: (c: CompanyDetail) => (c.province ? t(`provinces.${c.province}`) : '') },
      { label: t('company.fields.city'), value: (c: CompanyDetail) => c.city },
      { label: t('company.fields.website'), value: (c: CompanyDetail) => (c.website ? hostname(c.website) : ''), href: (c: CompanyDetail) => (isWebLink(c.website) ? c.website : '') },
    ],
  },
  {
    title: t('company.activity'),
    rows: [
      {
        label: t('company.fields.ateco_section'),
        value: (c: CompanyDetail) => (c.ateco_section ? `${c.ateco_section} · ${t(`sections.${c.ateco_section}`)}` : ''),
      },
      { label: t('company.fields.ateco_code'), value: (c: CompanyDetail) => c.ateco_code },
      { label: t('company.fields.ateco_description'), value: (c: CompanyDetail) => c.ateco_description },
    ],
  },
  {
    title: t('funding.title'),
    rows: withBest([
      {
        label: t('funding.beneficiaryProjects'),
        value: (c) => (c.funding.beneficiary_projects ? n(c.funding.beneficiary_projects) : ''),
        number: (c) => c.funding.beneficiary_projects,
      },
      {
        label: t('funding.soleBeneficiaryFunding'),
        value: (c) => money(c.funding.sole_beneficiary_funding),
        number: (c) => c.funding.sole_beneficiary_funding,
      },
      {
        label: t('funding.sharedProjects'),
        value: (c) => (c.funding.shared_projects ? n(c.funding.shared_projects) : ''),
        number: (c) => c.funding.shared_projects,
      },
    ]),
  },
  {
    title: t('aid.title'),
    rows: withBest([
      { label: t('aid.grants'), value: (c) => (c.aid.count ? n(c.aid.count) : ''), number: (c) => c.aid.count },
      { label: t('aid.total'), value: (c) => money(c.aid.total_amount), number: (c) => c.aid.total_amount },
      { label: t('aid.latest'), value: (c) => date(c.aid.latest_date) },
    ]),
  },
])

const columns = computed(() => companies.value.length + (full.value ? 0 : 1))
const onlyDifferences = ref(false)

const hasData = (row: Row) => companies.value.some((c) => row.value(c))
const differs = (row: Row) => new Set(companies.value.map((c) => row.value(c))).size > 1
const shown = (row: Row) => hasData(row) && (!onlyDifferences.value || companies.value.length < 2 || differs(row))

const visibleGroups = computed(() =>
  groups.value.map((group) => ({ ...group, rows: group.rows.filter(shown) })).filter((group) => group.rows.length),
)

const hiddenCount = computed(() =>
  onlyDifferences.value ? groups.value.flatMap((group) => group.rows).filter((row) => hasData(row) && !differs(row)).length : 0,
)

const fieldCount = computed(() => groups.value.reduce((sum, group) => sum + group.rows.length, 0))

function filled(company: CompanyDetail) {
  return groups.value.reduce((sum, group) => sum + group.rows.filter((row) => row.value(company)).length, 0)
}

function completeness(company: CompanyDetail) {
  return fieldCount.value ? filled(company) / fieldCount.value : 0
}
</script>

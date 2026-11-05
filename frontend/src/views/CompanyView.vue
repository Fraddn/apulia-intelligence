<template>
  <section class="company">
    <RouterLink :to="{ name: 'companies' }" class="company__back">← {{ t('company.back') }}</RouterLink>
    <LoadState
      :loading="loading"
      :error="failed"
      :message="notFound ? t('company.notFound') : undefined"
      :retryable="!notFound"
      @retry="load"
    >
      <template v-if="company">
        <header class="card company__header">
          <h1 class="company__name">{{ company.name }}</h1>
          <div class="company__chips">
            <span class="chip mono">{{ t('company.fields.vat_number') }} {{ company.vat_number }}</span>
            <span v-if="company.province" class="chip">{{ t(`provinces.${company.province}`) }}</span>
            <span v-if="company.ateco_section" class="chip">
              {{ company.ateco_section }} · {{ t(`sections.${company.ateco_section}`) }}
            </span>
          </div>
        </header>

        <div class="company__groups">
          <article v-for="group in groups" :key="group.title" class="card">
            <h2 class="company__group-title">{{ group.title }}</h2>
            <dl class="company__fields">
              <div v-for="row in group.rows" :key="row.field" class="company__row">
                <dt class="company__term">{{ t(`company.fields.${row.field}`) }}</dt>
                <dd class="company__value">
                  <a v-if="row.href && row.value" :href="row.href" target="_blank" rel="noopener">{{ row.value }}</a>
                  <span v-else-if="row.value">{{ row.value }}</span>
                  <span v-else class="muted">{{ t('common.notAvailable') }}</span>
                  <span v-if="row.provenance" class="company__source">
                    <AssuranceBadge :assurance="row.provenance.assurance" />
                    <span class="muted">
                      {{ row.provenance.source.name }} · {{ formatDate(row.provenance.data_date, locale) }}
                      <template v-if="row.provenance.confidence !== null">
                        · {{ t('company.confidence', { value: pct(row.provenance.confidence) }) }}
                      </template>
                    </span>
                    <span v-if="row.note" class="muted company__source-note">{{ row.note }}</span>
                    <span v-if="showRaw(row)" class="muted company__source-note">
                      {{ t('company.rawValue', { value: row.provenance.raw_value }) }}
                    </span>
                  </span>
                </dd>
              </div>
            </dl>
          </article>

          <article class="card">
            <h2 class="company__group-title">{{ t('company.sources') }}</h2>
            <p class="muted company__hint">{{ t('company.sourcesHint') }}</p>
            <ul class="company__sources">
              <li v-for="source in sources" :key="source.name">
                <a v-if="source.url" :href="source.url" target="_blank" rel="noopener">{{ source.name }}</a>
                <span v-else>{{ source.name }}</span>
                <span v-if="source.licence" class="muted"> · {{ source.licence }}</span>
                <span v-if="source.attribution" class="muted"> · {{ source.attribution }}</span>
              </li>
            </ul>
          </article>
        </div>

        <article class="card company__funding">
          <h2 class="company__group-title">{{ t('funding.title') }}</h2>
          <template v-if="company.projects_total">
            <div class="company__funding-tiles">
              <StatTile :label="t('funding.beneficiaryProjects')" :value="formatNumber(company.funding.beneficiary_projects, locale)" />
              <StatTile
                :label="t('funding.soleBeneficiaryFunding')"
                :value="company.funding.sole_beneficiary_funding === null ? '–' : formatCurrency(company.funding.sole_beneficiary_funding, locale)"
                :hint="t('funding.soleBeneficiary') + ': ' + formatNumber(company.funding.sole_beneficiary_projects, locale)"
              />
              <StatTile
                :label="t('funding.sharedProjects')"
                :value="formatNumber(company.funding.shared_projects, locale)"
                :hint="t('funding.sharedProjectsHint')"
              />
            </div>
            <p class="muted company__hint">{{ t('funding.rule') }}</p>
            <p v-if="otherRoles" class="company__hint">{{ t('funding.otherRoles', { roles: otherRoles }) }}</p>
            <ProjectList :projects="company.projects" :total="company.projects_total" />
          </template>
          <p v-else class="muted company__hint">{{ t('funding.none') }}</p>
        </article>
      </template>
    </LoadState>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ApiError, api, type CompanyDetail, type Provenance, type Source } from '../api'
import AssuranceBadge from '../components/AssuranceBadge.vue'
import LoadState from '../components/LoadState.vue'
import ProjectList from '../components/ProjectList.vue'
import StatTile from '../components/StatTile.vue'
import { formatCurrency, formatDate, formatNumber } from '../format'

interface Row {
  field: string
  value: string
  provenance?: Provenance
  href?: string
  note?: string
}

const props = defineProps<{ vat: string }>()

const { t, locale } = useI18n()
const company = ref<CompanyDetail | null>(null)
const loading = ref(true)
const failed = ref(false)
const notFound = ref(false)

async function load() {
  loading.value = true
  failed.value = false
  notFound.value = false
  try {
    company.value = await api.company(props.vat)
  } catch (error) {
    failed.value = true
    notFound.value = error instanceof ApiError && error.status === 404
  } finally {
    loading.value = false
  }
}

watch(() => props.vat, load, { immediate: true })

const pct = (value: number) =>
  new Intl.NumberFormat(locale.value, { style: 'percent', maximumFractionDigits: 0 }).format(value)

const provenance = computed(() => new Map(company.value?.provenance.map((p) => [p.field, p]) ?? []))

function makeRow(field: keyof CompanyDetail, value: string, extra: Partial<Row> = {}): Row {
  return { field, value, provenance: provenance.value.get(field), ...extra }
}

const groups = computed(() => {
  const c = company.value
  if (!c) return []
  const derivedProvince = provenance.value.get('province')?.assurance === 'derived'
  return [
    {
      title: t('company.identity'),
      rows: [
        makeRow('vat_number', c.vat_number),
        makeRow('tax_code', c.tax_code),
        makeRow('legal_form', c.legal_form),
        makeRow('status', c.status === 'unknown' ? '' : t(`status.${c.status}`)),
        makeRow('founded_on', c.founded_on ? formatDate(c.founded_on, locale.value) : ''),
      ],
    },
    {
      title: t('company.activity'),
      rows: [
        makeRow('ateco_section', c.ateco_section ? `${c.ateco_section} · ${t(`sections.${c.ateco_section}`)}` : ''),
        makeRow('ateco_code', c.ateco_code),
        makeRow('ateco_description', c.ateco_description),
        makeRow('ateco_version', c.ateco_version),
      ],
    },
    {
      title: t('company.location'),
      rows: [
        makeRow('province', c.province ? t(`provinces.${c.province}`) : '', {
          note: derivedProvince ? t('company.derivedProvince') : undefined,
        }),
        makeRow('municipality_code', c.municipality_code),
        makeRow('address', c.address),
        makeRow('postcode', c.postcode),
        makeRow('website', c.website, { href: c.website }),
      ],
    },
    {
      title: t('company.size'),
      rows: [
        makeRow('size_class', c.size_class === 'unknown' ? '' : t(`size.${c.size_class}`)),
        makeRow('employees_band', c.employees_band),
      ],
    },
  ]
})

function showRaw(r: Row) {
  const raw = r.provenance?.raw_value
  if (!raw || r.note) return false
  return raw !== r.value && raw.replace(/\s+/g, ' ').trim() !== r.value
}

const otherRoles = computed(() =>
  Object.entries(company.value?.funding.roles ?? {})
    .filter(([role, count]) => role !== 'beneficiary' && count)
    .map(([role, count]) => `${t(`funding.roles.${role}`)} (${formatNumber(count ?? 0, locale.value)})`)
    .join(', '),
)

const sources = computed(() => {
  const unique = new Map<string, Source>()
  company.value?.provenance.forEach((p) => unique.set(p.source.name, p.source))
  return [...unique.values()]
})
</script>

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
          <div class="company__title-row">
            <h1 class="company__name">{{ company.name }}</h1>
            <div class="company__actions">
              <SaveButton :vat="company.vat_number" :name="company.name" />
              <RouterLink :to="{ name: 'compare', query: { vats: company.vat_number } }" class="btn btn--small btn--round">
                <AppIcon name="compare" :size="16" />
                {{ t('company.compare') }}
              </RouterLink>
            </div>
          </div>
          <p class="meta-line company__meta">
            <span class="mono">{{ t('company.fields.vat_number') }} {{ company.vat_number }}</span>
            <span v-if="company.province">{{ company.city ? `${company.city} (${company.province})` : t(`provinces.${company.province}`) }}</span>
            <span v-if="company.ateco_section">{{ t(`sections.${company.ateco_section}`) }}</span>
            <a v-if="isWebLink(company.website)" :href="company.website" target="_blank" rel="noopener">{{ hostname(company.website) }}</a>
          </p>
          <dl v-if="facts.length" class="company__facts">
            <div v-for="fact in facts" :key="fact.label" class="company__fact">
              <dt class="company__fact-label">{{ fact.label }}</dt>
              <dd class="company__fact-value">{{ fact.value }}</dd>
            </div>
          </dl>
        </header>

        <div class="company__groups">
          <article v-for="group in groups" :key="group.title" class="card">
            <h2 class="company__group-title">{{ group.title }}</h2>
            <p v-if="group.main" class="meta-line company__card-source">
              <span>{{ t('company.sourceUnlessNoted') }}</span>
              <AssuranceBadge :assurance="group.main.assurance" />
              <span>{{ group.main.source.name }}</span>
              <span>{{ formatDate(group.main.data_date, locale) }}</span>
            </p>
            <template v-if="group.key === 'location'">
              <DiscoveryStatus :searching="discovering" :discovery="discovery" />
              <WebsiteStatus :check="company.website_check" />
            </template>
            <dl v-if="group.rows.length" class="company__fields">
              <div v-for="row in group.rows" :key="row.field" class="company__row">
                <dt class="company__term">{{ t(`company.fields.${row.field}`) }}</dt>
                <dd class="company__value">
                  <a v-if="row.href" :href="row.href" :title="row.title" :target="row.href.startsWith('http') ? '_blank' : undefined" rel="noopener">{{ row.value }}</a>
                  <span v-else :title="row.title">{{ row.value }}</span>
                  <span v-if="row.ownSource && row.provenance" class="company__source">
                    <AssuranceBadge :assurance="row.provenance.assurance" />
                    <span class="muted">
                      {{ row.provenance.source.name }} · {{ formatDate(row.provenance.data_date, locale) }}
                      <template v-if="row.provenance.confidence !== null">
                        · {{ t('company.confidence', { value: pct(row.provenance.confidence) }) }}
                      </template>
                    </span>
                    <span v-if="row.note" class="muted company__source-note">{{ row.note }}</span>
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

        <article class="card company__funding">
          <h2 class="company__group-title">{{ t('aid.title') }}</h2>
          <template v-if="company.aid.count">
            <div class="company__funding-tiles">
              <StatTile :label="t('aid.grants')" :value="formatNumber(company.aid.count, locale)" />
              <StatTile
                :label="t('aid.total')"
                :value="company.aid.total_amount === null ? '–' : formatCurrency(company.aid.total_amount, locale)"
              />
              <StatTile :label="t('aid.latest')" :value="formatDate(company.aid.latest_date, locale)" />
            </div>
            <p class="muted company__hint">{{ t('aid.rule') }}</p>
            <AidList :items="company.aid.items" :total="company.aid.count" />
          </template>
          <p v-else class="muted company__hint">{{ t('aid.none') }}</p>
        </article>
      </template>
    </LoadState>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ApiError, api, type CompanyDetail, type Discovery, type Provenance, type Source } from '../api'
import AidList from '../components/AidList.vue'
import AppIcon from '../components/AppIcon.vue'
import AssuranceBadge from '../components/AssuranceBadge.vue'
import DiscoveryStatus from '../components/DiscoveryStatus.vue'
import LoadState from '../components/LoadState.vue'
import ProjectList from '../components/ProjectList.vue'
import SaveButton from '../components/SaveButton.vue'
import StatTile from '../components/StatTile.vue'
import WebsiteStatus from '../components/WebsiteStatus.vue'
import { formatCurrency, formatDate, formatNumber, isWebLink } from '../format'

interface Row {
  field: string
  value: string
  provenance?: Provenance
  href?: string
  note?: string
  title?: string
  ownSource?: boolean
}

const props = defineProps<{ vat: string }>()

const { t, locale } = useI18n()
const company = ref<CompanyDetail | null>(null)
const loading = ref(true)
const failed = ref(false)
const notFound = ref(false)

const discovering = ref(false)
const discovery = ref<Discovery | null>(null)

async function discoverWebsite(vat: string) {
  discovering.value = true
  try {
    const result = await api.discover(vat)
    if (props.vat !== vat) return
    discovery.value = result.discovery
    company.value = result.company
  } catch {
    discovery.value = null
  } finally {
    discovering.value = false
  }
}

async function load() {
  loading.value = true
  failed.value = false
  notFound.value = false
  discovery.value = null
  try {
    company.value = await api.company(props.vat)
    if (!company.value.website_check) discoverWebsite(props.vat)
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

function hostname(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

const provenance = computed(() => new Map(company.value?.provenance.map((p) => [p.field, p]) ?? []))

function rawTitle(value: string, p?: Provenance) {
  const raw = p?.raw_value
  if (!raw || raw === value || raw.replace(/\s+/g, ' ').trim() === value) return undefined
  return t('company.rawValue', { value: raw })
}

function makeRow(field: keyof CompanyDetail, value: string, extra: Partial<Row> = {}): Row {
  const p = provenance.value.get(field)
  const title = [rawTitle(value, p), extra.title].filter(Boolean).join('\n') || undefined
  return { field, value, provenance: p, ...extra, title }
}

const sourceKey = (p: Provenance) => `${p.source.name}|${p.assurance}|${p.data_date}`

function withSharedSource(rows: Row[]) {
  const counts = new Map<string, { count: number; provenance: Provenance }>()
  for (const row of rows) {
    if (!row.provenance || row.provenance.confidence !== null) continue
    const key = sourceKey(row.provenance)
    const entry = counts.get(key) ?? { count: 0, provenance: row.provenance }
    entry.count += 1
    counts.set(key, entry)
  }
  const main = [...counts.values()].sort((a, b) => b.count - a.count)[0]?.provenance
  const mainKey = main ? sourceKey(main) : ''
  return {
    main,
    rows: rows.map((row) => ({
      ...row,
      ownSource: Boolean(row.provenance) && (row.provenance!.confidence !== null || sourceKey(row.provenance!) !== mainKey || Boolean(row.note)),
    })),
  }
}

const groups = computed(() => {
  const c = company.value
  if (!c) return []
  const derivedProvince = provenance.value.get('province')?.assurance === 'derived'
  const all = [
    {
      key: 'identity',
      title: t('company.identity'),
      rows: [
        makeRow('legal_form', c.legal_form),
        makeRow('status', c.status === 'unknown' ? '' : t(`status.${c.status}`)),
        makeRow('founded_on', c.founded_on ? formatDate(c.founded_on, locale.value) : ''),
        makeRow('size_class', c.size_class === 'unknown' ? '' : t(`size.${c.size_class}`)),
        makeRow('employees_band', c.employees_band),
        makeRow('tax_code', c.tax_code === c.vat_number ? '' : c.tax_code),
      ],
    },
    {
      key: 'activity',
      title: t('company.activity'),
      rows: [
        makeRow('ateco_code', c.ateco_code ? [c.ateco_section, c.ateco_code].filter(Boolean).join(' · ') : '', {
          title: c.ateco_version ? t('company.atecoVersion', { version: c.ateco_version }) : undefined,
        }),
        makeRow('ateco_description', c.ateco_description),
      ],
    },
    {
      key: 'location',
      title: t('company.location'),
      rows: [
        makeRow('province', c.province ? t(`provinces.${c.province}`) : '', {
          note: derivedProvince ? t('company.derivedProvince') : undefined,
        }),
        makeRow('city', c.city, {
          title: c.municipality_code ? t('company.istatCode', { code: c.municipality_code }) : undefined,
        }),
        makeRow('address', c.address),
        makeRow('postcode', c.postcode),
        makeRow('website', c.website, { href: isWebLink(c.website) ? c.website : undefined }),
        makeRow('phone', c.phone, { href: c.phone ? `tel:${c.phone.replace(/\s+/g, '')}` : undefined }),
        makeRow('email', c.email, { href: c.email ? `mailto:${c.email}` : undefined }),
        makeRow('pec', c.pec, { href: c.pec ? `mailto:${c.pec}` : undefined }),
      ],
    },
  ]
  return all
    .map((group) => ({ ...group, ...withSharedSource(group.rows.filter((row) => row.value)) }))
    .filter((group) => group.rows.length || group.key === 'location')
})

const facts = computed(() => {
  const c = company.value
  if (!c) return []
  const items = [
    { label: t('company.fields.size_class'), value: c.size_class === 'unknown' ? '' : t(`size.${c.size_class}`) },
    { label: t('company.fields.employees_band'), value: c.employees_band },
    { label: t('company.fields.founded_on'), value: c.founded_on ? c.founded_on.slice(0, 4) : '' },
    {
      label: t('funding.beneficiaryProjects'),
      value: c.funding.beneficiary_projects ? formatNumber(c.funding.beneficiary_projects, locale.value) : '',
    },
    {
      label: t('funding.soleBeneficiaryFunding'),
      value: c.funding.sole_beneficiary_funding === null ? '' : formatCurrency(c.funding.sole_beneficiary_funding, locale.value),
    },
    {
      label: t('aid.total'),
      value: c.aid.count && c.aid.total_amount !== null ? formatCurrency(c.aid.total_amount, locale.value) : '',
    },
  ]
  return items.filter((item) => item.value)
})

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

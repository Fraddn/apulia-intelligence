<template>
  <section class="glossary">
    <PageHeader :title="t('glossary.title')" :info-title="t('glossary.infoTitle')" :items="INFO_KEYS.map((key) => t(`glossary.${key}`))">
      <template #after>
        <span class="muted glossary__count">{{ t('glossary.results', { count: matchCount }, matchCount) }}</span>
      </template>
    </PageHeader>

    <div class="glossary__layout">
      <nav class="card glossary__toc" :aria-label="t('glossary.contents')">
        <h2 class="glossary__toc-title">{{ t('glossary.contents') }}</h2>
        <ul class="glossary__toc-list">
          <li v-for="group in groups" :key="group.key">
            <RouterLink
              :to="{ hash: `#group-${group.key}` }"
              class="glossary__toc-link"
              :class="{ 'glossary__toc-link--empty': !group.terms.length }"
            >
              <span>{{ t(`glossary.groups.${group.key}`) }}</span>
              <span class="glossary__toc-count">{{ group.terms.length }}</span>
            </RouterLink>
          </li>
        </ul>
      </nav>

      <div class="glossary__main">
        <div class="card glossary__search">
          <AppIcon name="search" class="glossary__search-icon" />
          <input
            v-model="query"
            class="input glossary__search-input"
            type="search"
            :aria-label="t('glossary.searchLabel')"
            :placeholder="t('glossary.searchPlaceholder')"
          >
        </div>

        <p v-if="!matchCount" class="card glossary__none muted">{{ t('glossary.noResults', { query: query.trim() }) }}</p>

        <section
          v-for="group in groups.filter((g) => g.terms.length)"
          :id="`group-${group.key}`"
          :key="group.key"
          class="glossary__group"
          :aria-labelledby="`group-${group.key}-title`"
        >
          <h2 :id="`group-${group.key}-title`" class="glossary__group-title">{{ t(`glossary.groups.${group.key}`) }}</h2>
          <dl class="glossary__terms">
            <div v-for="term in group.terms" :id="`term-${term.key}`" :key="term.key" class="card glossary__term">
              <dt class="glossary__term-name">
                <template v-for="(part, index) in highlight(term.name)" :key="index">
                  <mark v-if="part.match">{{ part.text }}</mark>
                  <template v-else>{{ part.text }}</template>
                </template>
              </dt>
              <dd class="glossary__aka">
                <template v-for="(part, index) in highlight(term.aka)" :key="index">
                  <mark v-if="part.match">{{ part.text }}</mark>
                  <template v-else>{{ part.text }}</template>
                </template>
              </dd>
              <dd class="glossary__text">
                <template v-for="(part, index) in highlight(term.text)" :key="index">
                  <mark v-if="part.match">{{ part.text }}</mark>
                  <template v-else>{{ part.text }}</template>
                </template>
              </dd>
            </div>
          </dl>
        </section>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'

const INFO_KEYS = ['info1', 'info2']
const GROUPS: Record<string, string[]> = {
  identity: ['vat', 'taxCode', 'legalForm', 'status', 'size', 'sme', 'employees'],
  activity: ['ateco', 'section', 'atecoCode', 'atecoVersion', 'nace'],
  location: ['province', 'bat', 'istat', 'municipalityCode', 'postcode', 'pec'],
  funding: ['opencoesione', 'cohesion', 'project', 'cup', 'beneficiary', 'implementer', 'contractor', 'programmer', 'soleFunding', 'shared', 'cycle', 'theme'],
  aid: ['rna', 'stateAid', 'grant', 'aidElement', 'cor', 'deMinimis', 'exemption', 'grantingBody'],
  quality: ['source', 'dataDate', 'licence', 'assurance', 'official', 'fromCompany', 'derived', 'inferred', 'manual', 'confidence', 'website', 'missing'],
  app: ['completeness', 'library', 'compare'],
}

const { t } = useI18n()
const query = ref('')

const fold = (text: string) => text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

const groups = computed(() => {
  const term = fold(query.value.trim())
  return Object.entries(GROUPS).map(([key, keys]) => ({
    key,
    terms: keys
      .map((k) => ({
        key: k,
        name: t(`glossary.terms.${k}.term`),
        aka: t(`glossary.terms.${k}.aka`),
        text: t(`glossary.terms.${k}.text`),
      }))
      .filter((item) => !term || [item.name, item.aka, item.text].some((value) => fold(value).includes(term))),
  }))
})

const matchCount = computed(() => groups.value.reduce((sum, group) => sum + group.terms.length, 0))

function highlight(text: string): { text: string; match: boolean }[] {
  const term = fold(query.value.trim())
  if (!term) return [{ text, match: false }]
  const folded = fold(text)
  const parts: { text: string; match: boolean }[] = []
  let start = 0
  let index = folded.indexOf(term)
  while (index !== -1) {
    if (index > start) parts.push({ text: text.slice(start, index), match: false })
    parts.push({ text: text.slice(index, index + term.length), match: true })
    start = index + term.length
    index = folded.indexOf(term, start)
  }
  if (start < text.length) parts.push({ text: text.slice(start), match: false })
  return parts
}
</script>

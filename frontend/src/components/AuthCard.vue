<template>
  <div class="auth">
    <aside class="auth__brand">
      <div class="auth__logo">
        <span class="auth__mark"><BrandMark :size="26" /></span>
        <span class="auth__name">Puglia<span class="auth__name-accent">Imprese</span></span>
      </div>
      <div class="auth__pitch">
        <p class="auth__headline">{{ t('authBrand.headline') }}</p>
        <p class="auth__lead">{{ t('authBrand.lead') }}</p>
        <ul class="auth__features">
          <li v-for="key in FEATURES" :key="key">
            <AppIcon name="check" :size="18" />
            {{ t(`authBrand.${key}`) }}
          </li>
        </ul>
      </div>
      <dl v-if="summary" class="auth__stats">
        <div v-for="stat in stats" :key="stat.key" class="auth__stat">
          <dt>{{ t(`authBrand.${stat.key}`) }}</dt>
          <dd><AnimatedNumber :value="stat.value" :format="(value) => formatNumber(Math.round(value), locale)" /></dd>
        </div>
      </dl>
      <i18n-t keypath="footer.attribution" tag="p" scope="global" class="auth__attribution">
        <template #sources>
          <a href="https://opencoesione.gov.it/it/opendata/" target="_blank" rel="noopener">OpenCoesione</a>
          (CC BY 4.0)
        </template>
      </i18n-t>
    </aside>
    <main id="main" class="auth__main">
      <div class="auth__tools">
        <LanguageSwitch />
        <ThemeToggle />
      </div>
      <section class="auth__panel">
        <span class="auth__icon" aria-hidden="true"><AppIcon :name="icon" :size="22" /></span>
        <h1 class="auth__title">{{ title }}</h1>
        <p v-if="subtitle" class="auth__subtitle">{{ subtitle }}</p>
        <slot />
        <p v-if="$slots.footer" class="auth__footer">
          <slot name="footer" />
        </p>
      </section>
    </main>
  </div>
</template>

<script lang="ts">
import { ref } from 'vue'
import { api, type Summary } from '../api'

const summary = ref<Summary | null>(null)
let requested = false

function loadSummary() {
  if (requested) return
  requested = true
  api.summary().then(
    (value) => (summary.value = value),
    () => (requested = false),
  )
}
</script>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatNumber } from '../format'
import AnimatedNumber from './AnimatedNumber.vue'
import AppIcon, { type IconName } from './AppIcon.vue'
import BrandMark from './BrandMark.vue'
import LanguageSwitch from './LanguageSwitch.vue'
import ThemeToggle from './ThemeToggle.vue'

withDefaults(defineProps<{ title: string; subtitle?: string; icon?: IconName }>(), { subtitle: '', icon: 'lock' })

const FEATURES = ['feature1', 'feature2', 'feature3']

const { t, locale } = useI18n()

const stats = computed(() =>
  summary.value
    ? [
        { key: 'companies', value: summary.value.companies },
        { key: 'fundedProjects', value: summary.value.funded_projects },
        { key: 'aidGrants', value: summary.value.aid_grants },
      ]
    : [],
)

onMounted(loadSummary)
</script>

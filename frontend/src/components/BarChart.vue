<template>
  <figure class="bar-chart">
    <figcaption class="bar-chart__caption">
      <h2 class="bar-chart__title">{{ title }}</h2>
      <p v-if="subtitle" class="bar-chart__subtitle muted">{{ subtitle }}</p>
    </figcaption>
    <ul class="bar-chart__rows">
      <li
        v-for="(item, index) in items"
        :key="item.key"
        class="bar-chart__row"
        :class="{ 'bar-chart__row--selected': selected === item.key, 'bar-chart__row--dim': selected && selected !== item.key }"
      >
        <component
          :is="item.to ? RouterLink : 'div'"
          :to="item.to"
          class="bar-chart__hit"
          :tabindex="item.to ? undefined : 0"
          :aria-label="`${item.label}: ${format(item.value)} (${share(item.value)})`"
          @mouseenter="active = item.key"
          @mouseleave="active = null"
          @focus="active = item.key"
          @blur="active = null"
        >
          <span class="bar-chart__label">{{ item.label }}</span>
          <span class="bar-chart__track">
            <span class="bar-chart__bar" :style="{ '--i': index, width: `calc((100% - var(--value-space)) * ${ratio(item.value)})` }" />
            <span class="bar-chart__value">{{ format(item.value) }}</span>
          </span>
        </component>
        <span
          v-if="active === item.key"
          class="bar-chart__tooltip"
          role="tooltip"
          :style="{ left: `calc((100% - var(--value-space)) * ${ratio(item.value)})` }"
          :class="{ 'bar-chart__tooltip--flip': ratio(item.value) > 0.6 }"
        >
          <strong>{{ item.label }}</strong>
          <span>{{ format(item.value) }} · {{ share(item.value) }}</span>
        </span>
      </li>
    </ul>
  </figure>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, type RouteLocationRaw } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { formatNumber, formatPercent } from '../format'

export interface BarItem {
  key: string
  label: string
  value: number
  to?: RouteLocationRaw
}

const props = defineProps<{
  title: string
  subtitle?: string
  items: BarItem[]
  total?: number
  selected?: string
}>()

const { locale } = useI18n()
const active = ref<string | null>(null)

const max = computed(() => Math.max(1, ...props.items.map((item) => item.value)))
const total = computed(() => props.total ?? props.items.reduce((sum, item) => sum + item.value, 0))

function ratio(value: number) {
  return value / max.value
}

function format(value: number) {
  return formatNumber(value, locale.value)
}

function share(value: number) {
  return formatPercent(value, total.value, locale.value)
}
</script>

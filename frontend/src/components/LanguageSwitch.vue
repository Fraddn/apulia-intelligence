<template>
  <div class="lang-switch" role="group" :aria-label="t('settings.language')">
    <button
      v-for="code in LOCALES"
      :key="code"
      type="button"
      class="lang-switch__option"
      :class="{ 'lang-switch__option--active': locale === code }"
      :aria-pressed="locale === code"
      :lang="code"
      @click="setLocale(code)"
    >
      {{ code.toUpperCase() }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { LOCALES, setLocale } from '../i18n'

const { t, locale } = useI18n()
</script>

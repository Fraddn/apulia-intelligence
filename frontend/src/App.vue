<template>
  <a class="skip-link" href="#main">{{ t('app.skipToContent') }}</a>
  <RouterView v-if="route.meta.public" />
  <template v-else>
    <AppHeader />
    <main id="main" class="app-main">
      <RouterView />
    </main>
    <footer class="app-footer">
      <i18n-t keypath="footer.attribution" tag="p" scope="global">
        <template #sources>
          <a href="https://opencoesione.gov.it/it/opendata/" target="_blank" rel="noopener">OpenCoesione</a>
          (CC BY 4.0)
        </template>
      </i18n-t>
    </footer>
  </template>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import AppHeader from './components/AppHeader.vue'

const { t } = useI18n()
const route = useRoute()
</script>

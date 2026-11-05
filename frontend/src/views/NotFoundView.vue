<template>
  <section class="card not-found">
    <h1 class="page-title">{{ t('notFound.title') }}</h1>
    <RouterLink to="/" class="btn btn--primary">{{ t('notFound.home') }}</RouterLink>
  </section>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

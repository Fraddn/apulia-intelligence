<template>
  <header class="page-header">
    <div class="page-header__row">
      <h1 class="page-title">{{ title }}</h1>
      <button
        type="button"
        class="page-header__info"
        :class="{ 'page-header__info--open': open }"
        :aria-expanded="open"
        :aria-controls="panelId"
        :aria-label="t('info.toggle')"
        :title="t('info.toggle')"
        @click="open = !open"
      >
        <AppIcon name="info" :size="20" />
      </button>
      <slot name="after" />
    </div>
    <Transition name="reveal">
      <section v-if="open" :id="panelId" class="card page-header__panel">
        <div class="page-header__panel-head">
          <h2 class="page-header__panel-title">{{ infoTitle }}</h2>
          <button type="button" class="page-header__close" :aria-label="t('info.close')" :title="t('info.close')" @click="open = false">
            <AppIcon name="close" :size="18" />
          </button>
        </div>
        <ul class="page-header__list">
          <li v-for="item in items" :key="item">{{ item }}</li>
        </ul>
      </section>
    </Transition>
  </header>
</template>

<script setup lang="ts">
import { ref, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import AppIcon from './AppIcon.vue'

defineProps<{ title: string; infoTitle: string; items: string[] }>()

const { t } = useI18n()
const open = ref(false)
const panelId = useId()
</script>

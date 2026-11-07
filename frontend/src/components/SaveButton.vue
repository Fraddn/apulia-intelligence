<template>
  <button
    type="button"
    class="btn btn--small btn--round save-button"
    :class="{ 'save-button--saved': saved, 'save-button--icon': iconOnly, 'save-button--failed': failed }"
    :aria-pressed="saved"
    :aria-label="label"
    :title="failed ? t('library.saveFailed') : label"
    :disabled="busy"
    @click="toggle"
  >
    <AppIcon name="bookmark" :size="16" />
    <span v-if="!iconOnly">{{ saved ? t('library.saved') : t('library.save') }}</span>
  </button>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLibrary } from '../library'
import AppIcon from './AppIcon.vue'

const props = withDefaults(defineProps<{ vat: string; name?: string; iconOnly?: boolean }>(), { name: '', iconOnly: false })

const { t } = useI18n()
const library = useLibrary()
const failed = ref(false)

const saved = computed(() => library.savedVats.value.has(props.vat))
const busy = computed(() => library.pending.value.has(props.vat))
const label = computed(() =>
  saved.value ? t('library.removeNamed', { name: props.name || props.vat }) : t('library.saveNamed', { name: props.name || props.vat }),
)

onMounted(() => library.load())

async function toggle() {
  failed.value = false
  try {
    await library.toggle(props.vat)
  } catch {
    failed.value = true
  }
}
</script>

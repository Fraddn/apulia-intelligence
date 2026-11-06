<template>
  <div class="stat-tile card">
    <span class="stat-tile__label">{{ label }}</span>
    <span class="stat-tile__value">{{ value }}</span>
    <span v-if="hint" class="stat-tile__hint">{{ hint }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string
  value: string
  hint?: string
}>()
</script>

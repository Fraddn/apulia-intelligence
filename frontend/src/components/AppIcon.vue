<template>
  <svg
    class="icon"
    viewBox="0 0 24 24"
    :width="size"
    :height="size"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path v-for="(d, index) in ICONS[name]" :key="index" :d="d" />
  </svg>
</template>

<script setup lang="ts">
type IconName = 'dashboard' | 'companies' | 'user' | 'logout' | 'login' | 'sun' | 'moon' | 'info' | 'close'

const ICONS: Record<IconName, string[]> = {
  dashboard: ['M4 4h6v8H4z', 'M14 4h6v5h-6z', 'M14 13h6v7h-6z', 'M4 16h6v4H4z'],
  companies: ['M6 21V5a1 1 0 0 1 1-1h7a1 1 0 0 1 1 1v16', 'M15 9h3a1 1 0 0 1 1 1v11', 'M3 21h18', 'M9 8h2', 'M9 12h2', 'M9 16h2'],
  user: ['M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', 'M4 21a8 8 0 0 1 16 0'],
  logout: ['M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4', 'M16 17l5-5-5-5', 'M21 12H9'],
  login: ['M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4', 'M10 17l5-5-5-5', 'M15 12H3'],
  sun: ['M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z', 'M12 2v2', 'M12 20v2', 'M4.9 4.9l1.4 1.4', 'M17.7 17.7l1.4 1.4', 'M2 12h2', 'M20 12h2', 'M4.9 19.1l1.4-1.4', 'M17.7 6.3l1.4-1.4'],
  moon: ['M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z'],
  info: ['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z', 'M12 16v-5', 'M12 8h.01'],
  close: ['M6 6l12 12', 'M18 6L6 18'],
}

withDefaults(defineProps<{ name: IconName; size?: number }>(), { size: 18 })
</script>

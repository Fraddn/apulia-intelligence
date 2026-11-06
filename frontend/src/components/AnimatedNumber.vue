<template>
  <span class="animated-number">{{ format(shown) }}</span>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(defineProps<{ value: number; format: (value: number) => string; duration?: number }>(), {
  duration: 700,
})

const shown = ref(props.value)
let frame = 0

function animated() {
  if (typeof requestAnimationFrame === 'undefined' || typeof matchMedia === 'undefined') return false
  return !matchMedia('(prefers-reduced-motion: reduce)').matches
}

function run(from: number, to: number) {
  if (!animated() || from === to) {
    shown.value = to
    return
  }
  cancelAnimationFrame(frame)
  shown.value = from
  const start = performance.now()
  const step = (now: number) => {
    const progress = Math.min(1, (now - start) / props.duration)
    const eased = 1 - Math.pow(1 - progress, 3)
    shown.value = progress < 1 ? from + (to - from) * eased : to
    if (progress < 1) frame = requestAnimationFrame(step)
  }
  frame = requestAnimationFrame(step)
}

run(0, props.value)
watch(() => props.value, (to) => run(shown.value, to))
onBeforeUnmount(() => {
  if (frame) cancelAnimationFrame(frame)
})
</script>

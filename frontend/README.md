# Frontend

Vue 3 + Vite + TypeScript, Vue Router, vue-i18n.

```bash
npm install
npm run dev        # http://localhost:5173, proxies /api to Django on :8000
npm run check      # lint + type-check + tests
npm run build      # production build in dist/
```

## Conventions

- Single-file components: `<template>` first, then `<script setup lang="ts">`.
- **All CSS lives in one unscoped `<style>` block in `src/App.vue`**: theme tokens (light/dark, orange accent) plus component styles. Class names are prefixed per component (`.bar-chart__bar`, `.companies__table`). No other component has a `<style>` block, no `scoped`, and there are no CSS files.
- **Minimum font size is 14px** (body 15px); font sizes are in `px` only. `src/__tests__/typography.spec.ts` enforces it.
- ESLint enforces this (`npm run lint`): `vue/block-order` (template before script), `vue/enforce-style-attribute` (no scoped/module), `vue/no-restricted-block` (no `<style>` outside App.vue).
- All user-facing text is in `src/locales/it.ts` and `src/locales/en.ts`, which must have identical keys (a test enforces this).
- Theme: `data-theme` on `<html>`, remembered in `localStorage`, defaulting to the system setting.
- No comments unless something is genuinely non-obvious.

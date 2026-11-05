<template>
  <a class="skip-link" href="#main">{{ t('app.skipToContent') }}</a>
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

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import AppHeader from './components/AppHeader.vue'

const { t } = useI18n()
</script>

<style>
:root {
  color-scheme: light;
  --bg: #f4f5f7;
  --surface: #ffffff;
  --surface-2: #f1f3f6;
  --border: #e2e5ea;
  --text: #0f1720;
  --text-2: #475467;
  --text-muted: #5d6675;
  --accent: #1c5cab;
  --accent-strong: #1c5cab;
  --accent-on: #ffffff;
  --accent-soft: #e8f0fb;
  --accent-soft-text: #184f95;
  --accent-line: #86b6ef;
  --series-1: #2a78d6;
  --row-hover: #f3f7fd;
  --shadow: 0 1px 2px rgb(15 23 32 / 0.05);
  --radius: 6px;
  --content-width: 1440px;
  --font: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

:root[data-theme='dark'] {
  color-scheme: dark;
  --bg: #0f1115;
  --surface: #171a1f;
  --surface-2: #1f232a;
  --border: #2c313a;
  --text: #eef1f5;
  --text-2: #c2c8d2;
  --text-muted: #98a1ae;
  --accent: #86b6ef;
  --accent-strong: #86b6ef;
  --accent-on: #0f1115;
  --accent-soft: #1a2a40;
  --accent-soft-text: #9ec5f4;
  --accent-line: #256abf;
  --series-1: #3987e5;
  --row-hover: #1b2230;
  --shadow: none;
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font);
  font-size: 15px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

#app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

a {
  color: var(--accent);
}

:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

h1,
h2,
h3 {
  margin: 0;
  line-height: 1.25;
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 20px;
}

.muted {
  color: var(--text-muted);
}

.mono {
  font-variant-numeric: tabular-nums;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

.page-title {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  border-radius: 6px;
  padding: 8px 14px;
  font: inherit;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
}

.btn:hover:not(:disabled) {
  border-color: var(--accent-line);
  background: var(--accent-soft);
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn--small {
  padding: 4px 10px;
  font-size: 14px;
}

.btn--primary {
  background: var(--accent-strong);
  border-color: var(--accent-strong);
  color: var(--accent-on);
}

.btn--primary:hover:not(:disabled) {
  background: var(--accent-strong);
  border-color: var(--accent-strong);
  filter: brightness(1.08);
}

.input {
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  border-radius: 6px;
  padding: 9px 12px;
  font: inherit;
  min-width: 0;
}

.input:focus {
  border-color: var(--accent);
  outline: 2px solid color-mix(in srgb, var(--accent) 25%, transparent);
  outline-offset: 0;
}

.chip {
  font-size: 14px;
  padding: 3px 10px;
  border-radius: 4px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-2);
}

.skip-link {
  position: absolute;
  left: 16px;
  top: -48px;
  background: var(--surface);
  padding: 8px 12px;
  border-radius: 6px;
  z-index: 20;
}

.skip-link:focus {
  top: 12px;
}

.app-main {
  flex: 1;
  width: 100%;
  max-width: var(--content-width);
  margin: 0 auto;
  padding: 28px 16px 56px;
}

.app-footer {
  border-top: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 14px;
  text-align: center;
  padding: 18px 16px;
}

.app-footer p {
  margin: 0;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: color-mix(in srgb, var(--surface) 92%, transparent);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
}

.app-header__inner {
  max-width: var(--content-width);
  margin: 0 auto;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 28px;
  flex-wrap: wrap;
}

.app-header__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
}

.app-header__mark {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 6px;
  background: var(--accent-strong);
  color: var(--accent-on);
}

.app-header__titles {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}

.app-header__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.app-header__version {
  font-size: 14px;
  font-weight: 600;
  line-height: 1.4;
  padding: 0 6px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--surface-2);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.app-header__title {
  color: var(--text);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.app-header__tagline {
  color: var(--text-muted);
  font-size: 14px;
}

.app-header__nav {
  display: flex;
  gap: 4px;
  flex: 1;
}

.app-header__link {
  color: var(--text-2);
  text-decoration: none;
  padding: 7px 14px;
  border-radius: 4px;
  font-weight: 500;
}

.app-header__link:hover {
  background: var(--surface-2);
  color: var(--text);
}

.app-header__link--active,
.app-header__link--active:hover {
  background: var(--accent-soft);
  color: var(--accent-soft-text);
}

.app-header__controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: var(--text-muted);
  margin-right: 4px;
}

.user-menu__name {
  color: var(--text);
  font-weight: 600;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lang-switch {
  display: inline-flex;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 3px;
  background: var(--surface-2);
}

.lang-switch__option {
  border: 0;
  background: transparent;
  color: var(--text-muted);
  font: inherit;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 4px 11px;
  border-radius: 4px;
  cursor: pointer;
}

.lang-switch__option--active {
  background: var(--accent-strong);
  color: var(--accent-on);
}

.theme-toggle {
  display: inline-grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--surface-2);
  color: var(--text-2);
  cursor: pointer;
}

.theme-toggle:hover {
  color: var(--accent);
  border-color: var(--accent-line);
}

.stat-tile {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  border-top: 3px solid var(--accent-line);
}

.stat-tile__label {
  color: var(--text-2);
  font-size: 14px;
  font-weight: 500;
}

.stat-tile__value {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.stat-tile__hint {
  color: var(--text-muted);
  font-size: 14px;
}

.stat-tile--hero {
  padding: 24px;
}

.stat-tile--hero .stat-tile__value {
  font-size: 56px;
  line-height: 1.05;
}

.bar-chart {
  margin: 0;
  --value-space: 4.5rem;
}

.bar-chart__caption {
  margin-bottom: 18px;
}

.bar-chart__title {
  font-size: 16px;
  font-weight: 700;
}

.bar-chart__subtitle {
  margin: 2px 0 0;
  font-size: 14px;
}

.bar-chart__rows {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bar-chart__row {
  position: relative;
}

.bar-chart__hit {
  display: block;
  padding: 6px 8px;
  margin: 0 -8px;
  border-radius: 6px;
  color: inherit;
  text-decoration: none;
}

a.bar-chart__hit:hover,
.bar-chart__hit:focus-visible {
  background: var(--row-hover);
}

.bar-chart__label {
  display: block;
  font-size: 14px;
  color: var(--text-2);
  margin-bottom: 4px;
}

.bar-chart__track {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bar-chart__bar {
  display: block;
  height: 16px;
  min-width: 2px;
  background: var(--series-1);
  border-radius: 0 4px 4px 0;
}

.bar-chart__value {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.bar-chart__tooltip {
  position: absolute;
  bottom: calc(100% - 4px);
  margin-left: 8px;
  z-index: 5;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgb(0 0 0 / 0.12);
  font-size: 14px;
  color: var(--text-2);
  white-space: nowrap;
  pointer-events: none;
}

.bar-chart__tooltip--flip {
  transform: translateX(-100%);
  margin-left: 0;
}

.bar-chart__tooltip strong {
  color: var(--text);
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text-2);
  white-space: nowrap;
}

.badge__icon path {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.badge--official {
  color: var(--accent-soft-text);
  border-color: color-mix(in srgb, var(--accent) 35%, transparent);
  background: var(--accent-soft);
}

.project-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.project-list__item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 0;
  border-top: 1px solid var(--border);
}

.project-list__item:first-child {
  border-top: 0;
  padding-top: 0;
}

.project-list__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.project-list__title {
  font-weight: 600;
  text-decoration: none;
  overflow-wrap: anywhere;
}

a.project-list__title:hover {
  text-decoration: underline;
}

.project-list__amount {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.project-list__amount-label {
  color: var(--text-muted);
  font-size: 14px;
}

.project-list__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: 14px;
}

.project-list__summary {
  margin: 0;
  color: var(--text-2);
  font-size: 14px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.project-list__more {
  margin: 12px 0 0;
  font-size: 14px;
}

.aid-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.aid-list__item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 0;
  border-top: 1px solid var(--border);
}

.aid-list__item:first-child {
  border-top: 0;
  padding-top: 0;
}

.aid-list__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.aid-list__title {
  font-weight: 600;
  overflow-wrap: anywhere;
}

.aid-list__amount {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.aid-list__measure,
.aid-list__objectives {
  margin: 0;
  font-size: 14px;
}

.aid-list__objectives {
  color: var(--text-2);
}

.aid-list__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: 14px;
}

.aid-list__more {
  margin: 12px 0 0;
  font-size: 14px;
}

.load-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 56px 16px;
  flex-wrap: wrap;
}

.load-state p {
  margin: 0;
}

.load-state__spinner {
  width: 18px;
  height: 18px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: load-state-spin 0.8s linear infinite;
}

@keyframes load-state-spin {
  to {
    transform: rotate(360deg);
  }
}

.dashboard {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dashboard__tiles {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.dashboard__tiles .stat-tile--hero {
  grid-column: 1 / -1;
}

.dashboard__tile--wide {
  grid-column: span 2;
}

.dashboard__charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  align-items: start;
}

.dashboard__note {
  font-size: 14px;
  margin: 16px 0 0;
  padding-top: 12px;
  border-top: 1px dashed var(--border);
}

.dashboard__coverage {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px 24px;
  flex-wrap: wrap;
  background: var(--accent-soft);
  border-color: color-mix(in srgb, var(--accent) 25%, transparent);
}

.dashboard__coverage h2 {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 4px;
}

.dashboard__coverage p {
  margin: 0;
  color: var(--text-2);
  max-width: 72ch;
}

.companies {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.companies__top {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}

.companies__count {
  margin: 0;
}

.companies__filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 12px;
}

.companies__filter {
  display: flex;
  min-width: 0;
}

.companies__filter--search {
  flex: 1 1 260px;
}

.companies__filter--search .input {
  width: 100%;
}

.companies__filter select {
  max-width: 280px;
}

.companies__check,
.companies__sort {
  align-items: center;
  gap: 8px;
  color: var(--text-2);
  white-space: nowrap;
}

.companies__check input {
  width: 18px;
  height: 18px;
  accent-color: var(--accent-strong);
}

.companies__sort {
  margin-left: auto;
}

.companies__table th.companies__num,
.companies__table td.companies__num {
  text-align: right;
}

.companies__table-card {
  padding: 0;
  overflow: hidden;
  transition: opacity 0.15s;
}

.companies__table-card--busy {
  opacity: 0.6;
}

.companies__table-wrap {
  overflow-x: auto;
}

.companies__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.companies__table th,
.companies__table td {
  text-align: left;
  padding: 11px 16px;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.companies__table td:first-child {
  white-space: normal;
  min-width: 220px;
}

.companies__table th {
  font-size: 14px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  background: var(--surface-2);
}

.companies__table tbody tr:hover {
  background: var(--row-hover);
}

.companies__table td a {
  font-weight: 600;
  text-decoration: none;
}

.companies__table td a:hover {
  text-decoration: underline;
}

.companies__sector {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.companies__section-letter {
  display: inline-grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 4px;
  background: var(--accent-soft);
  color: var(--accent-soft-text);
  font-size: 14px;
  font-weight: 700;
}

.companies__empty {
  padding: 40px 16px;
  margin: 0;
  text-align: center;
}

.companies__pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  flex-wrap: wrap;
  font-size: 14px;
}

.companies__pager-buttons {
  display: flex;
  gap: 8px;
}

.company {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.company__back {
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
}

.company__header {
  border-left: 4px solid var(--accent-strong);
}

.company__name {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.company__chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.company__groups {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  align-items: start;
}

.company__group-title {
  font-size: 14px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--accent);
  margin-bottom: 8px;
}

.company__funding-tiles {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.company__funding-tiles .stat-tile {
  box-shadow: none;
  background: var(--surface-2);
}

.company__fields {
  margin: 0;
}

.company__row {
  display: grid;
  grid-template-columns: minmax(120px, 38%) 1fr;
  gap: 12px;
  padding: 10px 0;
  border-top: 1px solid var(--border);
}

.company__row:first-child {
  border-top: 0;
}

.company__term {
  color: var(--text-muted);
  font-size: 14px;
}

.company__value {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  overflow-wrap: anywhere;
}

.company__source {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 14px;
}

.company__source-note {
  flex-basis: 100%;
}

.company__hint {
  margin: 0 0 8px;
  font-size: 14px;
}

.company__sources {
  margin: 0;
  padding-left: 18px;
  font-size: 14px;
}

.not-found {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 16px;
}

@media (max-width: 900px) {
  .dashboard__tiles {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard__charts,
  .company__groups,
  .company__funding-tiles {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .app-header {
    position: static;
  }

  .app-header__inner {
    gap: 10px;
  }

  .app-header__tagline {
    display: none;
  }

  .app-header__brand {
    order: 1;
    flex: 1;
    min-width: 0;
  }

  .app-header__controls {
    display: contents;
  }

  .theme-toggle {
    order: 2;
  }

  .app-header__nav {
    order: 3;
    flex-basis: 100%;
  }

  .user-menu {
    order: 4;
    flex: 1;
    min-width: 0;
  }

  .lang-switch {
    order: 5;
  }

  .user-menu__name {
    max-width: 140px;
  }

  .stat-tile--hero .stat-tile__value {
    font-size: 44px;
  }

  .stat-tile__value {
    font-size: 22px;
  }

  .companies__filter {
    flex: 1 1 100%;
  }

  .dashboard__tile--wide {
    grid-column: 1 / -1;
  }

  .project-list__head {
    flex-direction: column;
    gap: 4px;
  }

  .project-list__amount {
    align-items: flex-start;
  }

  .companies__filter select {
    width: 100%;
    max-width: none;
  }
}

@media (max-width: 480px) {
  .company__row {
    grid-template-columns: 1fr;
    gap: 2px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .load-state__spinner {
    animation: none;
  }
}
</style>

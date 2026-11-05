import { createI18n } from 'vue-i18n'
import en from './locales/en'
import it from './locales/it'
import { readStorage, writeStorage } from './storage'

export const LOCALES = ['it', 'en'] as const
export type Locale = (typeof LOCALES)[number]

const STORAGE_KEY = 'puglia-imprese-locale'

export function detectLocale(): Locale {
  const stored = readStorage(STORAGE_KEY)
  if (stored === 'it' || stored === 'en') return stored
  return navigator.language?.toLowerCase().startsWith('it') ? 'it' : 'en'
}

export const i18n = createI18n({
  legacy: false,
  locale: detectLocale(),
  fallbackLocale: 'en',
  messages: { it, en },
})

export function setLocale(locale: Locale) {
  i18n.global.locale.value = locale
  document.documentElement.lang = locale
  writeStorage(STORAGE_KEY, locale)
}

document.documentElement.lang = i18n.global.locale.value

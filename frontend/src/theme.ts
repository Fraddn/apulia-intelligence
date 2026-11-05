import { ref } from 'vue'
import { readStorage, writeStorage } from './storage'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'puglia-imprese-theme'

function initialTheme(): Theme {
  const stored = readStorage(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

const theme = ref<Theme>(initialTheme())

function apply(value: Theme) {
  document.documentElement.dataset.theme = value
}

apply(theme.value)

export function useTheme() {
  function setTheme(value: Theme) {
    theme.value = value
    apply(value)
    writeStorage(STORAGE_KEY, value)
  }

  function toggleTheme() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  return { theme, setTheme, toggleTheme }
}

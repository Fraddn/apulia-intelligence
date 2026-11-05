import { beforeEach, describe, expect, it, vi } from 'vitest'

beforeEach(() => {
  vi.resetModules()
  localStorage.clear()
  delete document.documentElement.dataset.theme
})

describe('theme', () => {
  it('uses the stored theme', async () => {
    localStorage.setItem('puglia-imprese-theme', 'dark')
    const { useTheme } = await import('../theme')
    expect(useTheme().theme.value).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('toggles, applies and remembers the theme', async () => {
    localStorage.setItem('puglia-imprese-theme', 'light')
    const { useTheme } = await import('../theme')
    const { theme, toggleTheme } = useTheme()
    toggleTheme()
    expect(theme.value).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem('puglia-imprese-theme')).toBe('dark')
  })
})

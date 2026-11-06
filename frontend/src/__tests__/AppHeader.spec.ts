import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter } from 'vue-router'
import AppHeader from '../components/AppHeader.vue'
import en from '../locales/en'

afterEach(() => vi.unstubAllGlobals())

async function render(fetchResult: Promise<unknown>) {
  vi.stubGlobal('fetch', vi.fn().mockReturnValue(fetchResult))
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/login', name: 'login', component: { template: '<div />' } }, { path: '/:p(.*)*', component: { template: '<div />' } }] })
  const wrapper = mount(AppHeader, { global: { plugins: [i18n, router] } })
  await flushPromises()
  return wrapper
}

const ok = (version: string) => Promise.resolve({ ok: true, status: 200, json: async () => ({ status: 'ok', version }) })

describe('AppHeader version', () => {
  it('shows the release version next to the name', async () => {
    const wrapper = await render(ok('2026.11.3'))
    const badge = wrapper.find('.app-header__version')
    expect(badge.text()).toBe('v2026.11.3')
    expect(badge.attributes('title')).toBe('Version 2026.11.3')
  })

  it('shows dev for local builds', async () => {
    const wrapper = await render(ok('dev'))
    expect(wrapper.find('.app-header__version').text()).toBe('dev')
  })

  it('hides the badge when the version is unavailable', async () => {
    const wrapper = await render(Promise.reject(new Error('offline')))
    expect(wrapper.find('.app-header__version').exists()).toBe(false)
  })
})

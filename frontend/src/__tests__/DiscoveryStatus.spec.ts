import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import type { Discovery } from '../api'
import DiscoveryStatus from '../components/DiscoveryStatus.vue'
import en from '../locales/en'

function render(searching: boolean, discovery: Discovery | null) {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return mount(DiscoveryStatus, { props: { searching, discovery }, global: { plugins: [i18n] } })
}

describe('DiscoveryStatus', () => {
  it('shows the search in progress', () => {
    expect(render(true, null).text()).toContain('Looking for the company website')
  })

  it('explains each outcome', () => {
    expect(render(false, { status: 'not_found', found_url: '', attempted_at: null }).text()).toContain('No website showing this company’s VAT number')
    expect(render(false, { status: 'no_candidates', found_url: '', attempted_at: null }).text()).toContain('too short')
    expect(render(false, { status: 'busy', found_url: '', attempted_at: null }).text()).toContain('busy')
    expect(render(false, { status: 'timeout', found_url: '', attempted_at: null }).text()).toContain('took too long')
  })

  it('stays quiet when a website was found or nothing happened', () => {
    expect(render(false, { status: 'found', found_url: 'https://x.it/', attempted_at: null }).text()).toBe('')
    expect(render(false, null).text()).toBe('')
  })
})

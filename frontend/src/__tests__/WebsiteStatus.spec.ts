import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import type { WebsiteCheck } from '../api'
import WebsiteStatus from '../components/WebsiteStatus.vue'
import en from '../locales/en'

function render(check: WebsiteCheck | null) {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return mount(WebsiteStatus, { props: { check }, global: { plugins: [i18n] } })
}

const verified: WebsiteCheck = { url: 'https://alfa.it/', status: 'verified', pages: 3, checked_at: '2026-11-05T10:00:00Z' }

describe('WebsiteStatus', () => {
  it('describes a verified website with date and link', () => {
    const wrapper = render(verified)
    expect(wrapper.text()).toContain('Contacts read from the company website on 5 Nov 2026')
    expect(wrapper.text()).toContain('VAT number verified')
    expect(wrapper.find('a').attributes('href')).toBe('https://alfa.it/')
  })

  it('explains the other outcomes', () => {
    expect(render({ ...verified, status: 'vat_not_found' }).text()).toContain('does not show this company’s VAT number')
    expect(render({ ...verified, status: 'unreachable' }).text()).toContain('could not be reached')
    expect(render({ ...verified, status: 'blocked' }).text()).toContain('does not allow automated reading')
  })

  it('renders nothing without a check or without a website', () => {
    expect(render(null).text()).toBe('')
    expect(render({ ...verified, status: 'no_website', url: '' }).text()).toBe('')
  })
})

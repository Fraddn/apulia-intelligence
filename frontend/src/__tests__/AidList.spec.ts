import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import type { StateAidItem } from '../api'
import AidList from '../components/AidList.vue'
import en from '../locales/en'

function aid(overrides: Partial<StateAidItem> = {}): StateAidItem {
  return {
    cor: '101',
    granted_on: '2025-06-01',
    measure_title: 'PR PUGLIA FESR 2021/2027 – Innovazione',
    granting_body: 'Regione Puglia',
    project_title: 'Piattaforma digitale',
    objectives: 'Ricerca, sviluppo e innovazione',
    procedures: 'De Minimis',
    instruments: 'Sovvenzione',
    aid_amount: 25000,
    transparency_url: 'https://www.regione.puglia.it/bandi/101',
    ...overrides,
  }
}

function render(items: StateAidItem[], total = items.length) {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return mount(AidList, { props: { items, total }, global: { plugins: [i18n] } })
}

describe('AidList', () => {
  it('shows project, measure, body, date, procedure and amount', () => {
    const item = render([aid()]).find('.aid-list__item')
    expect(item.find('.aid-list__title').text()).toBe('Piattaforma digitale')
    expect(item.text()).toContain('PR PUGLIA FESR 2021/2027 – Innovazione')
    expect(item.text()).toContain('Regione Puglia')
    expect(item.text()).toContain('1 Jun 2025')
    expect(item.text()).toContain('De Minimis')
    expect(item.text()).toContain('Ricerca, sviluppo e innovazione')
    expect(item.text()).toContain('€25,000')
    expect(item.find('a').attributes('href')).toBe('https://www.regione.puglia.it/bandi/101')
  })

  it('uses the measure as title when the project title is missing', () => {
    const item = render([aid({ project_title: '' })]).find('.aid-list__item')
    expect(item.find('.aid-list__title').text()).toBe('PR PUGLIA FESR 2021/2027 – Innovazione')
  })

  it('handles missing amounts and non-web links', () => {
    const wrapper = render([aid({ aid_amount: null, transparency_url: 'n.d.' })])
    expect(wrapper.text()).toContain('Not available')
    expect(wrapper.find('a').exists()).toBe(false)
  })

  it('says when only part of the list is shown', () => {
    expect(render([aid()], 80).text()).toContain('Showing 1 of 80 grants')
  })
})

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import type { FundedProject } from '../api'
import ProjectList from '../components/ProjectList.vue'
import en from '../locales/en'

function project(overrides: Partial<FundedProject> = {}): FundedProject {
  return {
    code: 'P1',
    title: 'Piattaforma cloud',
    summary: 'Sviluppo di una piattaforma cloud per la logistica',
    theme_code: '01',
    theme: 'Ricerca e innovazione',
    cycle: 'Ciclo di programmazione 2014-2020',
    status: 'completed',
    role: 'beneficiary',
    public_funding: 100000,
    beneficiaries_count: 1,
    start_date: '2021-01-15',
    expected_end_date: '2022-12-31',
    actual_end_date: null,
    url: 'https://opencoesione.gov.it/it/dati/progetti/p1/',
    ...overrides,
  }
}

function render(projects: FundedProject[], total = projects.length) {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return mount(ProjectList, { props: { projects, total }, global: { plugins: [i18n] } })
}

describe('ProjectList', () => {
  it('shows title, link, theme, role, status, amount and description', () => {
    const wrapper = render([project()])
    const item = wrapper.find('.project-list__item')
    expect(item.find('a').attributes('href')).toBe('https://opencoesione.gov.it/it/dati/progetti/p1/')
    expect(item.find('a').text()).toBe('Piattaforma cloud')
    expect(item.text()).toContain('Research and innovation')
    expect(item.text()).toContain('Beneficiary')
    expect(item.text()).toContain('Completed')
    expect(item.text()).toContain('€100,000')
    expect(item.text()).toContain('Sole beneficiary')
    expect(item.text()).toContain('Sviluppo di una piattaforma cloud')
  })

  it('marks shared projects', () => {
    const wrapper = render([project({ beneficiaries_count: 3 })])
    expect(wrapper.text()).toContain('Shared by 3 beneficiaries')
    expect(wrapper.text()).not.toContain('Sole beneficiary')
  })

  it('does not claim funding for non-beneficiary roles', () => {
    const wrapper = render([project({ role: 'contractor' })])
    expect(wrapper.text()).toContain('Contractor')
    expect(wrapper.text()).not.toContain('Sole beneficiary')
    expect(wrapper.text()).toContain('Project value')
  })

  it('hides a description identical to the title and handles missing amounts', () => {
    const wrapper = render([project({ summary: 'Piattaforma cloud', public_funding: null })])
    expect(wrapper.findAll('.project-list__summary')).toHaveLength(0)
    expect(wrapper.text()).toContain('Not available')
  })

  it('falls back to the source label for unknown themes', () => {
    const wrapper = render([project({ theme_code: '99', theme: 'Tema sconosciuto' })])
    expect(wrapper.text()).toContain('Tema sconosciuto')
  })

  it('says when only part of the list is shown', () => {
    const wrapper = render([project()], 120)
    expect(wrapper.text()).toContain('Showing 1 of 120 projects')
  })
})

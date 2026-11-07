import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter } from 'vue-router'
import en from '../locales/en'
import { resetLibrary } from '../library'
import CompanyView from '../views/CompanyView.vue'

afterEach(() => {
  vi.unstubAllGlobals()
  resetLibrary()
})

const source = { name: 'OpenCoesione', kind: 'open_data', url: '', licence: '', attribution: '' }
const official = (field: string, raw = '') => ({
  field, raw_value: raw, assurance: 'official', confidence: null, source, reference: '', data_date: '2026-06-30', collected_at: '2026-07-01',
})

const company: Record<string, unknown> = {
  vat_number: '03132170717', name: 'ALFA SRL', province: 'BA', city: '', ateco_section: '', ateco_code: '',
  size_class: 'unknown', tax_code: '03132170717', legal_form_code: '', legal_form: '', ateco_description: '',
  ateco_version: '', municipality_code: '', address: '', postcode: '', website: '', phone: '080 123456',
  email: '', pec: '', latitude: null, longitude: null, status: 'unknown', employees_band: '', founded_on: null,
  profile_level: 'basic', provenance: [], projects: [], projects_total: 0,
  funding: { beneficiary_projects: 0, sole_beneficiary_projects: 0, shared_projects: 0, sole_beneficiary_funding: null, roles: {} },
  aid: { count: 0, total_amount: null, latest_date: null, items: [] },
  website_check: { url: '', status: 'no_website', pages: 0, checked_at: null },
}

async function render(overrides: Record<string, unknown> = {}) {
  const body = { ...company, ...overrides }
  const fetchMock = vi.fn((url: string) =>
    Promise.resolve({ ok: true, status: 200, json: async () => (url.startsWith('/api/library') ? [] : body) }),
  )
  vi.stubGlobal('fetch', fetchMock)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/companies', name: 'companies', component: { template: '<div />' } },
      { path: '/compare', name: 'compare', component: { template: '<div />' } },
      { path: '/companies/:vat', name: 'company', component: CompanyView, props: true },
    ],
  })
  await router.push('/companies/03132170717')
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  const wrapper = mount(CompanyView, { props: { vat: '03132170717' }, global: { plugins: [i18n, router] } })
  await flushPromises()
  return wrapper
}

describe('CompanyView fields', () => {
  it('shows only fields that have a value', async () => {
    const terms = (await render()).findAll('.company__term').map((term) => term.text())
    expect(terms).toEqual(['Province', 'Phone'])
  })

  it('shows the tax code only when it differs from the VAT number', async () => {
    const terms = (await render({ tax_code: '80012345678' })).findAll('.company__term').map((term) => term.text())
    expect(terms).toContain('Tax code')
  })

  it('names a shared source once per card and keeps notes for exceptions', async () => {
    const wrapper = await render({
      legal_form: 'Società a responsabilità limitata',
      size_class: 'small',
      provenance: [
        official('legal_form'),
        official('size_class', 'Piccola impresa'),
        { ...official('founded_on'), source: { ...source, name: 'RNA' } },
      ],
      founded_on: '2001-05-04',
    })
    const identity = wrapper.findAll('.card').find((card) => card.text().startsWith('Identity'))!
    expect(identity.find('.company__card-source').text()).toContain('OpenCoesione')
    expect(identity.findAll('.company__source').map((line) => line.text())).toEqual([expect.stringContaining('RNA')])
    expect(identity.find('[title="Original value: Piccola impresa"]').text()).toBe('Small')
  })

  it('summarises key figures under the name', async () => {
    const wrapper = await render({
      size_class: 'small',
      founded_on: '2001-05-04',
      funding: { beneficiary_projects: 3, sole_beneficiary_projects: 2, shared_projects: 1, sole_beneficiary_funding: 250000, roles: {} },
    })
    const facts = wrapper.findAll('.company__fact').map((fact) => fact.text())
    expect(facts).toEqual(['Company sizeSmall', 'Founded2001', 'Projects as beneficiary3', 'Funding as sole beneficiary€250,000'])
  })

  it('hides a group with no values but keeps the location card', async () => {
    const titles = (await render()).findAll('.company__group-title').map((title) => title.text())
    expect(titles).toContain('Location')
    expect(titles).not.toContain('Size')
    expect(titles).not.toContain('Activity')
  })
})

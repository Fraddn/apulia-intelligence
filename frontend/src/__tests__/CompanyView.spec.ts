import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter } from 'vue-router'
import en from '../locales/en'
import CompanyView from '../views/CompanyView.vue'

afterEach(() => vi.unstubAllGlobals())

const company = {
  vat_number: '03132170717', name: 'ALFA SRL', province: 'BA', city: '', ateco_section: '', ateco_code: '',
  size_class: 'unknown', tax_code: '03132170717', legal_form_code: '', legal_form: '', ateco_description: '',
  ateco_version: '', municipality_code: '', address: '', postcode: '', website: '', phone: '080 123456',
  email: '', pec: '', latitude: null, longitude: null, status: 'unknown', employees_band: '', founded_on: null,
  profile_level: 'basic', provenance: [], projects: [], projects_total: 0,
  funding: { beneficiary_projects: 0, sole_beneficiary_projects: 0, shared_projects: 0, sole_beneficiary_funding: null, roles: {} },
  aid: { count: 0, total_amount: null, latest_date: null, items: [] },
  website_check: { url: '', status: 'no_website', pages: 0, checked_at: null },
}

async function render() {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => company })
  vi.stubGlobal('fetch', fetchMock)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/companies', name: 'companies', component: { template: '<div />' } },
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
    expect(terms).toEqual(['VAT number', 'Tax code', 'Province', 'Phone'])
  })

  it('hides a group with no values but keeps the location card', async () => {
    const titles = (await render()).findAll('.company__group-title').map((title) => title.text())
    expect(titles).toContain('Location')
    expect(titles).not.toContain('Size')
    expect(titles).not.toContain('Activity')
  })
})

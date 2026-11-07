import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter } from 'vue-router'
import en from '../locales/en'
import CompareView from '../views/CompareView.vue'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

function detail(vat: string, name: string, extra: Record<string, unknown> = {}) {
  return {
    vat_number: vat, name, province: 'BA', city: 'Bari', ateco_section: 'J', ateco_code: '62.01.00', size_class: 'small',
    tax_code: vat, legal_form_code: '', legal_form: 'Srl', ateco_description: 'Software', ateco_version: '2007',
    municipality_code: '', address: '', postcode: '', website: '', phone: '', email: '', pec: '', latitude: null,
    longitude: null, status: 'unknown', employees_band: '', founded_on: null, profile_level: 'basic', provenance: [],
    projects: [], projects_total: 0,
    funding: { beneficiary_projects: 0, sole_beneficiary_projects: 0, shared_projects: 0, sole_beneficiary_funding: null, roles: {} },
    aid: { count: 0, total_amount: null, latest_date: null, items: [] },
    website_check: null,
    ...extra,
  }
}

const ALFA = detail('03132170717', 'ALFA SRL', {
  funding: { beneficiary_projects: 3, sole_beneficiary_projects: 2, shared_projects: 1, sole_beneficiary_funding: 250000, roles: {} },
})
const BETA = detail('05866880726', 'BETA SPA', {
  funding: { beneficiary_projects: 1, sole_beneficiary_projects: 1, shared_projects: 0, sole_beneficiary_funding: 900000, roles: {} },
})
const GAMMA = { vat_number: '02462780731', name: 'GAMMA SRL', province: 'TA', city: '', ateco_section: 'F', ateco_code: '', size_class: 'unknown', beneficiary_projects: 0, sole_beneficiary_funding: null }

function api(url: string) {
  const path = new URL(url, 'http://x').pathname
  const details: Record<string, unknown> = { '03132170717': ALFA, '05866880726': BETA, '02462780731': detail('02462780731', 'GAMMA SRL') }
  const body = details[path.split('/').pop()!] ?? { count: 1, items: [GAMMA] }
  return Promise.resolve({ ok: true, status: 200, json: async () => body })
}

async function render(url: string) {
  const fetchMock = vi.fn(api)
  vi.stubGlobal('fetch', fetchMock)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/compare', name: 'compare', component: CompareView },
      { path: '/companies/:vat', name: 'company', component: { template: '<div />' } },
    ],
  })
  await router.push(url)
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  const wrapper = mount(CompareView, { global: { plugins: [i18n, router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router, fetchMock }
}

const cellsOf = (wrapper: Awaited<ReturnType<typeof render>>['wrapper'], label: string) =>
  wrapper.findAll('tr').find((row) => row.find('th').text() === label)!.findAll('td:not(.compare__slot-cell)')

const labels = (wrapper: Awaited<ReturnType<typeof render>>['wrapper']) => wrapper.findAll('.compare__label').map((th) => th.text())

describe('CompareView', () => {
  it('shows a hint when nothing is selected', async () => {
    const { wrapper } = await render('/compare')
    expect(wrapper.find('.compare__empty').text()).toContain('add 2 to 4 companies')
  })

  it('puts the companies side by side and highlights the higher number', async () => {
    const { wrapper } = await render('/compare?vats=03132170717,05866880726')
    expect(wrapper.findAll('.compare__company-name').map((a) => a.text())).toEqual(['ALFA SRL', 'BETA SPA'])
    const projects = cellsOf(wrapper, 'Projects as beneficiary')
    expect(projects.map((c) => c.text())).toEqual(['3', '1'])
    expect(projects[0].classes()).toContain('compare__best')
    const funding = cellsOf(wrapper, 'Funding as sole beneficiary')
    expect(funding[1].classes()).toContain('compare__best')
    expect(funding[1].find('.compare__bar').attributes('style')).toContain('--fill: 1')
    expect(labels(wrapper)).not.toContain('Grants')
  })

  it('can hide the rows where every company has the same value', async () => {
    const { wrapper } = await render('/compare?vats=03132170717,05866880726')
    expect(labels(wrapper)).toContain('Legal form')
    await wrapper.find('.compare__toggle input').setValue(true)
    expect(labels(wrapper)).not.toContain('Legal form')
    expect(labels(wrapper)).toContain('Projects as beneficiary')
    expect(wrapper.find('.compare__toolbar').text()).toMatch(/identical rows? hidden/)
  })

  it('offers an empty slot until the comparison is full', async () => {
    const { wrapper } = await render('/compare?vats=03132170717')
    expect(wrapper.find('.compare__slot').text()).toContain('Add at least one more')
    expect(wrapper.find('.compare__toolbar').exists()).toBe(false)
  })

  it('removes a company from the comparison', async () => {
    const { wrapper, router } = await render('/compare?vats=03132170717,05866880726')
    await wrapper.find('.compare__remove').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ vats: '05866880726' })
  })

  it('searches and adds a company from the suggestions', async () => {
    vi.useFakeTimers()
    const { wrapper, router, fetchMock } = await render('/compare?vats=03132170717')
    const input = wrapper.find('input[role="combobox"]')
    await input.trigger('focus')
    await input.setValue('gamma')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    expect(new URL(fetchMock.mock.calls.at(-1)![0], 'http://x').searchParams.get('search')).toBe('gamma')
    const option = wrapper.find('[role="option"]')
    expect(option.text()).toContain('GAMMA SRL')
    await option.trigger('mousedown')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ vats: '03132170717,02462780731' })
  })
})

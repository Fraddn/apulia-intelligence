import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter } from 'vue-router'
import en from '../locales/en'
import DashboardView from '../views/DashboardView.vue'

afterEach(() => vi.unstubAllGlobals())

const stats = {
  total: 100,
  with_ateco: 90,
  size_known: 80,
  by_province: [{ province: 'BA', count: 60 }, { province: 'LE', count: 40 }],
  by_section: [{ section: 'C', count: 50 }, { section: 'G', count: 40 }],
  by_size: [{ size: 'sme', count: 70 }, { size: 'large', count: 10 }, { size: 'unknown', count: 20 }],
  sources: [{ name: 'OpenCoesione', url: '', licence: '', attribution: '', data_date: '2026-06-30' }],
  funding: { beneficiary_companies: 30, beneficiary_projects: 40, sole_beneficiary_funding: 1000000, by_theme: [{ theme_code: '01', theme: 'Ricerca', count: 5 }] },
  aid: { companies: 20, grants: 50, total_amount: 500000 },
}

async function render(url = '/') {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => stats })
  vi.stubGlobal('fetch', fetchMock)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'dashboard', component: DashboardView },
      { path: '/companies', name: 'companies', component: { template: '<div />' } },
    ],
  })
  await router.push(url)
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  const wrapper = mount(DashboardView, { global: { plugins: [i18n, router] } })
  await flushPromises()
  return { wrapper, router, fetchMock }
}

const lastUrl = (fetchMock: ReturnType<typeof vi.fn>) => new URL(fetchMock.mock.calls.at(-1)?.[0], 'http://x')

describe('DashboardView', () => {
  it('filters the whole dashboard from the dropdowns, and clears it', async () => {
    const { wrapper, router, fetchMock } = await render()
    await wrapper.find('select[name="province"]').setValue('BA')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ province: 'BA' })
    expect(lastUrl(fetchMock).searchParams.get('province')).toBe('BA')
    expect(wrapper.find('.bar-chart__row--selected').text()).toContain('Bari')
    await wrapper.find('select[name="section"]').setValue('C')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ province: 'BA', section: 'C' })
    await wrapper.find('.dashboard__scope button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({})
  })

  it('every bar opens the company list instead of changing the dashboard', async () => {
    const { wrapper } = await render('/?section=C')
    const bars = wrapper.findAll('.bar-chart__hit')
    expect(bars.every((bar) => bar.element.tagName === 'A' || bar.text().startsWith('SME'))).toBe(true)
    const hrefs = bars.map((bar) => bar.attributes('href'))
    expect(hrefs).toContain('/companies?section=C&province=LE')
    expect(hrefs).toContain('/companies?section=G')
  })

  it('links figures and bars to the company list with the current filter', async () => {
    const { wrapper } = await render('/?province=BA')
    const hrefs = wrapper.findAll('a').map((a) => a.attributes('href'))
    expect(hrefs).toContain('/companies?province=BA&min_projects=1&sort=funding')
    expect(wrapper.findAll('.dashboard__metric--link .dashboard__metric-cta')).toHaveLength(3)
    expect(hrefs).toContain('/companies?province=BA&size=large')
    expect(hrefs).toContain('/companies?province=BA&theme=01')
    expect(hrefs).not.toContain('/companies?province=BA&size=sme')
  })
})

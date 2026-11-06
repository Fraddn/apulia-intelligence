import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter } from 'vue-router'
import en from '../locales/en'
import CompaniesView from '../views/CompaniesView.vue'

afterEach(() => vi.unstubAllGlobals())

const page: { count: number; items: Record<string, unknown>[] } = {
  count: 1,
  items: [
    {
      vat_number: '03132170717', name: 'ALFA INFORMATICA SRL', province: 'BA', city: '',
      ateco_section: 'J', ateco_code: '62.01.00', size_class: 'unknown',
      beneficiary_projects: 2, sole_beneficiary_funding: 100000,
    },
  ],
}

async function render(url: string) {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => page })
  vi.stubGlobal('fetch', fetchMock)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/companies', name: 'companies', component: CompaniesView },
      { path: '/companies/:vat', name: 'company', component: { template: '<div />' } },
    ],
  })
  await router.push(url)
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  const wrapper = mount(CompaniesView, { global: { plugins: [i18n, router] } })
  await flushPromises()
  return { wrapper, fetchMock, router }
}

function lastRequest(fetchMock: ReturnType<typeof vi.fn>) {
  return new URL(fetchMock.mock.calls.at(-1)?.[0], 'http://x').searchParams
}

describe('CompaniesView filters', () => {
  it('sends all filters and the sort order from the URL', async () => {
    const { fetchMock } = await render('/companies?section=J&division=62&theme=01&size=sme&min_projects=2&min_funding=100000&sort=funding')
    const params = lastRequest(fetchMock)
    expect(params.get('section')).toBe('J')
    expect(params.get('division')).toBe('62')
    expect(params.get('size')).toBe('sme')
    expect(params.get('min_projects')).toBe('2')
    expect(params.get('min_funding')).toBe('100000')
    expect(params.get('theme')).toBe('01')
    expect(params.get('sort')).toBe('funding')
  })

  it('shows sub-sectors only for the chosen sector', async () => {
    const { wrapper } = await render('/companies')
    expect(wrapper.find('select[name="division"]').exists()).toBe(false)
    const { wrapper: withSection } = await render('/companies?section=J')
    const options = withSection.findAll('select[name="division"] option').map((o) => o.attributes('value'))
    expect(options).toEqual(['', '58', '59', '60', '61', '62', '63'])
  })

  it('clears the sub-sector when the sector changes', async () => {
    const { wrapper, router } = await render('/companies?section=J&division=62')
    await wrapper.find('select[name="section"]').setValue('C')
    await flushPromises()
    expect(router.currentRoute.value.query.section).toBe('C')
    expect(router.currentRoute.value.query.division).toBeUndefined()
  })

  it('sets size, project and funding filters and changes sorting', async () => {
    const { wrapper, router } = await render('/companies')
    for (const [name, value] of [['size', 'large'], ['min_projects', '5'], ['min_funding', '1000000']]) {
      await wrapper.find(`select[name="${name}"]`).setValue(value)
      await flushPromises()
    }
    expect(router.currentRoute.value.query).toMatchObject({ size: 'large', min_projects: '5', min_funding: '1000000' })
    expect(wrapper.find('select[name="min_funding"] option[value="1000000"]').text()).toBe('At least €1,000,000')
    await wrapper.find('select[name="sort"]').setValue('projects')
    await flushPromises()
    expect(router.currentRoute.value.query.sort).toBe('projects')
  })

  it('shows the town with the province code, or the province when the town is unknown', async () => {
    page.items = [
      { ...page.items[0], city: 'Brindisi', province: 'BR' },
      { ...page.items[0], vat_number: '02462780731', city: '', province: 'TA' },
    ]
    const { wrapper } = await render('/companies')
    const cells = wrapper.findAll('tbody tr').map((row) => row.findAll('td')[2].text())
    expect(cells).toEqual(['Brindisi (BR)', 'Taranto'])
    expect(wrapper.findAll('thead th')[2].text()).toBe('Location')
  })

  it('shows funding columns', async () => {
    const { wrapper } = await render('/companies')
    const row = wrapper.find('tbody tr')
    expect(row.text()).toContain('€100,000')
    expect(row.findAll('td').map((td) => td.text())).toContain('2')
  })

  it('shows page numbers around the current page with the first and last page', async () => {
    page.count = 1000
    const { wrapper } = await render('/companies?page=6')
    const items = wrapper.findAll('.companies__pages > *').map((el) => el.text())
    expect(items).toEqual(['← Previous', '6 / 40', '1', '…', '4', '5', '6', '7', '8', '…', '40', 'Next →'])
    expect(wrapper.find('[aria-current="page"]').text()).toBe('6')
  })

  it('changes rows per page and goes back to the first page', async () => {
    page.count = 1000
    const { wrapper, router, fetchMock } = await render('/companies?page=3&province=BA')
    await wrapper.find('select[name="page_size"]').setValue('100')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ province: 'BA', page_size: '100' })
    expect(lastRequest(fetchMock).get('page_size')).toBe('100')
    const items = wrapper.findAll('.companies__page').map((el) => el.text())
    expect(items).toEqual(['1', '2', '3', '10'])
  })

  it('counts active filters on the phone filter toggle and opens the panel', async () => {
    const { wrapper } = await render('/companies?province=BA&size=sme&search=alfa')
    const toggle = wrapper.find('.companies__filters-toggle')
    expect(toggle.text()).toBe('Filters (2)')
    expect(toggle.attributes('aria-expanded')).toBe('false')
    await toggle.trigger('click')
    expect(wrapper.find('.companies__filters').classes()).toContain('companies__filters--open')
    expect(toggle.attributes('aria-expanded')).toBe('true')
  })

  it('shows a compact page status for phones', async () => {
    page.count = 1000
    const { wrapper } = await render('/companies?page=6')
    expect(wrapper.find('.companies__page-status').text()).toBe('6 / 40')
  })
})

import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter } from 'vue-router'
import SaveButton from '../components/SaveButton.vue'
import { resetLibrary } from '../library'
import en from '../locales/en'
import LibraryView from '../views/LibraryView.vue'

afterEach(() => {
  resetLibrary()
  vi.unstubAllGlobals()
})

function saved(vat: string, name: string, extra: Record<string, unknown> = {}) {
  return {
    vat_number: vat, name, province: 'BA', city: 'Bari', ateco_section: 'J', ateco_code: '62.01.00', size_class: 'small',
    beneficiary_projects: 0, sole_beneficiary_funding: null, saved_at: '2026-11-01T10:00:00Z', note: '', ...extra,
  }
}

const ALFA = saved('03132170717', 'ALFA SRL', { note: 'Call in spring', beneficiary_projects: 2, sole_beneficiary_funding: 50000 })
const BETA = saved('05866880726', 'BETA SPA', { city: 'Lecce', province: 'LE', sole_beneficiary_funding: 900000 })
const GAMMA = saved('02462780731', 'GAMMA SRL')

function server(initial: ReturnType<typeof saved>[]) {
  let items = [...initial]
  return vi.fn(async (url: string, init: RequestInit = {}) => {
    const vat = url.split('/').pop()!
    const method = init.method ?? 'GET'
    let body: unknown = items
    let status = 200
    if (method === 'DELETE') {
      items = items.filter((i) => i.vat_number !== vat)
      status = 204
    } else if (method === 'PATCH') {
      const note = JSON.parse(String(init.body)).note
      items = items.map((i) => (i.vat_number === vat ? { ...i, note } : i))
      body = items.find((i) => i.vat_number === vat)
    } else if (method === 'POST') {
      const item = [ALFA, BETA, GAMMA].find((i) => i.vat_number === vat)!
      items = [{ ...item, note: '' }, ...items.filter((i) => i.vat_number !== vat)]
      body = items[0]
    }
    return { ok: true, status, json: async () => body }
  })
}

function plugins() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/library', name: 'library', component: LibraryView },
      { path: '/companies', name: 'companies', component: { template: '<div />' } },
      { path: '/compare', name: 'compare', component: { template: '<div />' } },
      { path: '/companies/:vat', name: 'company', component: { template: '<div />' } },
    ],
  })
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return { router, i18n }
}

async function render(items: ReturnType<typeof saved>[]) {
  const fetchMock = server(items)
  vi.stubGlobal('fetch', fetchMock)
  const { router, i18n } = plugins()
  await router.push('/library')
  const wrapper = mount(LibraryView, { global: { plugins: [i18n, router] } })
  await flushPromises()
  return { wrapper, fetchMock }
}

const names = (wrapper: Awaited<ReturnType<typeof render>>['wrapper']) => wrapper.findAll('.library__name').map((a) => a.text())

describe('LibraryView', () => {
  it('invites to browse when nothing is saved', async () => {
    const { wrapper } = await render([])
    expect(wrapper.find('.library__empty').text()).toContain('Nothing saved yet')
  })

  it('lists saved companies with their note, and filters and sorts them', async () => {
    const { wrapper } = await render([BETA, ALFA])
    expect(names(wrapper)).toEqual(['BETA SPA', 'ALFA SRL'])
    expect(wrapper.find('.library__note-text').text()).toBe('Call in spring')
    await wrapper.find('.library__search-input').setValue('spring')
    expect(names(wrapper)).toEqual(['ALFA SRL'])
    await wrapper.find('.library__search-input').setValue('')
    await wrapper.find('select').setValue('name')
    expect(names(wrapper)).toEqual(['ALFA SRL', 'BETA SPA'])
  })

  it('edits a note', async () => {
    const { wrapper, fetchMock } = await render([GAMMA])
    await wrapper.find('.library__add-note').trigger('click')
    await wrapper.find('textarea').setValue('Good partner')
    await wrapper.find('.library__note-form').trigger('submit')
    await flushPromises()
    const [url, init] = fetchMock.mock.calls.at(-1)!
    expect(url).toBe('/api/library/02462780731')
    expect(init).toMatchObject({ method: 'PATCH', body: JSON.stringify({ note: 'Good partner' }) })
    expect(wrapper.find('.library__note-text').text()).toBe('Good partner')
  })

  it('deletes a note and can bring it back', async () => {
    const { wrapper, fetchMock } = await render([ALFA])
    await wrapper.find('.library__note-tool--danger').trigger('click')
    await flushPromises()
    expect(fetchMock.mock.calls.at(-1)![1]).toMatchObject({ method: 'PATCH', body: JSON.stringify({ note: '' }) })
    expect(wrapper.find('.library__note').exists()).toBe(false)
    expect(wrapper.find('.library__note-deleted').text()).toContain('Note deleted.')
    await wrapper.find('.library__note-deleted .btn').trigger('click')
    await flushPromises()
    expect(wrapper.find('.library__note-text').text()).toBe('Call in spring')
  })

  it('compares the ticked companies', async () => {
    const { wrapper } = await render([ALFA, BETA, GAMMA])
    expect(wrapper.find('.library__compare-disabled').exists()).toBe(true)
    const boxes = wrapper.findAll('.library__pick input')
    await boxes[0].setValue(true)
    await boxes[2].setValue(true)
    const link = wrapper.find('.library__compare a')
    expect(link.attributes('href')).toBe('/compare?vats=03132170717,02462780731')
  })

  it('removes a company and can undo it, keeping the note', async () => {
    const { wrapper, fetchMock } = await render([ALFA, BETA])
    await wrapper.findAll('.library__remove')[0].trigger('click')
    await flushPromises()
    expect(names(wrapper)).toEqual(['BETA SPA'])
    expect(wrapper.find('.library__undo').text()).toContain('ALFA SRL removed')
    await wrapper.find('.library__undo .btn').trigger('click')
    await flushPromises()
    expect(names(wrapper)).toContain('ALFA SRL')
    expect(fetchMock.mock.calls.at(-1)![1]).toMatchObject({ method: 'PATCH', body: JSON.stringify({ note: 'Call in spring' }) })
  })
})

describe('SaveButton', () => {
  it('saves and unsaves a company', async () => {
    const fetchMock = server([])
    vi.stubGlobal('fetch', fetchMock)
    const { router, i18n } = plugins()
    const wrapper = mount(SaveButton, { props: { vat: '05866880726', name: 'BETA SPA' }, global: { plugins: [i18n, router] } })
    await flushPromises()
    expect(wrapper.text()).toBe('Save')
    expect(wrapper.attributes('aria-pressed')).toBe('false')
    await wrapper.trigger('click')
    await flushPromises()
    expect(fetchMock.mock.calls.at(-1)).toEqual(['/api/library/05866880726', expect.objectContaining({ method: 'POST' })])
    expect(wrapper.text()).toBe('Saved')
    expect(wrapper.attributes('aria-pressed')).toBe('true')
    await wrapper.trigger('click')
    await flushPromises()
    expect(fetchMock.mock.calls.at(-1)![1]).toMatchObject({ method: 'DELETE' })
    expect(wrapper.text()).toBe('Save')
  })
})

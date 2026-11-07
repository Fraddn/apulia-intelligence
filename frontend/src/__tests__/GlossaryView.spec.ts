import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter } from 'vue-router'
import en from '../locales/en'
import itMessages from '../locales/it'
import GlossaryView from '../views/GlossaryView.vue'

async function render(locale = 'en') {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/info', name: 'glossary', component: GlossaryView }] })
  await router.push('/info')
  const i18n = createI18n({ legacy: false, locale, messages: { en, it: itMessages } })
  const wrapper = mount(GlossaryView, { global: { plugins: [i18n, router] } })
  await flushPromises()
  return wrapper
}

describe('GlossaryView', () => {
  it('lists every term in the locale, grouped', async () => {
    const wrapper = await render()
    expect(wrapper.findAll('.glossary__term')).toHaveLength(Object.keys(en.glossary.terms).length)
    expect(wrapper.findAll('.glossary__group-title').map((h) => h.text())).toEqual(Object.values(en.glossary.groups))
    expect(wrapper.find('#term-vat').text()).toContain('Partita IVA')
  })

  it('filters terms and highlights the match, ignoring accents', async () => {
    const wrapper = await render('it')
    await wrapper.find('.glossary__search-input').setValue('attivita')
    const names = wrapper.findAll('.glossary__term-name').map((n) => n.text())
    expect(names).toContain('ATECO')
    expect(names).not.toContain('PEC')
    expect(wrapper.find('.glossary__term mark').text().toLowerCase()).toBe('attività')
  })

  it('says when nothing matches', async () => {
    const wrapper = await render()
    await wrapper.find('.glossary__search-input').setValue('zzzz')
    expect(wrapper.find('.glossary__none').text()).toContain('zzzz')
    expect(wrapper.findAll('.glossary__term')).toHaveLength(0)
  })
})

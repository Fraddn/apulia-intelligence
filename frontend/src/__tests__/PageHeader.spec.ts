import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import en from '../locales/en'
import PageHeader from '../components/PageHeader.vue'

function render() {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return mount(PageHeader, {
    props: { title: 'Companies', infoTitle: 'About this list', items: ['First point', 'Second point'] },
    global: { plugins: [i18n] },
  })
}

describe('PageHeader', () => {
  it('opens and closes the information panel from the i button', async () => {
    const wrapper = render()
    const toggle = wrapper.find('.page-header__info')
    expect(wrapper.find('h1').text()).toBe('Companies')
    expect(toggle.attributes('aria-label')).toBe('About this page')
    expect(wrapper.find('.page-header__panel').exists()).toBe(false)

    await toggle.trigger('click')
    const panel = wrapper.find('.page-header__panel')
    expect(toggle.attributes('aria-expanded')).toBe('true')
    expect(toggle.attributes('aria-controls')).toBe(panel.attributes('id'))
    expect(panel.find('h2').text()).toBe('About this list')
    expect(panel.findAll('li').map((li) => li.text())).toEqual(['First point', 'Second point'])

    await wrapper.find('.page-header__close').trigger('click')
    expect(wrapper.find('.page-header__panel').exists()).toBe(false)
  })
})

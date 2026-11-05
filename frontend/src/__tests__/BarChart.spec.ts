import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter } from 'vue-router'
import BarChart, { type BarItem } from '../components/BarChart.vue'

function render(props: { title: string; items: BarItem[]; total?: number }) {
  const i18n = createI18n({ legacy: false, locale: 'it', messages: { it: {} } })
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:p(.*)*', component: { template: '<div />' } }] })
  return mount(BarChart, { props, global: { plugins: [i18n, router] } })
}

const items: BarItem[] = [
  { key: 'BA', label: 'Bari', value: 200 },
  { key: 'LE', label: 'Lecce', value: 100 },
]

describe('BarChart', () => {
  it('scales bars to the largest value and labels them', () => {
    const wrapper = render({ title: 'Per provincia', items })
    const bars = wrapper.findAll('.bar-chart__bar')
    expect(bars[0].attributes('style')).toContain('* 1)')
    expect(bars[1].attributes('style')).toContain('* 0.5)')
    expect(wrapper.findAll('.bar-chart__value').map((v) => v.text())).toEqual(['200', '100'])
    expect(wrapper.find('.bar-chart__title').text()).toBe('Per provincia')
  })

  it('gives each bar an accessible name with value and share', () => {
    const wrapper = render({ title: 't', items, total: 400 })
    expect(wrapper.findAll('.bar-chart__hit')[0].attributes('aria-label')).toBe('Bari: 200 (50%)')
  })

  it('shows a tooltip on hover and focus', async () => {
    const wrapper = render({ title: 't', items })
    expect(wrapper.find('[role="tooltip"]').exists()).toBe(false)
    await wrapper.findAll('.bar-chart__hit')[1].trigger('mouseenter')
    expect(wrapper.find('[role="tooltip"]').text()).toContain('Lecce')
    await wrapper.findAll('.bar-chart__hit')[1].trigger('mouseleave')
    await wrapper.findAll('.bar-chart__hit')[0].trigger('focus')
    expect(wrapper.find('[role="tooltip"]').text()).toContain('Bari')
  })

  it('renders links when a target is given', () => {
    const wrapper = render({ title: 't', items: [{ ...items[0], to: '/companies?province=BA' }] })
    expect(wrapper.find('a.bar-chart__hit').attributes('href')).toBe('/companies?province=BA')
  })
})

import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AnimatedNumber from '../components/AnimatedNumber.vue'

afterEach(() => vi.unstubAllGlobals())

const format = (value: number) => String(Math.round(value))

function fakeFrames(reduce = false) {
  const callbacks: FrameRequestCallback[] = []
  vi.stubGlobal('matchMedia', () => ({ matches: reduce }))
  vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => callbacks.push(cb))
  vi.stubGlobal('cancelAnimationFrame', () => {})
  vi.spyOn(performance, 'now').mockReturnValue(0)
  return (time: number) => callbacks.splice(0).forEach((cb) => cb(time))
}

describe('AnimatedNumber', () => {
  it('counts up from zero and lands exactly on the value', async () => {
    const tick = fakeFrames()
    const wrapper = mount(AnimatedNumber, { props: { value: 1000, format, duration: 100 } })
    expect(wrapper.text()).toBe('0')
    tick(50)
    await wrapper.vm.$nextTick()
    expect(Number(wrapper.text())).toBeGreaterThan(500)
    expect(Number(wrapper.text())).toBeLessThan(1000)
    tick(100)
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toBe('1000')
  })

  it('shows the final value at once when the user prefers reduced motion', () => {
    fakeFrames(true)
    const wrapper = mount(AnimatedNumber, { props: { value: 1000, format } })
    expect(wrapper.text()).toBe('1000')
  })
})

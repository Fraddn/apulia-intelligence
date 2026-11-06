import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter } from 'vue-router'
import en from '../locales/en'

const SESSION = '/_allauth/browser/v1/auth/session'

function response(status: number, body: unknown) {
  return Promise.resolve({ ok: status < 400, status, json: async () => body })
}

const signedIn = { status: 200, data: { user: { id: 1, display: 'Mario Rossi', email: 'mario@example.com' } }, meta: { is_authenticated: true } }
const anonymous = { status: 401, data: { flows: [] }, meta: { is_authenticated: false } }

async function render(start = '/companies') {
  vi.resetModules()
  const { default: UserMenu } = await import('../components/UserMenu.vue')
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  const blank = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'login', component: blank },
      { path: '/:p(.*)*', component: blank },
    ],
  })
  await router.push(start)
  const wrapper = mount(UserMenu, { global: { plugins: [i18n, router] } })
  await flushPromises()
  return { wrapper, router }
}

beforeEach(() => {
  document.cookie = 'csrftoken=abc123'
})

afterEach(() => vi.unstubAllGlobals())

describe('UserMenu', () => {
  it('shows who is signed in', async () => {
    const fetchMock = vi.fn().mockReturnValue(response(200, signedIn))
    vi.stubGlobal('fetch', fetchMock)
    const { wrapper } = await render()
    expect(fetchMock.mock.calls[0][0]).toBe(SESSION)
    expect(wrapper.text()).toContain('Signed in as')
    expect(wrapper.find('.user-menu__name').text()).toBe('Mario Rossi')
    expect(wrapper.find('.user-menu__user').attributes('title')).toBe('mario@example.com')
  })

  it('links to the login page when signed out', async () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(response(401, anonymous)))
    const { wrapper } = await render('/signup')
    const link = wrapper.find('a.user-menu__login')
    expect(link.attributes('href')).toBe('/login')
    expect(link.text()).toBe('Log in')
  })

  it('hides the login link on the login page itself', async () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(response(401, anonymous)))
    const { wrapper } = await render('/login')
    expect(wrapper.find('a.user-menu__login').exists()).toBe(false)
  })

  it('logs out with the CSRF token and goes to the login page', async () => {
    const fetchMock = vi.fn().mockReturnValueOnce(response(200, signedIn)).mockReturnValueOnce(response(401, anonymous))
    vi.stubGlobal('fetch', fetchMock)
    const { wrapper, router } = await render()
    await wrapper.find('.user-menu__logout').trigger('click')
    await flushPromises()
    const [url, options] = fetchMock.mock.calls[1]
    expect(url).toBe(SESSION)
    expect(options.method).toBe('DELETE')
    expect(options.headers['X-CSRFToken']).toBe('abc123')
    expect(router.currentRoute.value.name).toBe('login')
    expect(wrapper.find('.user-menu__user').exists()).toBe(false)
  })

  it('renders nothing while the session is unknown or unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(Promise.reject(new Error('offline'))))
    const { wrapper } = await render()
    expect(wrapper.find('.user-menu').exists()).toBe(false)
  })
})

import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi, type Mock } from 'vitest'
import { createI18n } from 'vue-i18n'
import { createMemoryHistory, createRouter } from 'vue-router'
import en from '../locales/en'

const user = { id: 1, display: 'Mario', email: 'mario@example.com' }

function reply(status: number, body: unknown) {
  return { ok: status < 400, status, json: async () => body }
}

const SUMMARY = { companies: 42485, funded_projects: 15230, aid_grants: 98012 }

function stub(authFetch: Mock) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, options: unknown) =>
      url === '/api/summary' ? Promise.resolve(reply(200, SUMMARY)) : authFetch(url, options),
    ),
  )
  return authFetch
}

async function fillSignup(wrapper: Awaited<ReturnType<typeof mountView>>['wrapper'], second = 'Puglia-2026') {
  await wrapper.find('input[name=username]').setValue('maria.rossi')
  await wrapper.find('input[type=email]').setValue('new@example.com')
  const [password, confirm] = wrapper.findAll('input[type=password]')
  await password.setValue('Puglia-2026')
  await confirm.setValue(second)
}

async function mountView(file: string, path: string, props: Record<string, string> = {}) {
  vi.resetModules()
  const { default: View } = await import(`../views/${file}.vue`)
  const blank = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'dashboard', component: blank },
      { path: '/companies', name: 'companies', component: blank },
      { path: '/login', name: 'login', component: blank },
      { path: '/signup', name: 'signup', component: blank },
    ],
  })
  await router.push(path)
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  const wrapper = mount(View, { props, global: { plugins: [i18n, router] } })
  await flushPromises()
  return { wrapper, router }
}

afterEach(() => vi.unstubAllGlobals())

describe('LoginView', () => {
  it('logs in and goes to the requested page', async () => {
    const fetchMock = vi.fn().mockResolvedValue(reply(200, { data: { user }, meta: { is_authenticated: true } }))
    stub(fetchMock)
    const { wrapper, router } = await mountView('LoginView', '/login?next=/companies')
    await wrapper.find('input[name=username]').setValue('mario@example.com')
    await wrapper.find('input[type=password]').setValue('secret-password')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/_allauth/browser/v1/auth/login')
    expect(JSON.parse(options.body)).toEqual({ email: 'mario@example.com', password: 'secret-password' })
    expect(options.headers['Accept-Language']).toBe('en')
    expect(router.currentRoute.value.path).toBe('/companies')
  })

  it('logs in with a username when there is no @', async () => {
    const fetchMock = stub(vi.fn().mockResolvedValue(reply(200, { data: { user }, meta: { is_authenticated: true } })))
    const { wrapper, router } = await mountView('LoginView', '/login')
    await wrapper.find('input[name=username]').setValue('maria.rossi')
    await wrapper.find('input[type=password]').setValue('secret-password')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ username: 'maria.rossi', password: 'secret-password' })
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('shows username errors under the login field', async () => {
    const errors = [{ message: 'The username and/or password you specified are not correct.', code: 'username_password_mismatch', param: 'username' }]
    stub(vi.fn().mockResolvedValue(reply(400, { status: 400, errors })))
    const { wrapper } = await mountView('LoginView', '/login')
    await wrapper.find('input[name=username]').setValue('maria')
    await wrapper.find('input[type=password]').setValue('wrong')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('.auth-field__error').text()).toContain('username and/or password')
  })

  it('shows the server error under the right field', async () => {
    const errors = [{ message: 'The email address and/or password you specified are not correct.', code: 'email_password_mismatch', param: 'password' }]
    stub(vi.fn().mockResolvedValue(reply(400, { status: 400, errors })))
    const { wrapper, router } = await mountView('LoginView', '/login')
    await wrapper.find('input[name=username]').setValue('mario@example.com')
    await wrapper.find('input[type=password]').setValue('wrong')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('.auth-field__error').text()).toContain('not correct')
    expect(router.currentRoute.value.name).toBe('login')
  })

  it('asks to confirm the email when verification is pending', async () => {
    const body = { data: { flows: [{ id: 'verify_email', is_pending: true }] }, meta: { is_authenticated: false } }
    stub(vi.fn().mockResolvedValue(reply(401, body)))
    const { wrapper } = await mountView('LoginView', '/login')
    await wrapper.find('input[name=username]').setValue('new@example.com')
    await wrapper.find('input[type=password]').setValue('secret-password')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('.auth-notice--info').text()).toContain(en.auth.login.pendingVerification)
  })

  it('explains rate limiting and network failures', async () => {
    stub(vi.fn().mockResolvedValueOnce(reply(429, {})).mockRejectedValueOnce(new Error('offline')))
    const { wrapper } = await mountView('LoginView', '/login')
    await wrapper.find('input[name=username]').setValue('mario@example.com')
    await wrapper.find('input[type=password]').setValue('x')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('.auth-notice--error').text()).toBe(en.auth.errors.tooMany)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.find('.auth-notice--error').text()).toBe(en.auth.errors.offline)
  })
})

describe('SignupView', () => {
  it('blocks submission while the passwords differ', async () => {
    const fetchMock = stub(vi.fn())
    const { wrapper } = await mountView('SignupView', '/signup')
    await fillSignup(wrapper, 'Puglia-2027')
    expect(wrapper.text()).toContain(en.auth.passwordsDiffer)
    expect(wrapper.find('button[type=submit]').attributes('disabled')).toBeDefined()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('sends the username and tells the user to check their inbox', async () => {
    const body = { data: { flows: [{ id: 'verify_email', is_pending: true }] }, meta: { is_authenticated: false } }
    const fetchMock = stub(vi.fn().mockResolvedValue(reply(401, body)))
    const { wrapper } = await mountView('SignupView', '/signup')
    await fillSignup(wrapper)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    const [url, options] = fetchMock.mock.calls[0]
    expect(url).toBe('/_allauth/browser/v1/auth/signup')
    expect(JSON.parse(options.body)).toEqual({
      username: 'maria.rossi', email: 'new@example.com', password: 'Puglia-2026',
    })
    expect(wrapper.find('.auth__title').text()).toBe(en.auth.signup.checkInbox)
    expect(wrapper.text()).toContain('new@example.com')
  })

  it('needs a username, email and password', async () => {
    stub(vi.fn())
    const { wrapper } = await mountView('SignupView', '/signup')
    for (const field of ['username', 'email']) {
      await fillSignup(wrapper)
      expect(wrapper.find('button[type=submit]').attributes('disabled')).toBeUndefined()
      await wrapper.find(`input[name=${field}]`).setValue('')
      expect(wrapper.find('button[type=submit]').attributes('disabled')).toBeDefined()
    }
  })

  it('shows username errors from the server under the username field', async () => {
    const errors = [{ message: 'A user with that username already exists.', code: 'username_taken', param: 'username' }]
    stub(vi.fn().mockResolvedValue(reply(400, { errors })))
    const { wrapper } = await mountView('SignupView', '/signup')
    await fillSignup(wrapper)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    const field = wrapper.find('input[name=username]').element.closest('label')
    expect(field?.querySelector('.auth-field__error')?.textContent).toBe('A user with that username already exists.')
  })
})

describe('auth layout', () => {
  it('shows the brand panel with the public totals', async () => {
    stub(vi.fn())
    const { wrapper } = await mountView('LoginView', '/login')
    expect(wrapper.find('.auth__headline').text()).toBe(en.authBrand.headline)
    expect(wrapper.find('.auth__logo').element.tagName).toBe('DIV')
    expect(wrapper.find('.auth__brand a[href="/"]').exists()).toBe(false)
    const stats = wrapper.findAll('.auth__stat')
    expect(stats.map((stat) => stat.find('dt').text())).toEqual([
      en.authBrand.companies, en.authBrand.fundedProjects, en.authBrand.aidGrants,
    ])
    expect(stats[0].find('dd').text()).toBe('42,485')
    expect(wrapper.find('.auth__tools .lang-switch').exists()).toBe(true)
    expect(wrapper.find('.auth__tools .theme-toggle').exists()).toBe(true)
  })

  it('hides the totals when they cannot be loaded', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    const { wrapper } = await mountView('LoginView', '/login')
    expect(wrapper.find('.auth__stats').exists()).toBe(false)
    expect(wrapper.find('form').exists()).toBe(true)
  })
})

describe('VerifyEmailView', () => {
  it('logs the user in when the link is valid', async () => {
    const fetchMock = vi.fn().mockResolvedValue(reply(200, { data: { user }, meta: { is_authenticated: true } }))
    stub(fetchMock)
    const { router } = await mountView('VerifyEmailView', '/login', { token: 'abc' })
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ key: 'abc' })
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('confirms and asks to log in when opened in another browser', async () => {
    stub(vi.fn().mockResolvedValue(reply(401, { data: { flows: [] }, meta: { is_authenticated: false } })))
    const { wrapper } = await mountView('VerifyEmailView', '/login', { token: 'abc' })
    expect(wrapper.find('.auth__title').text()).toBe(en.auth.verify.confirmed)
  })

  it('explains an expired link', async () => {
    stub(vi.fn().mockResolvedValue(reply(400, { errors: [{ message: 'Invalid', code: 'invalid', param: 'key' }] })))
    const { wrapper } = await mountView('VerifyEmailView', '/login', { token: 'abc' })
    expect(wrapper.find('.auth__title').text()).toBe(en.auth.verify.invalid)
  })
})

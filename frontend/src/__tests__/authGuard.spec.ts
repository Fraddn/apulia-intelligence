import { afterEach, describe, expect, it, vi } from 'vitest'

const signedIn = { data: { user: { id: 1, display: 'Mario', email: 'mario@example.com' } }, meta: { is_authenticated: true } }
const anonymous = { data: { flows: [] }, meta: { is_authenticated: false } }

function session(status: number, body: unknown) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => body }))
}

async function freshRouter() {
  vi.resetModules()
  const module = await import('../router')
  return module
}

afterEach(() => vi.unstubAllGlobals())

describe('login guard', () => {
  it('sends anonymous visitors to the login page and remembers where they were going', async () => {
    session(401, anonymous)
    const { router } = await freshRouter()
    await router.push('/companies?province=BA')
    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.next).toBe('/companies?province=BA')
  })

  it('does not add next for the home page', async () => {
    session(401, anonymous)
    const { router } = await freshRouter()
    await router.push('/')
    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.next).toBeUndefined()
  })

  it('lets anonymous visitors open public pages', async () => {
    session(401, anonymous)
    const { router } = await freshRouter()
    for (const path of ['/signup', '/account/verify-email/abc']) {
      await router.push(path)
      expect(router.currentRoute.value.path).toBe(path)
    }
  })

  it('lets signed-in users in and keeps them away from login and signup', async () => {
    session(200, signedIn)
    const { router } = await freshRouter()
    await router.push('/companies')
    expect(router.currentRoute.value.name).toBe('companies')
    await router.push('/login?next=/companies/123')
    expect(router.currentRoute.value.path).toBe('/companies/123')
    await router.push('/signup')
    expect(router.currentRoute.value.name).toBe('dashboard')
  })

  it('only follows next to paths inside the app', async () => {
    const { safeNext } = await freshRouter()
    expect(safeNext('/companies')).toBe('/companies')
    expect(safeNext('//evil.example.com')).toBe('/')
    expect(safeNext('https://evil.example.com')).toBe('/')
    expect(safeNext(undefined)).toBe('/')
  })
})

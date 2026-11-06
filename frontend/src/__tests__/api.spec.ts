import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api, buildQuery } from '../api'

afterEach(() => vi.unstubAllGlobals())

function mockFetch(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => body })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('api', () => {
  it('builds queries without empty values', () => {
    expect(buildQuery({ search: 'alfa', province: '', section: 'J', page: 2 })).toBe('?search=alfa&section=J&page=2')
    expect(buildQuery({})).toBe('')
  })

  it('requests the company list with filters', async () => {
    const fetchMock = mockFetch(200, { items: [], count: 0 })
    await expect(api.companies({ province: 'BA', page: 1 })).resolves.toEqual({ items: [], count: 0 })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/companies?province=BA&page=1')
  })

  it('throws ApiError with the status', async () => {
    mockFetch(404, {})
    await expect(api.company('00000000000')).rejects.toMatchObject({ status: 404 })
    await expect(api.company('00000000000')).rejects.toBeInstanceOf(ApiError)
  })

  it('starts website discovery with POST', async () => {
    const fetchMock = mockFetch(200, { discovery: null, company: {} })
    await api.discover('01775410747')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/companies/01775410747/discover')
    expect(fetchMock.mock.calls[0][1].method).toBe('POST')
  })
})

describe('api auth', () => {
  it('sends the CSRF token on POST', async () => {
    document.cookie = 'csrftoken=abc123'
    const fetchMock = mockFetch(200, { discovery: null, company: {} })
    await api.discover('01775410747')
    expect(fetchMock.mock.calls[0][1].headers['X-CSRFToken']).toBe('abc123')
  })

  it('calls the unauthorized handler on 401', async () => {
    vi.resetModules()
    const fresh = await import('../api')
    const handler = vi.fn()
    fresh.onUnauthorized(handler)
    mockFetch(401, {})
    await expect(fresh.api.stats()).rejects.toMatchObject({ status: 401 })
    expect(handler).toHaveBeenCalledOnce()
  })
})

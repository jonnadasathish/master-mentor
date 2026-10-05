import { describe, expect, it, vi } from 'vitest'
import { ApiError, createApiClient } from '../src/api/client'

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('createApiClient', () => {
  it('returns the success envelope and joins paths onto the base URL', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(200, { data: { db: 'ok' }, meta: { ruleset_version: 'v1' } }))
    const client = createApiClient('/api/v1/', fetchImpl)

    const envelope = await client.get<{ db: string }>('/health')

    expect(envelope).toEqual({ data: { db: 'ok' }, meta: { ruleset_version: 'v1' } })
    expect(fetchImpl).toHaveBeenCalledWith('/api/v1/health', expect.objectContaining({ method: 'GET' }))
  })

  it('turns an error envelope into ApiError with code, status and details', async () => {
    const body = { error: { code: 'DEPENDENCY_UNAVAILABLE', message: 'Database is unreachable.', details: { db: 'unreachable' } } }
    const client = createApiClient('/api/v1', vi.fn().mockResolvedValue(jsonResponse(503, body)))

    const error = await client.get('/health').catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ code: 'DEPENDENCY_UNAVAILABLE', status: 503, details: { db: 'unreachable' } })
  })

  it('reports network failures as NETWORK_ERROR', async () => {
    const client = createApiClient('/api/v1', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(client.get('/health')).rejects.toMatchObject({ code: 'NETWORK_ERROR', status: null })
  })

  it('rejects non-JSON and non-envelope responses as INVALID_RESPONSE', async () => {
    const html = createApiClient('/api/v1', vi.fn().mockResolvedValue(new Response('<html>', { status: 502 })))
    await expect(html.get('/health')).rejects.toMatchObject({ code: 'INVALID_RESPONSE', status: 502 })

    const bare = createApiClient('/api/v1', vi.fn().mockResolvedValue(jsonResponse(200, { db: 'ok' })))
    await expect(bare.get('/health')).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
  })

  it('posts JSON bodies and encodes query parameters', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(201, { data: { id: 1 }, meta: {} }))
    const client = createApiClient('/api/v1', fetchImpl)
    await client.post('/problem-attempts', { outcome: 'PASS' })
    const [url, init] = fetchImpl.mock.calls[0]!
    expect(url).toBe('/api/v1/problem-attempts')
    expect(init).toMatchObject({ method: 'POST', body: '{"outcome":"PASS"}' })
    expect(init.headers['Content-Type']).toBe('application/json')

    fetchImpl.mockResolvedValue(jsonResponse(200, { data: [], meta: {} }))
    await client.get('/problems', { q: 'two sum', difficulty: '', skill: undefined })
    expect(fetchImpl.mock.calls[1]![0]).toBe('/api/v1/problems?q=two+sum')
  })
})

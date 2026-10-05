import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, type ApiClient } from '../src/api/client'
import { useErrorStore } from '../src/stores/errors'
import { useSystemStore } from '../src/stores/system'

beforeEach(() => setActivePinia(createPinia()))

describe('error store', () => {
  it('keeps API error codes and wraps other errors as UI_ERROR', () => {
    const store = useErrorStore()
    store.report(new ApiError('NOT_FOUND', 'Missing.', 404), 'api')
    store.report(new Error('boom'), 'component')
    expect(store.errors.map((e) => e.code)).toEqual(['NOT_FOUND', 'UI_ERROR'])
  })

  it('keeps only the five most recent errors and can dismiss one', () => {
    const store = useErrorStore()
    for (let i = 0; i < 7; i++) store.report(new Error(`e${i}`), 'test')
    expect(store.errors.map((e) => e.message)).toEqual(['e2', 'e3', 'e4', 'e5', 'e6'])
    store.dismiss(store.errors[0]!.id)
    expect(store.errors).toHaveLength(4)
  })
})

describe('system store', () => {
  it('stores health data and meta on success', async () => {
    const client: ApiClient = {
      post: vi.fn(),
      get: vi.fn().mockResolvedValue({ data: { db: 'ok', ruleset_version: 'v1', seed_version: null }, meta: { ruleset_version: 'v1' } }),
    }
    const store = useSystemStore()
    await store.fetchHealth(client)
    expect(store.health?.db).toBe('ok')
    expect(store.meta?.ruleset_version).toBe('v1')
    expect(store.error).toBeNull()
    expect(store.loading).toBe(false)
  })

  it('stores the ApiError when the backend is unhealthy', async () => {
    const client: ApiClient = { post: vi.fn(), get: vi.fn().mockRejectedValue(new ApiError('DEPENDENCY_UNAVAILABLE', 'Database is unreachable.', 503)) }
    const store = useSystemStore()
    await store.fetchHealth(client)
    expect(store.health).toBeNull()
    expect(store.error?.code).toBe('DEPENDENCY_UNAVAILABLE')
  })
})

describe('cached resources', () => {
  it('serves the cache, shares one in-flight request and refetches stale data on request', async () => {
    const { createResource } = await import('../src/stores/resource')
    let calls = 0
    const resource = createResource(async () => ++calls)
    await Promise.all([resource.ensure(), resource.ensure()])
    expect(calls).toBe(1)
    await resource.ensure()
    expect(calls).toBe(1)
    await new Promise((resolve) => setTimeout(resolve, 5))
    await resource.ensure(1)
    expect(calls).toBe(2)
    await resource.refresh()
    expect(resource.data.value).toBe(3)
  })

  it('keeps the old data when a refresh fails and records the error', async () => {
    const { createResource } = await import('../src/stores/resource')
    let fail = false
    const resource = createResource(async () => {
      if (fail) throw new Error('down')
      return 'ok'
    })
    await resource.ensure()
    fail = true
    await resource.refresh()
    expect(resource.data.value).toBe('ok')
    expect((resource.error.value as Error).message).toBe('down')
  })
})

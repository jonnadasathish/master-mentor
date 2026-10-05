import { vi } from 'vitest'
import { ApiError } from '../src/api/client'

type Handler = unknown | ((params?: Record<string, unknown>) => unknown)

/**
 * Serves the mocked `api.get` from a path -> response map (the response is the envelope's `data`).
 * A value that is an Error rejects, so error states can be exercised. Unknown paths reject with 404.
 */
export function serve(api: { get: ReturnType<typeof vi.fn> }, routes: Record<string, Handler>): void {
  api.get.mockImplementation((path: string, params?: Record<string, unknown>) => {
    const handler = routes[path]
    if (handler === undefined) return Promise.reject(new ApiError('NOT_FOUND', `no fixture for ${path}`, 404))
    const value = typeof handler === 'function' ? (handler as (p?: Record<string, unknown>) => unknown)(params) : handler
    if (value instanceof Error) return Promise.reject(value)
    return Promise.resolve({ data: value, meta: {} })
  })
}

export const networkDown = () => new ApiError('NETWORK_ERROR', 'The server could not be reached.', null)

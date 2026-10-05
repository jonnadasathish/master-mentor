import type { Envelope, ErrorEnvelope } from './types'

/** Client-side error codes in addition to the server's (network failures, malformed responses). */
export const CLIENT_ERROR_CODES = { NETWORK_ERROR: 'NETWORK_ERROR', INVALID_RESPONSE: 'INVALID_RESPONSE' } as const

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number | null,
    readonly details: Record<string, unknown> = {},
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export interface ApiClient {
  get<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<Envelope<T>>
  post<T>(path: string, body: unknown): Promise<Envelope<T>>
}

/** The full HTTP client used by pages (components only need ``ApiClient``). */
export interface HttpClient extends ApiClient {
  patch<T>(path: string, body: unknown): Promise<Envelope<T>>
}

function withQuery(path: string, params?: Record<string, string | number | boolean | undefined>): string {
  if (!params) return path
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') query.set(key, String(value))
  }
  const text = query.toString()
  return text ? `${path}?${text}` : path
}

function isEnvelope<T>(body: unknown): body is Envelope<T> {
  return typeof body === 'object' && body !== null && 'data' in body && 'meta' in body
}

function isErrorEnvelope(body: unknown): body is ErrorEnvelope {
  if (typeof body !== 'object' || body === null || !('error' in body)) return false
  const error = (body as { error: unknown }).error
  return typeof error === 'object' && error !== null && 'code' in error && 'message' in error
}

/** Thin fetch wrapper: returns the success envelope or throws ApiError. No business logic. */
export function createApiClient(baseUrl: string, fetchImpl: typeof fetch = fetch): HttpClient {
  const root = baseUrl.replace(/\/+$/, '')

  async function request<T>(path: string, init: RequestInit): Promise<Envelope<T>> {
    let response: Response
    try {
      const headers: Record<string, string> = { Accept: 'application/json' }
      if (init.body !== undefined) headers['Content-Type'] = 'application/json'
      response = await fetchImpl(`${root}${path}`, { ...init, headers })
    } catch {
      throw new ApiError(CLIENT_ERROR_CODES.NETWORK_ERROR, 'The server could not be reached.', null)
    }

    let body: unknown
    try {
      body = await response.json()
    } catch {
      throw new ApiError(CLIENT_ERROR_CODES.INVALID_RESPONSE, 'The server returned a non-JSON response.', response.status)
    }

    if (!response.ok) {
      if (isErrorEnvelope(body)) {
        const { code, message, details } = body.error
        throw new ApiError(code, message, response.status, details ?? {})
      }
      throw new ApiError(CLIENT_ERROR_CODES.INVALID_RESPONSE, `Unexpected error response (${response.status}).`, response.status)
    }
    if (!isEnvelope<T>(body)) {
      throw new ApiError(CLIENT_ERROR_CODES.INVALID_RESPONSE, 'The server response is not an envelope.', response.status)
    }
    return body
  }

  return {
    get: <T>(path: string, params?: Record<string, string | number | boolean | undefined>) =>
      request<T>(withQuery(path, params), { method: 'GET' }),
    post: <T>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
    patch: <T>(path: string, body: unknown) => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  }
}

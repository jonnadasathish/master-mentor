import { ApiError } from '../api/client'

export interface FriendlyError {
  title: string
  body: string
}

/** Human wording for failures. The technical code stays available under "Technical details". */
export function friendlyError(error: unknown): FriendlyError {
  if (error instanceof ApiError) {
    if (error.code === 'NETWORK_ERROR' || error.status === null || error.status === 503 || error.status === 502 || error.status === 504) {
      return {
        title: "Master Mentor can't reach the preparation engine right now.",
        body: 'Your data is safe. Check that the app is running, then try again.',
      }
    }
    if (error.status === 404) {
      return { title: "We couldn't find that.", body: 'It may have been removed or the link may be out of date.' }
    }
    if (error.status === 409) {
      return { title: "That can't be done right now.", body: error.message }
    }
    if (error.status === 422) {
      return { title: 'Something in that request needs a second look.', body: error.message }
    }
    if (error.status >= 500) {
      return { title: 'Something went wrong on our side.', body: 'Please try again in a moment. Your data is safe.' }
    }
  }
  return { title: 'Something went wrong.', body: 'Please try again. If it keeps happening, check Settings → Developer.' }
}

/** Same wording from a stored error code (the global error store keeps codes, not exceptions). */
export function friendlyFromCode(code: string): FriendlyError {
  if (code === 'NETWORK_ERROR' || code === 'BACKEND_UNAVAILABLE') {
    return friendlyError(new ApiError('NETWORK_ERROR', '', null))
  }
  if (code === 'NOT_FOUND') return friendlyError(new ApiError(code, '', 404))
  return { title: 'Something went wrong.', body: 'Please try again. Your data is safe.' }
}

import { ref, shallowRef } from 'vue'

/**
 * A cached, de-duplicated server resource. `ensure()` fetches once and then serves the cache (so navigating between
 * pages does not refetch); `refresh()` always refetches (after a write); concurrent calls share one request.
 * `ensure(maxAgeMs)` also refetches data older than that, for pages that must not show yesterday's day.
 */
export function createResource<T>(fetcher: () => Promise<T>) {
  const data = shallowRef<T | null>(null)
  const error = shallowRef<unknown>(null)
  const loading = ref(false)
  let inflight: Promise<void> | null = null
  let fetchedAt = 0

  function refresh(): Promise<void> {
    if (inflight) return inflight
    loading.value = true
    inflight = fetcher()
      .then((value) => {
        data.value = value
        error.value = null
        fetchedAt = Date.now()
      })
      .catch((caught: unknown) => {
        error.value = caught
      })
      .finally(() => {
        loading.value = false
        inflight = null
      })
    return inflight
  }

  async function ensure(maxAgeMs = Number.POSITIVE_INFINITY): Promise<void> {
    if (data.value !== null && Date.now() - fetchedAt <= maxAgeMs) return
    await refresh()
  }

  function reset(): void {
    data.value = null
    error.value = null
    fetchedAt = 0
  }

  return { data, error, loading, ensure, refresh, reset }
}

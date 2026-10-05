import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ApiClient } from '../api/client'
import { ApiError } from '../api/client'
import type { HealthData, Meta } from '../api/types'

/** Backend connectivity status (used by the Status page). */
export const useSystemStore = defineStore('system', () => {
  const health = ref<HealthData | null>(null)
  const meta = ref<Meta | null>(null)
  const error = ref<ApiError | null>(null)
  const loading = ref(false)

  async function fetchHealth(client: ApiClient): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const envelope = await client.get<HealthData>('/health')
      health.value = envelope.data
      meta.value = envelope.meta
    } catch (caught) {
      health.value = null
      error.value = caught instanceof ApiError ? caught : new ApiError('UI_ERROR', String(caught), null)
    } finally {
      loading.value = false
    }
  }

  return { health, meta, error, loading, fetchHealth }
})

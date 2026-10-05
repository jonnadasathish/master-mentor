import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ApiClient } from '../api/client'
import { ApiError } from '../api/client'
import type { CatalogSummary, ComponentNode, Roadmap, RoleProfile, SkillDetail } from '../api/types'

/** Internal catalog verification data (Slice 2). Displays server data only; no calculations. */
export const useCatalogStore = defineStore('catalog', () => {
  const summary = ref<CatalogSummary | null>(null)
  const tree = ref<ComponentNode[]>([])
  const profile = ref<RoleProfile | null>(null)
  const roadmap = ref<Roadmap | null>(null)
  const selected = ref<SkillDetail | null>(null)
  const error = ref<ApiError | null>(null)
  const loading = ref(false)

  function capture(caught: unknown): void {
    error.value = caught instanceof ApiError ? caught : new ApiError('UI_ERROR', String(caught), null)
  }

  async function fetchAll(client: ApiClient): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const [s, t, p, r] = await Promise.all([
        client.get<CatalogSummary>('/catalog'),
        client.get<ComponentNode[]>('/catalog/tree'),
        client.get<RoleProfile>('/catalog/role-profile'),
        client.get<Roadmap>('/catalog/roadmap'),
      ])
      summary.value = s.data
      tree.value = t.data
      profile.value = p.data
      roadmap.value = r.data
    } catch (caught) {
      capture(caught)
    } finally {
      loading.value = false
    }
  }

  async function selectSkill(client: ApiClient, key: string): Promise<void> {
    try {
      selected.value = (await client.get<SkillDetail>(`/catalog/skills/${encodeURIComponent(key)}`)).data
    } catch (caught) {
      capture(caught)
    }
  }

  return { summary, tree, profile, roadmap, selected, error, loading, fetchAll, selectSkill }
})

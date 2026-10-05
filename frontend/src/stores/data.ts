import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api'
import type {
  ComponentNode, CurrentState, PersonalRoadmap, StartingProfile,
  ActiveGoal, ProblemAttempt, ProblemSummary, Baseline, GapDetail, MockRecord, MockSummary, Readiness, ReadinessPoint, RevisionList, RoadmapView,
  Settings, SkillWithState, Today, WeekContext, WeeklyReview, LearningTrack, LearningTrackDetail,
} from '../api/types'
import { prettyKey } from '../presentation/format'
import { createResource } from './resource'

/** Server read models, cached once and shared by every page (no duplicate fetching). Display data only. */

export const useSkillsStore = defineStore('skills', () => {
  const resource = createResource(async () => (await api.get<SkillWithState[]>('/skills')).data)
  const list = computed(() => resource.data.value ?? [])
  const byKey = computed(() => new Map(list.value.map((s) => [s.key, s])))
  function nameOf(key: string): string {
    return byKey.value.get(key)?.name ?? prettyKey(key)
  }
  function componentOf(key: string): string | null {
    return byKey.value.get(key)?.component ?? null
  }
  return { ...resource, list, byKey, nameOf, componentOf }
})

export const useReadinessStore = defineStore('readiness', () => {
  const resource = createResource(async () => (await api.get<Readiness>('/readiness')).data)
  const history = createResource(async () => (await api.get<ReadinessPoint[]>('/readiness/history')).data)
  return { ...resource, history }
})

export const useTodayStore = defineStore('today', () => {
  const resource = createResource(async () => (await api.get<Today>('/today')).data)
  const week = createResource(async () => (await api.get<WeekContext>('/today/week')).data)
  const baseline = createResource(async () => (await api.get<Baseline>('/baseline')).data)
  return { ...resource, week, baseline }
})

/** Self-reported context + target + first-run flag (D-080). The guard reads it before every navigation. */
export const useStartingProfileStore = defineStore('starting-profile', () => {
  const resource = createResource(async () => (await api.get<StartingProfile>('/profile')).data)
  return { ...resource }
})

export const usePersonalStore = defineStore('personal', () => {
  const roadmap = createResource(async () => (await api.get<PersonalRoadmap>('/roadmap/personal')).data)
  const state = createResource(async () => (await api.get<CurrentState>('/profile/state')).data)
  return { roadmap, state }
})

export const useProfileStore = defineStore('profile', () => {
  const settings = createResource(async () => (await api.get<Settings>('/settings')).data)
  const goal = createResource(async () => {
    try {
      return (await api.get<ActiveGoal>('/goals/active')).data
    } catch {
      return null as ActiveGoal | null // no goal yet is a normal state, not an error
    }
  })
  return { settings, goal }
})

export const useRevisionStore = defineStore('revision', () => {
  const resource = createResource(async () => (await api.get<RevisionList>('/revisions')).data)
  return { ...resource }
})

export const useMocksStore = defineStore('mocks', () => {
  const summary = createResource(async () => (await api.get<MockSummary>('/mocks/summary')).data)
  const list = createResource(async () => (await api.get<MockRecord[]>('/mocks', { limit: 20 })).data)
  return { summary, list }
})

export const useRoadmapStore = defineStore('roadmap', () => {
  const resource = createResource(async () => (await api.get<RoadmapView>('/roadmap')).data)
  return { ...resource }
})

export const useReviewStore = defineStore('review', () => {
  const latest = createResource(async () => (await api.get<WeeklyReview>('/weekly-reviews/latest')).data)
  const all = createResource(async () => (await api.get<WeeklyReview[]>('/weekly-reviews')).data)
  return { latest, all }
})

export interface CatalogSkill {
  key: string
  name: string
  group: string
  component: string
  is_pattern: boolean
  tier: string | null
  required: boolean | null
}

/** Static catalog facts the skills read model does not carry (e.g. which skills are patterns). */
export const useCatalogSkillsStore = defineStore('catalog-skills', () => {
  const resource = createResource(async () => (await api.get<CatalogSkill[]>('/catalog/skills')).data)
  return { ...resource }
})

export const useCatalogTreeStore = defineStore('catalog-tree', () => {
  const resource = createResource(async () => (await api.get<ComponentNode[]>('/catalog/tree')).data)
  return { ...resource }
})

export const useProblemsStore = defineStore('problems', () => {
  const resource = createResource(async () => (await api.get<ProblemSummary[]>('/problems')).data)
  const titleOf = (id: string | number) =>
    (resource.data.value ?? []).find((p) => String(p.id) === String(id))?.title ?? null
  return { ...resource, titleOf }
})

export const useAttemptsStore = defineStore('attempts', () => {
  const resource = createResource(async () => (await api.get<ProblemAttempt[]>('/problem-attempts', { limit: 8 })).data)
  return { ...resource }
})

/** Gap detail (with metrics) is fetched per skill on demand; cached by key for the session. */
export const useGapDetailStore = defineStore('gap-detail', () => {
  const cache = new Map<string, GapDetail>()
  async function load(key: string): Promise<GapDetail> {
    const hit = cache.get(key)
    if (hit) return hit
    const detail = (await api.get<GapDetail>(`/gaps/${encodeURIComponent(key)}`)).data
    cache.set(key, detail)
    return detail
  }
  function clear(): void {
    cache.clear()
  }
  return { load, clear }
})

/** Curriculum (tracks with per-skill progress) and track details, cached per track for the session. */
export const useLearningStore = defineStore('learning', () => {
  const curriculum = createResource(async () => (await api.get<LearningTrack[]>('/learning/curriculum')).data)
  const tracks = ref(new Map<string, LearningTrackDetail>())
  async function track(key: string, force = false): Promise<LearningTrackDetail> {
    const hit = tracks.value.get(key)
    if (hit && !force) return hit
    const detail = (await api.get<LearningTrackDetail>(`/learning/tracks/${encodeURIComponent(key)}`)).data
    tracks.value = new Map(tracks.value).set(key, detail)
    return detail
  }
  async function refresh(): Promise<void> {
    const loaded = [...tracks.value.keys()]
    await Promise.all([...(curriculum.data.value ? [curriculum.refresh()] : []), ...loaded.map((k) => track(k, true))])
  }
  return { curriculum, tracks, track, refresh }
})

/**
 * After any observation write the engines re-ran: refresh whatever is already loaded (and nothing else), so every
 * page shows the new server state without refetching data nobody has opened.
 */
export async function refreshDerivedData(): Promise<void> {
  const today = useTodayStore()
  const skills = useSkillsStore()
  const readiness = useReadinessStore()
  const revision = useRevisionStore()
  const mocks = useMocksStore()
  const roadmap = useRoadmapStore()
  const problems = useProblemsStore()
  const attempts = useAttemptsStore()
  const personal = usePersonalStore()
  const startingProfile = useStartingProfileStore()
  const learning = useLearningStore()
  useGapDetailStore().clear()
  const loaded: Promise<void>[] = []
  if (today.data) loaded.push(today.refresh())
  if (today.week.data) loaded.push(today.week.refresh())
  if (today.baseline.data) loaded.push(today.baseline.refresh())
  if (skills.data) loaded.push(skills.refresh())
  if (readiness.data) loaded.push(readiness.refresh())
  if (readiness.history.data) loaded.push(readiness.history.refresh())
  if (revision.data) loaded.push(revision.refresh())
  if (mocks.summary.data) loaded.push(mocks.summary.refresh())
  if (mocks.list.data) loaded.push(mocks.list.refresh())
  if (roadmap.data) loaded.push(roadmap.refresh())
  if (problems.data) loaded.push(problems.refresh())
  if (attempts.data) loaded.push(attempts.refresh())
  if (personal.roadmap.data) loaded.push(personal.roadmap.refresh())
  if (personal.state.data) loaded.push(personal.state.refresh())
  if (startingProfile.data) loaded.push(startingProfile.refresh())
  loaded.push(learning.refresh())
  await Promise.all(loaded)
}

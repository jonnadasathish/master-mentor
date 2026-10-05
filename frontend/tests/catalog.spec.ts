import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { ApiError, type ApiClient } from '../src/api/client'
import { useCatalogStore } from '../src/stores/catalog'

const FIXTURES: Record<string, unknown> = {
  '/catalog': {
    seed_version: 'seed-v1',
    catalog_fingerprint: 'f'.repeat(64),
    loaded_at: '2026-10-04T12:00:00Z',
    versions: { catalog_version: 'seed-v1+7546c05d7c71' },
    files: [],
    counts: { skills: 133, skill_prerequisites: 134, problems: 44, mission_templates: 86, roadmap_milestones: 18 },
  },
  '/catalog/tree': [
    { component: 'dsa', groups: [{ key: 'dsa.graphs', name: 'Graphs', component: 'dsa', skills: ['graph.traversal'] }] },
  ],
  '/catalog/role-profile': {
    profile_key: 'backend_fullstack_sde2',
    name: 'SWE Backend/Full-Stack',
    seniority: 'MID_SDE2',
    config: { components: [{ key: 'dsa', name: 'DSA', weight: 25, gate: 72, stretch: 80, track: 'dsa_coding' }] },
    tier_counts: { T1: 35, T2: 56, T3: 32, T4: 10 },
    required_skill_count: 123,
    critical_skills: ['graph.traversal'],
  },
  '/catalog/roadmap': {
    tracks: [{ track: 'dsa_coding', milestones: [{ key: 'DSA-1', name: 'Foundations', position: 1, skills: ['a.b'] }] }],
    baseline_items: [{ key: 'M0-B01', name: 'Sweep', minutes: 15 }],
    baseline_total_minutes: 15,
  },
  '/catalog/skills/graph.traversal': {
    key: 'graph.traversal', name: 'Graph traversal', group: 'dsa.graphs', component: 'dsa', is_pattern: true,
    tier: 'T1', importance: 100, target_score: 80, floor_score: 65, required: true,
    prerequisites: [{ key: 'trees.traversal', name: 'Trees', min_score: 45, depth: null }],
    dependents: [], milestone: { key: 'DSA-2', name: 'Core', track: 'dsa_coding' }, problem_count: 5,
  },
}

function fakeClient(failing?: string): ApiClient {
  return {
    get: vi.fn(async (path: string) => {
      if (path === failing) throw new ApiError('INVALID_STATE', 'The catalog is not loaded. Run `make seed`.', 409)
      return { data: FIXTURES[path], meta: { seed_version: 'seed-v1' } }
    }) as ApiClient['get'],
    post: vi.fn() as ApiClient['post'],
  }
}

vi.mock('../src/api', () => ({ api: fakeClient() }))

beforeEach(() => setActivePinia(createPinia()))

describe('catalog store', () => {
  it('loads summary, tree, role profile and roadmap', async () => {
    const store = useCatalogStore()
    await store.fetchAll(fakeClient())
    expect(store.summary?.counts.skills).toBe(133)
    expect(store.tree[0]?.groups[0]?.skills).toEqual(['graph.traversal'])
    expect(store.profile?.required_skill_count).toBe(123)
    expect(store.roadmap?.tracks[0]?.milestones[0]?.key).toBe('DSA-1')
    expect(store.error).toBeNull()
  })

  it('surfaces the not-loaded error envelope', async () => {
    const store = useCatalogStore()
    await store.fetchAll(fakeClient('/catalog'))
    expect(store.error?.code).toBe('INVALID_STATE')
  })

  it('selects a skill with its prerequisites', async () => {
    const store = useCatalogStore()
    await store.selectSkill(fakeClient(), 'graph.traversal')
    expect(store.selected?.prerequisites.map((p) => p.key)).toEqual(['trees.traversal'])
  })
})

describe('CatalogView', () => {
  it('renders the catalog summary, role profile, tree and roadmap', async () => {
    const { default: CatalogView } = await import('../src/views/CatalogView.vue')
    const wrapper = mount(CatalogView)
    await vi.waitFor(() => expect(wrapper.find('[data-testid="skill-count"]').exists()).toBe(true))
    expect(wrapper.find('[data-testid="skill-count"]').text()).toBe('133')
    expect(wrapper.find('[data-testid="problem-count"]').text()).toBe('44')
    expect(wrapper.find('[data-testid="profile-name"]').text()).toContain('123')
    expect(wrapper.findAll('[data-testid="tree-component"]')).toHaveLength(1)
    expect(wrapper.findAll('[data-testid="roadmap-track"]')).toHaveLength(1)

    await wrapper.find('button.skill').trigger('click')
    await vi.waitFor(() => expect(wrapper.find('[data-testid="skill-detail"]').exists()).toBe(true))
    await nextTick()
    expect(wrapper.find('[data-testid="skill-detail"]').text()).toContain('trees.traversal')
  })
})

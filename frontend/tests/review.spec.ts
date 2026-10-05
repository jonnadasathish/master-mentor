import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }))
vi.mock('../src/api', () => ({ api }))

import WeeklyReviewPanel from '../src/components/WeeklyReviewPanel.vue'

const REVIEW = {
  id: 1, week_start: '2026-10-26', reflection: null, reflected_at: null,
  metrics: {
    week_start: '2026-10-26', week_end: '2026-11-01', active_days: 4, planned_minutes: 300, completed_minutes: 240,
    plan_completion_pct: 80, revision_completion_pct: 50, minutes_by_track: { dsa_coding: { minutes: 150, weekly_target: 210 } },
    top_gaps: [], gap_changes: [], strongest_improvement: { skill_key: 'graph.traversal', before: 44, after: 59, delta: 15 },
    biggest_regression: null, readiness: { start: { state: 'FOUNDATION', weighted_score: 60 }, end: { state: 'DEVELOPING', weighted_score: 66 },
      new_blockers: [], cleared_blockers: [] }, mocks: [], backlog_minutes: 35,
  },
  next_focus: { top_gaps: [{ skill_key: 'sd.caching', status: 'HIGH', priority: 50 }], tracks_below_floor: ['cs'], stop_list: [] },
}

describe('WeeklyReviewPanel', () => {
  it('renders stored metrics and saves the reflection', async () => {
    api.get.mockResolvedValue({ data: REVIEW, meta: {} })
    api.post.mockResolvedValue({ data: { ...REVIEW, reflection: { improved: 'graphs' } }, meta: {} })
    const wrapper = mount(WeeklyReviewPanel)
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('Plan: 240 / 300 min (80%)')
    expect(text).toContain('Readiness: FOUNDATION → DEVELOPING')
    expect(text).toContain('Strongest improvement: graph.traversal 44 → 59')
    expect(text).toContain('Behind on: cs')
    await wrapper.find('[data-testid="reflection-improved"]').setValue('graphs')
    await wrapper.find('[data-testid="reflection-form"]').trigger('submit')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/weekly-reviews/2026-10-26/reflection', { improved: 'graphs' })
    expect(wrapper.text()).toContain('Reflection saved.')
  })
})

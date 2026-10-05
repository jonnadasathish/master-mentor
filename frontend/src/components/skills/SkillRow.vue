<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { SkillWithState } from '../../api/types'
import { stateFromGapStatus } from '../../presentation/language'
import ProgressBar from '../common/ProgressBar.vue'
import StatusPill from '../common/StatusPill.vue'

/** One skill as a compact row: name, score against target, and its gap state. Values are the server's. */
defineProps<{ skill: SkillWithState }>()
const TONE = { critical: 'critical', high: 'high', medium: 'medium', healthy: 'healthy', calibration: 'calibration' } as const
function tone(skill: SkillWithState) {
  return TONE[stateFromGapStatus(skill.gap?.status ?? 'UNASSESSED') as keyof typeof TONE] ?? 'accent'
}
</script>

<template>
  <RouterLink
    :to="{ name: 'skill', params: { key: skill.key } }"
    class="skill-row"
    :data-testid="`skill-row-${skill.key}`"
  >
    <span class="name">{{ skill.name }}</span>
    <span class="bar">
      <ProgressBar
        :value="skill.state.effective_score"
        :max="skill.target_score"
        :label="`${skill.name} score against target`"
        size="sm"
        :tone="tone(skill)"
      />
    </span>
    <span class="score tabular"><strong>{{ skill.state.effective_score ?? '—' }}</strong> / {{ skill.target_score ?? '—' }}</span>
    <StatusPill
      v-if="skill.gap"
      class="pill"
      :state="stateFromGapStatus(skill.gap.status)"
    />
  </RouterLink>
</template>

<style scoped>
.skill-row {
  display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(5rem, 1fr) 5.2rem 7.5rem; align-items: center; gap: var(--s-4);
  padding: var(--s-3) var(--s-4); color: inherit; text-decoration: none; border-radius: var(--r-md);
  transition: background var(--t-fast) var(--ease);
}
.skill-row:hover { background: var(--surface-2); text-decoration: none; }
.name { font-weight: 560; overflow: hidden; text-overflow: ellipsis; }
.score { color: var(--text-3); font-size: var(--fs-sm); text-align: right; }
.score strong { color: var(--text); }
.pill { justify-self: end; }
@media (max-width: 767px) {
  .skill-row { grid-template-columns: minmax(0, 1fr) auto; gap: var(--s-1) var(--s-3); }
  .bar { grid-column: 1 / -1; order: 3; }
  .pill { grid-row: 1; grid-column: 2; }
  .score { grid-row: 2; grid-column: 2; }
  .name { grid-row: 1; grid-column: 1; }
}
</style>

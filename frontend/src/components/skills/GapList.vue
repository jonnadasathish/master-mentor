<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { Today } from '../../api/types'
import { GAP_TYPE_LABEL, stateFromGapStatus } from '../../presentation/language'
import { reasonPhrases } from '../../presentation/reasons'
import { useSkillsStore } from '../../stores/data'
import Icon from '../common/Icon.vue'
import ProgressBar from '../common/ProgressBar.vue'
import StatusPill from '../common/StatusPill.vue'

/** The few gaps that matter most, in the engine's own order. Scores and targets come from the skills read model. */
const props = defineProps<{ gaps: Today['top_gaps']; limit?: number }>()
const skills = useSkillsStore()

const rows = computed(() =>
  props.gaps.slice(0, props.limit ?? 5).map((g) => {
    const skill = skills.byKey.get(g.skill_key)
    const score = skill?.state.effective_score ?? skill?.state.score ?? null
    return {
      key: g.skill_key,
      name: skills.nameOf(g.skill_key),
      status: g.status,
      score,
      target: skill?.target_score ?? null,
      type: g.primary_gap_type ? (GAP_TYPE_LABEL[g.primary_gap_type] ?? null) : null,
      reason: reasonPhrases(g.reason_codes, skills.nameOf, 1)[0] ?? null,
    }
  }),
)
const TONE = { critical: 'critical', high: 'high', medium: 'medium' } as const
function tone(status: string) {
  return TONE[stateFromGapStatus(status) as keyof typeof TONE] ?? 'accent'
}
</script>

<template>
  <ul
    class="gaps"
    data-testid="top-gaps"
  >
    <li
      v-for="r in rows"
      :key="r.key"
    >
      <RouterLink
        :to="{ name: 'skill', params: { key: r.key } }"
        class="gap"
        :data-testid="`gap-${r.key}`"
      >
        <div class="top">
          <span class="name">{{ r.name }}</span>
          <StatusPill :state="stateFromGapStatus(r.status)" />
        </div>
        <div class="score">
          <span class="tabular value"><strong>{{ r.score ?? '—' }}</strong> / {{ r.target ?? '—' }}</span>
          <ProgressBar
            :value="r.score"
            :max="r.target"
            :label="`${r.name}: ${r.score ?? 'not measured'} of ${r.target ?? 'unknown'}`"
            :tone="tone(r.status)"
          />
        </div>
        <p
          v-if="r.type || r.reason"
          class="why"
        >
          <template v-if="r.type">
            <strong>{{ r.type }}.</strong>
          </template>
          {{ r.reason }}
        </p>
        <Icon
          class="go"
          name="chevron-right"
          :size="16"
        />
      </RouterLink>
    </li>
  </ul>
</template>

<style scoped>
.gaps { display: grid; gap: var(--s-3); }
.gap {
  position: relative; display: grid; gap: var(--s-2); padding: var(--s-4) var(--s-5); background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r-lg); color: inherit; text-decoration: none; box-shadow: var(--shadow-sm);
  transition: box-shadow var(--t-base) var(--ease), border-color var(--t-base) var(--ease), transform var(--t-base) var(--ease);
}
.gap:hover { box-shadow: var(--shadow-md); border-color: var(--border-strong); text-decoration: none; transform: translateY(-1px); }
.top { display: flex; align-items: center; justify-content: space-between; gap: var(--s-3); padding-right: var(--s-5); }
.name { font-weight: 650; font-size: var(--fs-md); letter-spacing: -0.01em; }
.score { display: grid; grid-template-columns: 5.5rem minmax(0, 1fr); align-items: center; gap: var(--s-3); }
.value { font-size: var(--fs-sm); color: var(--text-3); }
.value strong { color: var(--text); font-size: var(--fs-md); }
.why { font-size: var(--fs-sm); color: var(--text-2); }
.go { position: absolute; right: var(--s-4); top: var(--s-4); color: var(--text-3); }
</style>

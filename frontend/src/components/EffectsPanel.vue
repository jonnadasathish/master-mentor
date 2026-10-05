<script setup lang="ts">
import type { Effects } from '../api/types'
import SkillDeltas from './SkillDeltas.vue'

/** The feedback loop after an observation (UI_SPEC §3): skill, gap, revision and readiness changes. */
defineProps<{ effects: Effects }>()
</script>

<template>
  <section
    class="effects"
    aria-label="What changed"
    data-testid="effects-panel"
  >
    <h3>What changed</h3>
    <SkillDeltas :deltas="effects.skill_deltas" />
    <ul v-if="effects.gap_deltas?.length">
      <li
        v-for="g in effects.gap_deltas"
        :key="g.skill_key"
      >
        Gap {{ g.skill_key }}: {{ g.before ? `${g.before.status.toLowerCase()} ${g.before.priority}` : '—' }} →
        {{ g.after.status.toLowerCase() }} {{ g.after.priority }}
      </li>
    </ul>
    <ul v-if="effects.revision_changes?.length">
      <li
        v-for="r in effects.revision_changes"
        :key="r.item_key"
      >
        Revision {{ r.item_key }}: {{ r.change.toLowerCase() + (r.due_date ? `, due ${r.due_date}` : '') }}
      </li>
    </ul>
    <p v-if="effects.readiness_change && effects.readiness_change.before !== effects.readiness_change.after">
      Readiness: {{ effects.readiness_change.before ?? '—' }} → {{ effects.readiness_change.after }}
    </p>
    <p v-if="effects.readiness_change?.blockers_removed?.length">
      Cleared: {{ effects.readiness_change.blockers_removed.join('; ') }}
    </p>
  </section>
</template>

<style scoped>
.effects { border: 1px solid #b9d3b9; background: #f3faf3; border-radius: 8px; padding: 0.5rem 0.9rem; margin: 0.75rem 0; }
.effects h3 { margin: 0 0 0.3rem; font-size: 1rem; }
ul { margin: 0.2rem 0; padding-left: 1.2rem; font-size: 0.85rem; }
</style>

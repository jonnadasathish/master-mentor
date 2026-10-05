<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { Effects } from '../../api/types'
import { GAP_STATUS_LABEL, READINESS_LABEL } from '../../presentation/language'
import { shortDate } from '../../presentation/format'
import { useSkillsStore } from '../../stores/data'
import Icon from '../common/Icon.vue'
import SkillDeltas from './SkillDeltas.vue'

/** The feedback loop: what the last result changed. Every value is from the server's mentor run. */
defineProps<{ effects: Effects }>()
const skills = useSkillsStore()

/** "PATTERN:two_pointers.core" -> "Two pointers"; "PROBLEM:17" -> "a problem you solved". */
function reviewLabel(itemKey: string): string {
  const [kind, ref] = itemKey.split(':')
  if (kind === 'PROBLEM') return 'a problem you worked on'
  if (kind === 'STORY') return 'one of your stories'
  if (kind === 'MOCKW') return 'a weakness from your mock'
  return ref ? skills.nameOf(ref.split(':').at(-1) ?? ref) : 'a recent topic'
}
const gapStatus = (s: string) => GAP_STATUS_LABEL[s] ?? s
</script>

<template>
  <section
    class="effects"
    aria-label="What changed"
    data-testid="effects-panel"
  >
    <h3>
      <Icon
        name="trending"
        :size="15"
      /> What changed
    </h3>
    <SkillDeltas :deltas="effects.skill_deltas" />
    <ul
      v-if="effects.gap_deltas?.length"
      class="lines"
    >
      <li
        v-for="g in effects.gap_deltas"
        :key="g.skill_key"
      >
        <RouterLink :to="{ name: 'skill', params: { key: g.skill_key } }">
          {{ skills.nameOf(g.skill_key) }}
        </RouterLink>
        <span>gap: {{ g.before ? gapStatus(g.before.status) : 'not measured' }} → <strong>{{ gapStatus(g.after.status) }}</strong></span>
      </li>
    </ul>
    <ul
      v-if="effects.revision_changes?.length"
      class="lines"
    >
      <li
        v-for="r in effects.revision_changes"
        :key="r.item_key"
      >
        <span>Review of {{ reviewLabel(r.item_key) }}</span>
        <span>{{ r.change === 'CREATED' ? 'scheduled' : 'rescheduled' }}<template v-if="r.due_date"> for {{ shortDate(r.due_date) }}</template></span>
      </li>
    </ul>
    <p
      v-if="effects.readiness_change && effects.readiness_change.before !== effects.readiness_change.after"
      class="readiness"
    >
      Readiness: {{ effects.readiness_change.before ? (READINESS_LABEL[effects.readiness_change.before] ?? effects.readiness_change.before) : '—' }}
      → <strong>{{ READINESS_LABEL[effects.readiness_change.after] ?? effects.readiness_change.after }}</strong>
    </p>
  </section>
</template>

<style scoped>
.effects { display: grid; gap: var(--s-2); padding: var(--s-4); background: var(--healthy-bg); border: 1px solid var(--healthy-bd); border-radius: var(--r-md); }
h3 { display: flex; align-items: center; gap: var(--s-2); font-size: var(--fs-sm); color: var(--healthy-fg); }
.lines { display: grid; gap: var(--s-1); font-size: var(--fs-sm); }
.lines li { display: flex; justify-content: space-between; gap: var(--s-4); flex-wrap: wrap; }
.readiness { font-size: var(--fs-sm); }
</style>

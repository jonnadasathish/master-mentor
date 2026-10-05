<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { SkillDelta, SkillSnapshot } from '../../api/types'
import { CONFIDENCE_LABEL } from '../../presentation/language'
import { useSkillsStore } from '../../stores/data'

/** Before -> after for each skill the last observation touched. Values come from the backend run. */
defineProps<{ deltas: SkillDelta[] }>()
const skills = useSkillsStore()

function side(s: SkillSnapshot | null): string {
  if (!s || s.score === null) return 'not measured yet'
  return `${s.score}`
}
function confidence(s: SkillSnapshot): string {
  return s.score === null ? '' : ` · ${(CONFIDENCE_LABEL[s.confidence] ?? s.confidence).toLowerCase()} confidence`
}
</script>

<template>
  <div
    class="deltas"
    data-testid="skill-deltas"
  >
    <p
      v-if="!deltas.length"
      class="muted"
    >
      No skill score changed.
    </p>
    <ul v-else>
      <li
        v-for="d in deltas"
        :key="d.skill_key"
      >
        <RouterLink :to="{ name: 'skill', params: { key: d.skill_key } }">
          {{ skills.nameOf(d.skill_key) }}
        </RouterLink>
        <span class="values tabular">{{ side(d.before) }} → <strong>{{ side(d.after) }}</strong><span class="muted">{{ confidence(d.after) }}</span></span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.deltas { font-size: var(--fs-sm); }
.deltas ul { display: grid; gap: var(--s-1); }
.deltas li { display: flex; justify-content: space-between; gap: var(--s-4); flex-wrap: wrap; }
</style>

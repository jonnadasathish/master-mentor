<script setup lang="ts">
import type { SkillDelta, SkillSnapshot } from '../api/types'

/** Display-only list of what the last observation changed (values come from the backend run). */
defineProps<{ deltas: SkillDelta[] }>()

function side(s: SkillSnapshot | null): string {
  if (!s || s.score === null) return 'unassessed'
  return `${s.score} (L${s.level}, ${s.confidence.toLowerCase()})`
}
</script>

<template>
  <div
    class="deltas"
    data-testid="skill-deltas"
  >
    <p v-if="!deltas.length">
      No skill state changed.
    </p>
    <ul v-else>
      <li
        v-for="d in deltas"
        :key="d.skill_key"
      >
        <RouterLink :to="{ name: 'skill', params: { key: d.skill_key } }">
          {{ d.skill_key }}
        </RouterLink>: {{ side(d.before) }} → {{ side(d.after) }}
      </li>
    </ul>
  </div>
</template>

<style scoped>
.deltas { font-size: 0.85rem; color: #333; }
.deltas ul { margin: 0.25rem 0; padding-left: 1.2rem; }
</style>

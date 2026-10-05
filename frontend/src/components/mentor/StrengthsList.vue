<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useSkillsStore } from '../../stores/data'
import StatusPill from '../common/StatusPill.vue'

/** Skills that are on target, best first (a sort of the server's own scores). */
const skills = useSkillsStore()
const strengths = computed(() =>
  skills.list
    .filter((s) => s.state.assessed && s.gap?.status === 'NONE' && s.state.effective_score !== null)
    .sort((a, b) => (b.state.effective_score ?? 0) - (a.state.effective_score ?? 0) || a.key.localeCompare(b.key))
    .slice(0, 3),
)
defineExpose({ strengths })
</script>

<template>
  <ul
    v-if="strengths.length"
    class="strengths"
    data-testid="strengths"
  >
    <li
      v-for="s in strengths"
      :key="s.key"
    >
      <RouterLink
        :to="{ name: 'skill', params: { key: s.key } }"
        class="row"
      >
        <span class="name">{{ s.name }}</span>
        <span class="tabular score">{{ s.state.effective_score }} / {{ s.target_score ?? '—' }}</span>
        <StatusPill state="healthy" />
      </RouterLink>
    </li>
  </ul>
</template>

<style scoped>
.strengths { display: grid; gap: var(--s-2); }
.row { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-md); color: inherit; }
.row:hover { text-decoration: none; border-color: var(--border-strong); }
.name { flex: 1; font-weight: 600; }
.score { color: var(--text-3); font-size: var(--fs-sm); }
</style>

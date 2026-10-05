<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '../../api'
import type { ProblemSummary } from '../../api/types'
import { useErrorStore } from '../../stores/errors'
import { outcomeLabel } from '../../practice/vocabulary'

interface SkillOption { key: string; name: string; component: string }

const route = useRoute()
const battery = typeof route.query.battery === 'string' ? route.query.battery : ''
const filters = reactive({
  q: '',
  difficulty: typeof route.query.difficulty === 'string' ? route.query.difficulty : '',
  skill: '',
  source: '',
})
const problems = ref<ProblemSummary[]>([])
const skills = ref<SkillOption[]>([])
const errorStore = useErrorStore()

async function load(): Promise<void> {
  try {
    problems.value = (await api.get<ProblemSummary[]>('/problems', { ...filters })).data
  } catch (caught) {
    errorStore.report(caught, 'problems')
  }
}

onMounted(async () => {
  try {
    const all = (await api.get<SkillOption[]>('/catalog/skills')).data
    skills.value = all.filter((s) => s.component === 'dsa' || s.component === 'coding')
  } catch (caught) {
    errorStore.report(caught, 'problems')
  }
  await load()
})
</script>

<template>
  <section>
    <h1>Problems</h1>
    <form
      class="filters"
      role="search"
      @submit.prevent="load"
    >
      <label>Search
        <input
          v-model="filters.q"
          type="search"
          placeholder="title or slug"
          data-testid="search"
          @input="load"
        >
      </label>
      <label>Difficulty
        <select
          v-model="filters.difficulty"
          data-testid="difficulty"
          @change="load"
        >
          <option value="">Any</option>
          <option value="EASY">Easy</option>
          <option value="MEDIUM">Medium</option>
          <option value="HARD">Hard</option>
        </select>
      </label>
      <label>Skill / pattern
        <select
          v-model="filters.skill"
          data-testid="skill"
          @change="load"
        >
          <option value="">Any</option>
          <option
            v-for="s in skills"
            :key="s.key"
            :value="s.key"
          >{{ s.key }}</option>
        </select>
      </label>
      <label>Source
        <select
          v-model="filters.source"
          data-testid="source"
          @change="load"
        >
          <option value="">Any</option>
          <option value="CATALOG">Catalog</option>
          <option value="PERSONAL">Personal</option>
        </select>
      </label>
    </form>
    <p data-testid="problem-count">
      {{ problems.length }} problems
    </p>
    <table>
      <thead>
        <tr>
          <th>Problem</th><th>Difficulty</th><th>Primary skill</th><th>Source</th><th>Attempts</th><th>Last</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="p in problems"
          :key="p.id"
          data-testid="problem-row"
        >
          <td>
            <RouterLink :to="{ name: 'problem', params: { problemKey: p.key }, query: battery ? { battery } : {} }">
              {{ p.title }}
            </RouterLink>
          </td>
          <td>{{ p.difficulty }}</td>
          <td>{{ p.skills.find((s) => s.primary)?.skill }}</td>
          <td>
            <span :class="['badge', p.source.toLowerCase()]">{{ p.source === 'CATALOG' ? 'Catalog' : 'Personal' }}</span>
          </td>
          <td>{{ p.attempt_count }}</td>
          <td>{{ p.last_attempt ? outcomeLabel(p.last_attempt.outcome) : '—' }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.filters { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 0.75rem; }
.filters label { display: flex; flex-direction: column; font-size: 0.85rem; }
.badge { font-size: 0.75rem; padding: 0.1rem 0.4rem; border-radius: 4px; border: 1px solid #999; }
.badge.personal { background: #fff4d6; }
</style>

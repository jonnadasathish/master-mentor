<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '../../api'
import type { ProblemSummary } from '../../api/types'
import EmptyState from '../../components/common/EmptyState.vue'
import ErrorState from '../../components/common/ErrorState.vue'
import Icon from '../../components/common/Icon.vue'
import PageHeader from '../../components/common/PageHeader.vue'
import Skeleton from '../../components/common/Skeleton.vue'
import StatusPill from '../../components/common/StatusPill.vue'
import { outcomeLabel } from '../../practice/vocabulary'
import { plural } from '../../presentation/format'
import { useCatalogSkillsStore, useSkillsStore } from '../../stores/data'

/** Find a problem to practise: search, difficulty, pattern and status. Filtering only narrows the server's list. */
const route = useRoute()
const battery = typeof route.query.battery === 'string' ? route.query.battery : ''
const skills = useSkillsStore()
const catalog = useCatalogSkillsStore()
const filters = reactive({
  q: '',
  difficulty: typeof route.query.difficulty === 'string' ? route.query.difficulty : '',
  skill: typeof route.query.skill === 'string' ? route.query.skill : '',
  status: '',
})
const problems = ref<ProblemSummary[] | null>(null)
const error = ref<unknown>(null)

const patternOptions = computed(() =>
  (catalog.data ?? []).filter((c) => c.component === 'dsa' || c.component === 'coding').sort((a, b) => a.name.localeCompare(b.name)),
)
const shown = computed(() =>
  (problems.value ?? []).filter((p) => {
    if (filters.status === 'new') return p.attempt_count === 0
    if (filters.status === 'again') return p.last_attempt !== null && p.last_attempt.outcome !== 'PASS'
    if (filters.status === 'solved') return p.last_attempt?.outcome === 'PASS'
    return true
  }),
)

async function load(): Promise<void> {
  error.value = null
  try {
    problems.value = (await api.get<ProblemSummary[]>('/problems', { q: filters.q, difficulty: filters.difficulty, skill: filters.skill })).data
  } catch (caught) {
    error.value = caught
  }
}

function status(p: ProblemSummary): { state: 'healthy' | 'medium' | 'calibration'; label: string } {
  if (!p.last_attempt) return { state: 'calibration', label: 'New' }
  return p.last_attempt.outcome === 'PASS'
    ? { state: 'healthy', label: outcomeLabel(p.last_attempt.outcome) }
    : { state: 'medium', label: outcomeLabel(p.last_attempt.outcome) }
}
const DIFFICULTY: Record<string, string> = { EASY: 'Easy', MEDIUM: 'Medium', HARD: 'Hard' }

onMounted(async () => {
  await Promise.all([load(), skills.ensure(), catalog.ensure()])
})
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="DSA"
      title="Problems"
    >
      <RouterLink
        :to="{ name: 'dsa' }"
        class="btn btn-ghost"
      >
        <Icon
          name="arrow-left"
          :size="16"
        /> Back to DSA
      </RouterLink>
    </PageHeader>

    <form
      class="filters"
      role="search"
      @submit.prevent="load"
    >
      <label class="search">
        <span class="sr-only">Search problems</span>
        <Icon
          name="search"
          :size="16"
        />
        <input
          v-model="filters.q"
          type="search"
          placeholder="Search by title"
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
      <label>Pattern
        <select
          v-model="filters.skill"
          data-testid="skill"
          @change="load"
        >
          <option value="">Any</option>
          <option
            v-for="s in patternOptions"
            :key="s.key"
            :value="s.key"
          >{{ s.name }}</option>
        </select>
      </label>
      <label>Status
        <select
          v-model="filters.status"
          data-testid="status"
        >
          <option value="">Any</option>
          <option value="new">Not attempted</option>
          <option value="again">Needs another go</option>
          <option value="solved">Solved</option>
        </select>
      </label>
    </form>

    <div
      v-if="problems === null && !error"
      class="stack"
      aria-busy="true"
    >
      <Skeleton
        v-for="n in 6"
        :key="n"
        height="3.4rem"
        radius="var(--r-md)"
      />
    </div>
    <ErrorState
      v-else-if="error"
      :error="error"
      @retry="load"
    />
    <EmptyState
      v-else-if="!shown.length"
      icon="search"
      title="No problems match."
      body="Try a different search or clear a filter."
    />
    <template v-else>
      <p
        class="muted count"
        data-testid="problem-count"
      >
        {{ plural(shown.length, 'problem') }}
      </p>
      <ul class="list card-quiet divided">
        <li
          v-for="p in shown"
          :key="p.id"
          data-testid="problem-row"
        >
          <RouterLink
            :to="{ name: 'problem', params: { problemKey: p.key }, query: battery ? { battery } : {} }"
            class="row-link"
          >
            <span class="title">{{ p.title }}</span>
            <span class="meta muted">
              {{ DIFFICULTY[p.difficulty] }} · {{ skills.nameOf(p.skills.find((s) => s.primary)?.skill ?? '') }}
              <template v-if="p.source === 'PERSONAL'">· Yours</template>
            </span>
            <span class="attempts muted small">{{ p.attempt_count ? plural(p.attempt_count, 'attempt') : '' }}</span>
            <StatusPill
              :state="status(p).state"
              :label="status(p).label"
            />
          </RouterLink>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.filters { display: flex; flex-wrap: wrap; gap: var(--s-3) var(--s-4); align-items: end; }
.filters label { display: grid; gap: var(--s-1); }
.search { position: relative; flex: 1 1 14rem; display: block; }
.search :deep(svg) { position: absolute; left: 0.8rem; top: 0.75rem; color: var(--text-3); }
.search input { width: 100%; padding-left: 2.3rem; }
.count { font-size: var(--fs-sm); }
.row-link { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1.2fr) 6rem auto; align-items: center; gap: var(--s-4); padding: var(--s-3) var(--s-4); color: inherit; }
.row-link:hover { background: var(--surface-2); text-decoration: none; }
.title { font-weight: 600; }
.meta, .attempts { font-size: var(--fs-sm); }
.attempts { text-align: right; }
@media (max-width: 767px) {
  .row-link { grid-template-columns: minmax(0, 1fr) auto; gap: var(--s-1) var(--s-3); }
  .meta { grid-column: 1; grid-row: 2; }
  .attempts { display: none; }
}
</style>

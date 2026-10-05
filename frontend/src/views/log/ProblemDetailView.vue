<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '../../api'
import type { ProblemAttempt, ProblemSummary } from '../../api/types'
import AttemptForm from '../../components/AttemptForm.vue'
import { useErrorStore } from '../../stores/errors'
import { formatDuration, hintsLabel, mistakeLabel, outcomeLabel } from '../../practice/vocabulary'

const route = useRoute()
const problem = ref<ProblemSummary | null>(null)
const history = ref<ProblemAttempt[]>([])
const errorStore = useErrorStore()
const batteryItem = computed(() => (typeof route.query.battery === 'string' ? route.query.battery : undefined))
const revisionItem = computed(() => (typeof route.query.revision === 'string' ? route.query.revision : undefined))

async function load(): Promise<void> {
  const key = encodeURIComponent(String(route.params.problemKey))
  try {
    problem.value = (await api.get<ProblemSummary>(`/problems/${key}`)).data
    history.value = (await api.get<ProblemAttempt[]>(`/problems/${key}/attempts`)).data
  } catch (caught) {
    errorStore.report(caught, 'problem')
  }
}

onMounted(load)
watch(() => route.params.problemKey, load)
</script>

<template>
  <section v-if="problem">
    <p>
      <RouterLink :to="{ name: 'problems' }">
        ← Problems
      </RouterLink>
    </p>
    <h1 data-testid="problem-title">
      {{ problem.title }}
    </h1>
    <p>
      {{ problem.difficulty }} · {{ problem.source === 'CATALOG' ? 'Catalog' : 'Personal' }} ·
      {{ problem.skills.map((s) => s.skill + (s.primary ? ' (primary)' : '')).join(', ') }}
      <a
        v-if="problem.url"
        :href="problem.url"
        target="_blank"
        rel="noopener"
      >open ↗</a>
    </p>
    <p data-testid="last-attempt">
      Last attempt:
      <template v-if="problem.last_attempt">
        {{ outcomeLabel(problem.last_attempt.outcome) }} on {{ problem.last_attempt.attempted_at.slice(0, 10) }}
      </template>
      <template v-else>
        none yet
      </template>
    </p>

    <p
      v-if="batteryItem"
      class="battery"
      data-testid="battery-banner"
    >
      Baseline battery item {{ batteryItem }}: this attempt counts toward calibration.
    </p>
    <p
      v-if="revisionItem"
      class="battery"
      data-testid="revision-banner"
    >
      Revision review {{ revisionItem }}: closed-book, no hints; the result moves its schedule.
    </p>
    <AttemptForm
      :problem-id="problem.id"
      :battery-item-key="batteryItem"
      :revision-item-key="revisionItem"
      :client="api"
      @recorded="load"
    />

    <h2>History ({{ history.length }})</h2>
    <ol data-testid="history">
      <li
        v-for="a in history"
        :key="a.id"
      >
        <RouterLink :to="{ name: 'attempt', params: { id: a.id } }">
          {{ a.attempted_on }}
        </RouterLink>
        · {{ outcomeLabel(a.outcome) }} · {{ formatDuration(a.time_seconds) }} · {{ hintsLabel(a.hints_used) }}
        <template v-if="a.mistakes.length">
          · {{ a.mistakes.map(mistakeLabel).join(', ') }}
        </template>
      </li>
    </ol>
  </section>
</template>

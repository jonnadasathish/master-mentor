<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '../../api'
import type { ProblemAttempt } from '../../api/types'
import AttemptForm from '../../components/AttemptForm.vue'
import { useErrorStore } from '../../stores/errors'
import { formatDuration, mistakeLabel, outcomeLabel } from '../../practice/vocabulary'

/** Shows exactly what was entered. A correction appends a new version; this record never changes. */
const route = useRoute()
const attempt = ref<ProblemAttempt | null>(null)
const errorStore = useErrorStore()
const correcting = ref(false)

onMounted(async () => {
  try {
    attempt.value = (await api.get<ProblemAttempt>(`/problem-attempts/${Number(route.params.id)}`)).data
  } catch (caught) {
    errorStore.report(caught, 'attempt')
  }
})

function yesNo(value: boolean | null): string {
  return value === null ? '—' : value ? 'yes' : 'no'
}
</script>

<template>
  <section v-if="attempt">
    <h1>Attempt #{{ attempt.id }}</h1>
    <p>
      <RouterLink :to="{ name: 'problem', params: { problemKey: attempt.problem.key } }">
        {{ attempt.problem.title }}
      </RouterLink>
    </p>
    <p
      v-if="!attempt.is_current"
      role="note"
    >
      Corrected later by
      <RouterLink :to="{ name: 'attempt', params: { id: attempt.superseded_by_id } }">
        #{{ attempt.superseded_by_id }}
      </RouterLink>
      (this original record is kept unchanged).
    </p>
    <dl data-testid="attempt-detail">
      <dt>Attempted</dt><dd>{{ attempt.attempted_at }} (local date {{ attempt.attempted_on }})</dd>
      <dt>Result</dt><dd>{{ outcomeLabel(attempt.outcome) }}</dd>
      <dt>Time</dt><dd>{{ formatDuration(attempt.time_seconds) }}</dd>
      <dt>Hints</dt><dd>{{ attempt.hints_used }}</dd>
      <dt>Mistakes</dt><dd>{{ attempt.mistakes.map(mistakeLabel).join(', ') || '—' }}</dd>
      <dt>Confidence before / after</dt><dd>{{ attempt.self_rating_before ?? '—' }} / {{ attempt.self_rating_after ?? '—' }}</dd>
      <dt>Explanation</dt><dd>{{ attempt.explanation_score ?? '—' }}</dd>
      <dt>Complexity correct</dt><dd>{{ yesNo(attempt.complexity_correct) }}</dd>
      <dt>Pattern named before hints</dt><dd>{{ yesNo(attempt.pattern_identified) }}</dd>
      <dt>Solution viewed</dt><dd>{{ yesNo(attempt.solution_viewed) }}</dd>
      <dt>Notes</dt><dd>{{ attempt.notes ?? '—' }}</dd>
    </dl>
    <p v-if="attempt.is_current">
      <button
        type="button"
        class="secondary"
        data-testid="correct-attempt"
        @click="correcting = !correcting"
      >
        {{ correcting ? 'Cancel correction' : 'Correct this attempt' }}
      </button>
    </p>
    <AttemptForm
      v-if="correcting"
      :problem-id="attempt.problem.id"
      :client="api"
      :correction-of="attempt"
    />
  </section>
</template>

<style scoped>
dl { display: grid; grid-template-columns: max-content 1fr; gap: 0.2rem 1rem; }
</style>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '../../api'
import type { ProblemAttempt } from '../../api/types'
import AttemptForm from '../../components/practice/AttemptForm.vue'
import ErrorState from '../../components/common/ErrorState.vue'
import Icon from '../../components/common/Icon.vue'
import PageHeader from '../../components/common/PageHeader.vue'
import Skeleton from '../../components/common/Skeleton.vue'
import StatusPill from '../../components/common/StatusPill.vue'
import { formatDuration, mistakeLabel, outcomeLabel } from '../../practice/vocabulary'
import { longDate } from '../../presentation/format'
import { refreshDerivedData } from '../../stores/data'

/** Shows exactly what was entered. A correction appends a new version; this record never changes. */
const route = useRoute()
const attempt = ref<ProblemAttempt | null>(null)
const error = ref<unknown>(null)
const correcting = ref(false)

async function load(): Promise<void> {
  error.value = null
  try {
    attempt.value = (await api.get<ProblemAttempt>(`/problem-attempts/${Number(route.params.id)}`)).data
  } catch (caught) {
    error.value = caught
  }
}
const yesNo = (value: boolean | null) => (value === null ? 'Not recorded' : value ? 'Yes' : 'No')

onMounted(load)
</script>

<template>
  <div class="page page-narrow">
    <Skeleton
      v-if="!attempt && !error"
      height="14rem"
      radius="var(--r-lg)"
    />
    <ErrorState
      v-else-if="!attempt"
      :error="error"
      @retry="load"
    />
    <template v-else>
      <PageHeader
        eyebrow="Attempt"
        :title="attempt.problem.title"
      >
        <RouterLink
          :to="{ name: 'problem', params: { problemKey: attempt.problem.key } }"
          class="btn btn-ghost"
        >
          <Icon
            name="arrow-left"
            :size="16"
          /> The problem
        </RouterLink>
      </PageHeader>

      <p
        v-if="!attempt.is_current"
        class="note"
        role="note"
      >
        <Icon
          name="info"
          :size="16"
        /> Corrected later in
        <RouterLink :to="{ name: 'attempt', params: { id: attempt.superseded_by_id } }">
          a newer version
        </RouterLink>. This original is kept unchanged.
      </p>

      <section class="card">
        <p class="top">
          <StatusPill
            :state="attempt.outcome === 'PASS' ? 'healthy' : attempt.outcome === 'PARTIAL' ? 'medium' : 'critical'"
            :label="outcomeLabel(attempt.outcome)"
          />
          <span class="muted">{{ longDate(attempt.attempted_on) }}</span>
        </p>
        <dl
          class="facts"
          data-testid="attempt-detail"
        >
          <div><dt>Time</dt><dd>{{ formatDuration(attempt.time_seconds) }}</dd></div>
          <div><dt>Hints used</dt><dd>{{ attempt.hints_used }}</dd></div>
          <div><dt>Mistakes</dt><dd>{{ attempt.mistakes.map(mistakeLabel).join(', ') || 'None recorded' }}</dd></div>
          <div><dt>Confidence before / after</dt><dd>{{ attempt.self_rating_before ?? '—' }} / {{ attempt.self_rating_after ?? '—' }}</dd></div>
          <div><dt>Explanation (0–10)</dt><dd>{{ attempt.explanation_score ?? '—' }}</dd></div>
          <div><dt>Complexity right</dt><dd>{{ yesNo(attempt.complexity_correct) }}</dd></div>
          <div><dt>Named the pattern first</dt><dd>{{ yesNo(attempt.pattern_identified) }}</dd></div>
          <div><dt>Viewed the solution</dt><dd>{{ yesNo(attempt.solution_viewed) }}</dd></div>
          <div class="wide">
            <dt>Notes</dt><dd>{{ attempt.notes ?? 'None' }}</dd>
          </div>
        </dl>
        <button
          v-if="attempt.is_current"
          type="button"
          class="btn"
          data-testid="correct-attempt"
          @click="correcting = !correcting"
        >
          {{ correcting ? 'Cancel correction' : 'Correct this attempt' }}
        </button>
      </section>

      <AttemptForm
        v-if="correcting"
        :problem-id="attempt.problem.id"
        :client="api"
        :correction-of="attempt"
        @recorded="() => refreshDerivedData()"
      />
    </template>
  </div>
</template>

<style scoped>
.top { display: flex; align-items: center; gap: var(--s-3); margin-bottom: var(--s-4); }
.facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--s-4) var(--s-5); margin-bottom: var(--s-5); }
.facts dt { font-size: var(--fs-xs); font-weight: 650; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-3); }
.facts dd { margin-top: 2px; }
.wide { grid-column: 1 / -1; }
.note { display: flex; align-items: center; gap: var(--s-2); padding: var(--s-3) var(--s-4); background: var(--due-bg); color: var(--due-fg); border-radius: var(--r-md); }
@media (max-width: 767px) { .facts { grid-template-columns: 1fr; } }
</style>

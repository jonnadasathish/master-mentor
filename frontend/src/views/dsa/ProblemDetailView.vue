<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '../../api'
import type { ProblemAttempt, ProblemSummary } from '../../api/types'
import AttemptForm from '../../components/practice/AttemptForm.vue'
import EmptyState from '../../components/common/EmptyState.vue'
import ErrorState from '../../components/common/ErrorState.vue'
import Icon from '../../components/common/Icon.vue'
import PageHeader from '../../components/common/PageHeader.vue'
import SectionHeading from '../../components/common/SectionHeading.vue'
import Skeleton from '../../components/common/Skeleton.vue'
import StatusPill from '../../components/common/StatusPill.vue'
import { formatDuration, hintsLabel, mistakeLabel, outcomeLabel } from '../../practice/vocabulary'
import { shortDate } from '../../presentation/format'
import { STAGE_LABEL } from '../../presentation/language'
import { PRACTICE_STATE_LABEL, PRACTICE_STATE_TONE } from '../../presentation/learning'
import { refreshDerivedData, useSkillsStore } from '../../stores/data'

const route = useRoute()
const skills = useSkillsStore()
const problem = ref<ProblemSummary | null>(null)
const hintsShown = ref(0)
const history = ref<ProblemAttempt[]>([])
const error = ref<unknown>(null)
const solving = ref(false)
const batteryItem = computed(() => (typeof route.query.battery === 'string' ? route.query.battery : undefined))
const revisionItem = computed(() => (typeof route.query.revision === 'string' ? route.query.revision : undefined))
const primary = computed(() => problem.value?.skills.find((s) => s.primary)?.skill ?? null)
const recommendation = computed(() => {
  const gap = primary.value ? skills.byKey.get(primary.value)?.gap : null
  if (!gap || !gap.focus_stage || ['NONE', 'UNASSESSED'].includes(gap.status)) return null
  if (gap.focus_stage === 'PREREQUISITE' && gap.focus_skill) return `Work on ${skills.nameOf(gap.focus_skill)} first: it is a prerequisite for this`
  return `${STAGE_LABEL[gap.focus_stage] ?? gap.focus_stage} on ${skills.nameOf(primary.value!)}`
})
const DIFFICULTY: Record<string, string> = { EASY: 'Easy', MEDIUM: 'Medium', HARD: 'Hard' }

async function load(): Promise<void> {
  const key = encodeURIComponent(String(route.params.problemKey))
  error.value = null
  try {
    problem.value = (await api.get<ProblemSummary>(`/problems/${key}`)).data
    history.value = (await api.get<ProblemAttempt[]>(`/problems/${key}/attempts`)).data
  } catch (caught) {
    error.value = caught
  }
}

async function recorded(): Promise<void> {
  await load()
  await refreshDerivedData()
}

onMounted(async () => {
  await Promise.all([load(), skills.ensure()])
  solving.value = !!batteryItem.value || !!revisionItem.value
})
watch(() => route.params.problemKey, load)
</script>

<template>
  <div class="page page-narrow">
    <Skeleton
      v-if="!problem && !error"
      height="12rem"
      radius="var(--r-lg)"
    />
    <ErrorState
      v-else-if="!problem"
      :error="error"
      @retry="load"
    />
    <template v-else>
      <PageHeader
        eyebrow="DSA problem"
        :title="problem.title"
      >
        <RouterLink
          :to="{ name: 'problems' }"
          class="btn btn-ghost"
        >
          <Icon
            name="arrow-left"
            :size="16"
          /> All problems
        </RouterLink>
      </PageHeader>

      <section class="card facts">
        <p class="pills">
          <span class="tag">{{ DIFFICULTY[problem.difficulty] }}</span>
          <span
            v-if="primary"
            class="tag"
          >{{ skills.nameOf(primary) }}</span>
          <span
            v-if="problem.source === 'PERSONAL'"
            class="tag"
          >Your problem</span>
          <StatusPill
            v-if="problem.practice_state"
            :state="PRACTICE_STATE_TONE[problem.practice_state]"
            :label="PRACTICE_STATE_LABEL[problem.practice_state]"
            quiet
          />
          <a
            v-if="problem.url"
            :href="problem.url"
            target="_blank"
            rel="noopener"
            class="ext"
          >Open the problem <Icon
            name="external"
            :size="14"
          /></a>
        </p>
        <div
          v-if="problem.guide"
          class="guide"
          data-testid="problem-guide"
        >
          <p>{{ problem.guide.summary }}</p>
          <details>
            <summary>Pattern and target complexity</summary>
            <p><strong>{{ problem.guide.pattern }}</strong> · time {{ problem.guide.time }}, space {{ problem.guide.space }}</p>
          </details>
          <div class="hints">
            <ol
              v-if="hintsShown"
              class="hint-list"
              data-testid="guide-hints"
            >
              <li
                v-for="h in problem.guide.hints.slice(0, hintsShown)"
                :key="h"
              >
                {{ h }}
              </li>
            </ol>
            <button
              v-if="hintsShown < problem.guide.hints.length"
              type="button"
              class="link-btn small"
              data-testid="guide-hint"
              @click="hintsShown += 1"
            >
              Show a hint ({{ problem.guide.hints.length - hintsShown }} left) — count it when you log the attempt
            </button>
          </div>
          <details>
            <summary>Common mistakes</summary>
            <ul class="hint-list">
              <li
                v-for="m in problem.guide.mistakes"
                :key="m"
              >
                {{ m }}
              </li>
            </ul>
          </details>
        </div>
        <p
          v-if="recommendation"
          class="rec"
        >
          <Icon
            name="zap"
            :size="16"
          /> <span><strong>Mentor suggests:</strong> {{ recommendation }}.</span>
        </p>
        <p
          class="last muted"
          data-testid="last-attempt"
        >
          <template v-if="problem.last_attempt">
            Last attempt: {{ outcomeLabel(problem.last_attempt.outcome) }} on {{ shortDate(problem.last_attempt.attempted_at.slice(0, 10)) }}.
          </template>
          <template v-else>
            You haven't attempted this one yet.
          </template>
        </p>
        <p
          v-if="batteryItem"
          class="note"
          data-testid="battery-banner"
        >
          <Icon
            name="crosshair"
            :size="14"
          /> This attempt counts toward your baseline.
        </p>
        <p
          v-if="revisionItem"
          class="note"
          data-testid="revision-banner"
        >
          <Icon
            name="revise"
            :size="14"
          /> Review: closed-book, no hints. The result sets when you see this again.
        </p>
        <button
          v-if="!solving"
          type="button"
          class="btn btn-primary btn-lg"
          data-testid="solve"
          @click="solving = true"
        >
          <Icon
            name="play"
            :size="14"
          /> {{ problem.attempt_count ? 'Try it again' : 'Start' }}
        </button>
      </section>

      <AttemptForm
        v-if="solving"
        :problem-id="problem.id"
        :battery-item-key="batteryItem"
        :revision-item-key="revisionItem"
        :client="api"
        @recorded="recorded"
      />

      <section>
        <SectionHeading title="Your attempts" />
        <EmptyState
          v-if="!history.length"
          icon="code"
          title="No attempts yet."
          body="Your history for this problem will appear here."
        />
        <ol
          v-else
          class="timeline card-quiet divided"
          data-testid="history"
        >
          <li
            v-for="a in history"
            :key="a.id"
          >
            <RouterLink
              :to="{ name: 'attempt', params: { id: a.id } }"
              class="when"
            >
              {{ shortDate(a.attempted_on) }}
            </RouterLink>
            <StatusPill
              :state="a.outcome === 'PASS' ? 'healthy' : a.outcome === 'PARTIAL' ? 'medium' : 'critical'"
              :label="outcomeLabel(a.outcome)"
            />
            <span class="muted small">{{ formatDuration(a.time_seconds) }} · {{ hintsLabel(a.hints_used) }}<template v-if="a.mistakes.length"> · {{ a.mistakes.map(mistakeLabel).join(', ') }}</template></span>
          </li>
        </ol>
      </section>
    </template>
  </div>
</template>

<style scoped>
.facts { display: grid; gap: var(--s-4); }
.pills { display: flex; flex-wrap: wrap; align-items: center; gap: var(--s-2); }
.tag { padding: 0.2rem 0.7rem; border-radius: 999px; background: var(--surface-3); font-size: var(--fs-sm); font-weight: 560; color: var(--text-2); }
.ext { display: inline-flex; align-items: center; gap: var(--s-1); font-size: var(--fs-sm); margin-left: auto; }
.guide { display: grid; gap: var(--s-2); padding: var(--s-3) var(--s-4); border: 1px solid var(--border); border-radius: var(--r-md); }
.guide summary { cursor: pointer; font-weight: 600; color: var(--accent-text); font-size: var(--fs-sm); }
.hints { display: grid; gap: var(--s-1); }
.hint-list { list-style: decimal; padding-left: var(--s-5); display: grid; gap: var(--s-1); font-size: var(--fs-sm); }
.rec { display: flex; gap: var(--s-2); align-items: flex-start; padding: var(--s-3) var(--s-4); background: var(--accent-soft); border-radius: var(--r-md); color: var(--accent-text); }
.rec :deep(svg) { margin-top: 0.15rem; }
.note { display: flex; align-items: center; gap: var(--s-2); font-size: var(--fs-sm); color: var(--calibration-fg); background: var(--calibration-bg); padding: var(--s-2) var(--s-3); border-radius: var(--r-md); }
.btn-lg { width: fit-content; }
.timeline li { display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap; padding: var(--s-3) var(--s-4); }
.when { font-weight: 600; min-width: 4rem; }
.small { font-size: var(--fs-sm); }
</style>

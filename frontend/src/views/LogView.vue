<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '../api'
import type { AssessmentRecord, ProblemAttempt } from '../api/types'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import Icon from '../components/common/Icon.vue'
import PageHeader from '../components/common/PageHeader.vue'
import SectionHeading from '../components/common/SectionHeading.vue'
import StatusPill from '../components/common/StatusPill.vue'
import AssessmentForm from '../components/practice/AssessmentForm.vue'
import { formatDuration, mistakeLabel, outcomeLabel } from '../practice/vocabulary'
import { shortDate } from '../presentation/format'
import { COMPONENT_LABEL, OBSERVATION_LABEL } from '../presentation/language'
import { refreshDerivedData, useSkillsStore } from '../stores/data'

/** One place to record any practice, and to see and correct what you recorded. */
const KINDS = ['RECALL_QUIZ', 'CONCEPT_EXPLAIN', 'CODE_EXERCISE', 'PATTERN_DRILL', 'SD_DESIGN', 'ESTIMATION_DRILL', 'LLD_DESIGN',
  'MACHINE_CODING', 'STORY_REHEARSAL', 'PROJECT_WALKTHROUGH', 'APPLIED_TASK', 'STUDY_SESSION'] as const
type Kind = (typeof KINDS)[number]
const MODES = [
  ['attempt', 'A coding problem'], ['assessment', 'Something else'], ['sweep', 'Self-rating'], ['mock', 'A mock interview'],
] as const

const route = useRoute()
const skills = useSkillsStore()
const wantedKind = typeof route.query.kind === 'string' && KINDS.includes(route.query.kind as Kind) ? (route.query.kind as Kind) : null
const mode = ref<'attempt' | 'assessment' | 'sweep' | 'mock'>(typeof route.query.skill === 'string' ? 'assessment' : 'attempt')
const attempts = ref<ProblemAttempt[]>([])
const assessments = ref<AssessmentRecord[]>([])
const kind = ref<Kind>(wantedKind ?? 'CONCEPT_EXPLAIN')
const skillKey = ref(typeof route.query.skill === 'string' ? route.query.skill : '')
const sourceKey = ref('')
const formKey = ref(0)
const correcting = ref<AssessmentRecord | null>(null)
const loaded = ref(false)
const showAllAttempts = ref(false)
const showAllAssessments = ref(false)
const PREVIEW = 6
const error = ref<unknown>(null)

const chosen = computed(() => skills.list.filter((s) => s.key === skillKey.value).map((s) => ({ key: s.key, name: s.name })))
const groups = computed(() => {
  const by = new Map<string, { key: string; name: string }[]>()
  for (const s of skills.list) by.set(s.component, [...(by.get(s.component) ?? []), { key: s.key, name: s.name }])
  return [...by.entries()].map(([component, items]) => ({ label: COMPONENT_LABEL[component] ?? component, items }))
})
const kindLabel = (k: string) => (OBSERVATION_LABEL[k] ?? k.toLowerCase().replace(/_/g, ' ')).replace(/^an? /, '').replace(/^./, (c) => c.toUpperCase())

async function load(): Promise<void> {
  error.value = null
  try {
    attempts.value = (await api.get<ProblemAttempt[]>('/problem-attempts', { limit: 20 })).data
    assessments.value = (await api.get<AssessmentRecord[]>('/assessments', { limit: 20 })).data
  } catch (caught) {
    error.value = caught
  } finally {
    loaded.value = true
  }
}

/** Refresh history only: the form stays mounted so its confirmation and what changed remain visible. */
async function recorded(): Promise<void> {
  await Promise.all([load(), refreshDerivedData()])
}

onMounted(() => Promise.all([load(), skills.ensure()]))
</script>

<template>
  <div class="page page-narrow">
    <PageHeader
      eyebrow="Log practice"
      title="What did you practise?"
      description="Record it in under a minute. Master Mentor updates your skills straight away."
    />

    <div
      class="tabs"
      role="tablist"
      aria-label="What to log"
    >
      <button
        v-for="[m, text] in MODES"
        :key="m"
        type="button"
        class="tab"
        role="tab"
        :aria-selected="mode === m"
        :data-testid="`kind-${m}`"
        @click="mode = m"
      >
        {{ text }}
      </button>
    </div>

    <section
      v-if="mode === 'attempt'"
      class="card prompt"
    >
      <p>Pick the problem, then time yourself and record the result.</p>
      <RouterLink
        :to="{ name: 'problems' }"
        class="btn btn-primary"
        data-testid="to-problems"
      >
        Find a problem <Icon
          name="arrow-right"
          :size="14"
        />
      </RouterLink>
    </section>

    <section
      v-else-if="mode === 'assessment'"
      class="card assess"
    >
      <div class="row">
        <label>What kind of practice?
          <select
            v-model="kind"
            data-testid="assessment-kind"
          >
            <option
              v-for="k in KINDS"
              :key="k"
              :value="k"
            >{{ kindLabel(k) }}</option>
          </select>
        </label>
        <label>Which skill?
          <select
            v-model="skillKey"
            data-testid="assessment-skill"
          >
            <option value="">Choose…</option>
            <optgroup
              v-for="g in groups"
              :key="g.label"
              :label="g.label"
            >
              <option
                v-for="s in g.items"
                :key="s.key"
                :value="s.key"
              >{{ s.name }}</option>
            </optgroup>
          </select>
        </label>
        <label>Exercise name <span class="muted">(optional)</span>
          <input
            v-model="sourceKey"
            placeholder="e.g. isolation-levels-quiz"
            maxlength="96"
          >
        </label>
      </div>
      <p
        v-if="kind === 'STUDY_SESSION'"
        class="muted"
      >
        Study sessions record minutes, never a score. Use "Mark studied" on a mission instead.
      </p>
      <template v-if="chosen.length && kind !== 'STUDY_SESSION'">
        <button
          type="button"
          class="link-btn"
          data-testid="log-another"
          @click="formKey += 1"
        >
          Start a new entry
        </button>
        <AssessmentForm
          :key="`${formKey}-${kind}-${skillKey}`"
          :client="api"
          :kind="kind"
          :skills="chosen"
          :source-key="sourceKey || `prompt:${skillKey}`"
          @recorded="recorded"
        />
      </template>
    </section>

    <section
      v-else-if="mode === 'sweep'"
      class="card prompt"
    >
      <p>Rate how familiar you are with each skill. It's part of your baseline.</p>
      <RouterLink
        :to="{ name: 'baseline' }"
        class="btn btn-primary"
      >
        Open your baseline
      </RouterLink>
    </section>

    <section
      v-else
      class="card prompt"
    >
      <p>Mock interviews have their own page, with rounds and per-skill scores.</p>
      <RouterLink
        :to="{ name: 'mocks' }"
        class="btn btn-primary"
      >
        Log a mock
      </RouterLink>
    </section>

    <ErrorState
      v-if="error"
      :error="error"
      @retry="load"
    />

    <section>
      <SectionHeading title="Recent problem attempts" />
      <EmptyState
        v-if="loaded && !attempts.length"
        icon="code"
        title="No attempts yet."
        body="Your coding practice will show up here."
      />
      <ul
        v-else
        class="list card-quiet divided"
        data-testid="recent-attempts"
      >
        <li
          v-for="a in showAllAttempts ? attempts : attempts.slice(0, PREVIEW)"
          :key="a.id"
        >
          <RouterLink
            :to="{ name: 'problem', params: { problemKey: a.problem.key } }"
            class="title"
          >
            {{ a.problem.title }}
          </RouterLink>
          <span class="muted small">{{ shortDate(a.attempted_on) }} · {{ formatDuration(a.time_seconds) }}<template v-if="a.mistakes.length"> · {{ a.mistakes.map(mistakeLabel).join(', ') }}</template></span>
          <StatusPill
            :state="a.outcome === 'PASS' ? 'healthy' : a.outcome === 'PARTIAL' ? 'medium' : 'critical'"
            :label="outcomeLabel(a.outcome)"
          />
          <RouterLink
            :to="{ name: 'attempt', params: { id: a.id } }"
            class="small"
          >
            Details
          </RouterLink>
        </li>
      </ul>
      <button
        v-if="attempts.length > PREVIEW"
        type="button"
        class="link-btn more"
        @click="showAllAttempts = !showAllAttempts"
      >
        {{ showAllAttempts ? 'Show fewer' : `Show all ${attempts.length}` }}
      </button>
    </section>

    <section>
      <SectionHeading title="Recent exercises and quizzes" />
      <EmptyState
        v-if="loaded && !assessments.length"
        icon="list"
        title="Nothing recorded yet."
        body="Quizzes, designs and explanations you record will show up here."
      />
      <ul
        v-else
        class="list card-quiet divided"
        data-testid="recent-assessments"
      >
        <li
          v-for="s in showAllAssessments ? assessments : assessments.slice(0, PREVIEW)"
          :key="s.id"
        >
          <span class="title">{{ kindLabel(s.kind) }}<template v-if="s.familiarity">
            · {{ s.familiarity.toLowerCase() }}
          </template></span>
          <span class="muted small">{{ shortDate(s.observed_on) }} · {{ s.skills.map((k) => skills.nameOf(k.skill) + (k.outcome_points !== null ? ` ${k.outcome_points}` : '')).slice(0, 3).join(', ') }}<template v-if="s.skills.length > 3">
            and {{ s.skills.length - 3 }} more
          </template></span>
          <button
            type="button"
            class="link-btn small"
            :data-testid="`correct-assessment-${s.id}`"
            @click="correcting = correcting?.id === s.id ? null : s"
          >
            Correct
          </button>
        </li>
      </ul>
      <button
        v-if="assessments.length > PREVIEW"
        type="button"
        class="link-btn more"
        @click="showAllAssessments = !showAllAssessments"
      >
        {{ showAllAssessments ? 'Show fewer' : `Show all ${assessments.length}` }}
      </button>
    </section>
    <AssessmentForm
      v-if="correcting && correcting.kind !== 'SELF_ASSESSMENT' && correcting.kind !== 'STUDY_SESSION'"
      :key="`correct-${correcting.id}`"
      :client="api"
      :kind="correcting.kind"
      :skills="correcting.skills.map((k) => ({ key: k.skill, name: skills.nameOf(k.skill) }))"
      :source-key="correcting.source_key"
      :correction-of="correcting"
      @recorded="recorded"
    />
    <p
      v-else-if="correcting"
      class="muted"
    >
      Re-run the self-rating or study entry instead; these carry no score to correct.
    </p>
  </div>
</template>

<style scoped>
.prompt { display: flex; align-items: center; justify-content: space-between; gap: var(--s-4); flex-wrap: wrap; }
.assess { display: grid; gap: var(--s-4); }
.row { display: flex; gap: var(--s-3) var(--s-4); flex-wrap: wrap; align-items: end; }
.row label { display: grid; gap: var(--s-1); flex: 1 1 14rem; font-weight: 560; }
.list li { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); flex-wrap: wrap; }
.title { font-weight: 600; flex: 1 1 10rem; min-width: 0; }
.small { font-size: var(--fs-sm); }
.more { margin-top: var(--s-3); font-size: var(--fs-sm); }
</style>

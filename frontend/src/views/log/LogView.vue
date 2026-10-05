<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../../api'
import type { AssessmentRecord, ProblemAttempt } from '../../api/types'
import AssessmentForm from '../../components/AssessmentForm.vue'
import { useErrorStore } from '../../stores/errors'
import { formatDuration, mistakeLabel, outcomeLabel } from '../../practice/vocabulary'

/** One place to capture any observation (UI_SPEC §4) and see / correct history. Raw values only. */
const KINDS = ['RECALL_QUIZ', 'CONCEPT_EXPLAIN', 'CODE_EXERCISE', 'PATTERN_DRILL', 'SD_DESIGN', 'ESTIMATION_DRILL', 'LLD_DESIGN',
  'MACHINE_CODING', 'STORY_REHEARSAL', 'PROJECT_WALKTHROUGH', 'APPLIED_TASK', 'STUDY_SESSION'] as const
const mode = ref<'attempt' | 'assessment' | 'sweep' | 'mock'>('attempt')
const attempts = ref<ProblemAttempt[]>([])
const assessments = ref<AssessmentRecord[]>([])
const skills = ref<{ key: string; name: string; component: string }[]>([])
const kind = ref<(typeof KINDS)[number]>('CONCEPT_EXPLAIN')
const skillKey = ref('')
const sourceKey = ref('')
const formKey = ref(0)
const correcting = ref<AssessmentRecord | null>(null)
const loaded = ref(false)
const errorStore = useErrorStore()

const chosen = computed(() => skills.value.filter((s) => s.key === skillKey.value).map((s) => ({ key: s.key, name: s.name })))

async function load(): Promise<void> {
  try {
    attempts.value = (await api.get<ProblemAttempt[]>('/problem-attempts', { limit: 50 })).data
    assessments.value = (await api.get<AssessmentRecord[]>('/assessments', { limit: 50 })).data
  } catch (caught) {
    errorStore.report(caught, 'log')
  } finally {
    loaded.value = true
  }
}

onMounted(async () => {
  await load()
  try {
    skills.value = (await api.get<{ key: string; name: string; component: string }[]>('/catalog/skills')).data
  } catch (caught) {
    errorStore.report(caught, 'log')
  }
})

/** Refresh history only: the form stays mounted to show its confirmation and what changed. */
function recorded(): void {
  void load()
}

function another(): void {
  formKey.value += 1
}
</script>

<template>
  <section>
    <h1>Log</h1>
    <div
      class="tabs"
      role="tablist"
      aria-label="What to log"
    >
      <button
        v-for="m in (['attempt', 'assessment', 'sweep', 'mock'] as const)"
        :key="m"
        type="button"
        role="tab"
        :aria-selected="mode === m"
        :data-testid="`kind-${m}`"
        @click="mode = m"
      >
        {{ { attempt: 'Problem attempt', assessment: 'Assessment', sweep: 'Self-assessment sweep', mock: 'Mock' }[m] }}
      </button>
    </div>

    <p v-if="mode === 'attempt'">
      <RouterLink
        :to="{ name: 'problems' }"
        data-testid="to-problems"
      >
        Find a problem and log an attempt →
      </RouterLink>
      (start/finish timer, result, hints, pattern, mistakes, confidence; under 30 s)
    </p>
    <div
      v-else-if="mode === 'assessment'"
      class="assess"
    >
      <div class="row">
        <label>Kind
          <select
            v-model="kind"
            data-testid="assessment-kind"
          >
            <option
              v-for="k in KINDS"
              :key="k"
              :value="k"
            >{{ k.toLowerCase().replace('_', ' ') }}</option>
          </select>
        </label>
        <label>Skill
          <select
            v-model="skillKey"
            data-testid="assessment-skill"
          >
            <option value="">Choose…</option>
            <option
              v-for="s in skills"
              :key="s.key"
              :value="s.key"
            >{{ s.key }}</option>
          </select>
        </label>
        <label>Prompt / exercise key
          <input
            v-model="sourceKey"
            placeholder="prompt:db-isolation"
            maxlength="96"
          >
        </label>
      </div>
      <p v-if="kind === 'STUDY_SESSION'">
        Study sessions record minutes only (never a score): use “Mark studied” on a plan item.
      </p>
      <button
        v-if="chosen.length && kind !== 'STUDY_SESSION'"
        type="button"
        class="link"
        data-testid="log-another"
        @click="another"
      >
        New entry
      </button>
      <AssessmentForm
        v-if="chosen.length && kind !== 'STUDY_SESSION'"
        :key="`${formKey}-${kind}-${skillKey}`"
        :client="api"
        :kind="kind"
        :skills="chosen"
        :source-key="sourceKey || `prompt:${skillKey}`"
        @recorded="recorded"
      />
    </div>
    <p v-else-if="mode === 'sweep'">
      The familiarity sweep (NONE / SOME / SOLID per required skill) lives on the
      <RouterLink :to="{ name: 'baseline' }">
        Baseline page
      </RouterLink>.
    </p>
    <p v-else>
      Mock interviews are logged on the <RouterLink :to="{ name: 'mocks' }">
        Mocks page
      </RouterLink>.
    </p>

    <h2>Recent attempts</h2>
    <p v-if="loaded && !attempts.length">
      No attempts recorded yet.
    </p>
    <table
      v-else
      data-testid="recent-attempts"
    >
      <thead>
        <tr>
          <th>When</th><th>Problem</th><th>Result</th><th>Time</th><th>Hints</th><th>Mistakes</th><th />
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="a in attempts"
          :key="a.id"
        >
          <td>
            <RouterLink :to="{ name: 'attempt', params: { id: a.id } }">
              {{ a.attempted_on }}
            </RouterLink>
          </td>
          <td>
            <RouterLink :to="{ name: 'problem', params: { problemKey: a.problem.key } }">
              {{ a.problem.title }}
            </RouterLink>
          </td>
          <td>{{ outcomeLabel(a.outcome) }}</td>
          <td>{{ formatDuration(a.time_seconds) }}</td>
          <td>{{ a.hints_used }}</td>
          <td>{{ a.mistakes.map(mistakeLabel).join(', ') || '—' }}</td>
          <td>
            <RouterLink :to="{ name: 'attempt', params: { id: a.id } }">
              Correct
            </RouterLink>
          </td>
        </tr>
      </tbody>
    </table>

    <h2>Recent assessments</h2>
    <p v-if="loaded && !assessments.length">
      No assessments recorded yet.
    </p>
    <table
      v-else
      data-testid="recent-assessments"
    >
      <thead>
        <tr>
          <th>When</th><th>Kind</th><th>Skills (points)</th><th>Links</th><th />
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="s in assessments"
          :key="s.id"
        >
          <td>{{ s.observed_on }}</td>
          <td>
            {{ s.kind.toLowerCase().replace('_', ' ') }}<template v-if="s.familiarity">
              ({{ s.familiarity.toLowerCase() }})
            </template>
          </td>
          <td>{{ s.skills.map((k) => `${k.skill} ${k.outcome_points ?? '—'}`).join(', ') }}</td>
          <td>{{ [s.battery_item_key, s.revision_item_key].filter(Boolean).join(', ') || '—' }}</td>
          <td>
            <button
              type="button"
              class="link"
              :data-testid="`correct-assessment-${s.id}`"
              @click="correcting = correcting?.id === s.id ? null : s"
            >
              Correct
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <AssessmentForm
      v-if="correcting && correcting.kind !== 'SELF_ASSESSMENT' && correcting.kind !== 'STUDY_SESSION'"
      :key="`correct-${correcting.id}`"
      :client="api"
      :kind="correcting.kind"
      :skills="correcting.skills.map((k) => ({ key: k.skill, name: k.skill }))"
      :source-key="correcting.source_key"
      :correction-of="correcting"
      @recorded="recorded"
    />
    <p v-else-if="correcting">
      Re-run the sweep / study entry instead; these carry no points to correct.
    </p>
  </section>
</template>

<style scoped>
.tabs { display: flex; gap: 0.4rem; margin: 0.5rem 0 1rem; flex-wrap: wrap; }
.tabs button { border: 1px solid #bbb; border-radius: 6px; background: #f6f6f8; padding: 0.25rem 0.8rem; }
.tabs button[aria-selected='true'] { background: #e3ecff; border-color: #3366cc; }
.row { display: flex; gap: 1rem; flex-wrap: wrap; }
.row label { display: flex; flex-direction: column; font-size: 0.85rem; }
table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
th, td { text-align: left; padding: 0.3rem 0.5rem; border-bottom: 1px solid #eee; }
.link { background: none; border: none; color: #2a55b0; text-decoration: underline; cursor: pointer; padding: 0; }
@media (max-width: 640px) { table { display: block; overflow-x: auto; } }
</style>

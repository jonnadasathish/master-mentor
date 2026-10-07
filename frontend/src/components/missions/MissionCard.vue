<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import type { HttpClient } from '../../api/client'
import { ApiError } from '../../api/client'
import type { Effects, PlanItem, PlanLearning } from '../../api/types'
import { openSession } from '../../learning/session'
import { formatMinutes } from '../../presentation/format'
import { CONTENT_TYPE_LABEL } from '../../presentation/learning'
import { tidyCriteria } from '../../presentation/text'
import { recordLabel, type MissionText } from '../../presentation/mission'
import Icon from '../common/Icon.vue'
import StatusPill from '../common/StatusPill.vue'
import AssessmentForm from '../practice/AssessmentForm.vue'
import AttemptForm from '../practice/AttemptForm.vue'
import EffectsPanel from './EffectsPanel.vue'

/**
 * One mission of today's plan. Not started -> in progress (timer) -> completed (the card transforms, it never
 * disappears). Skipped, deferred and blocked missions stay visible too. Display and actions only: the plan, the
 * wording inputs and every number come from the server.
 */
const props = defineProps<{
  item: PlanItem
  client: HttpClient
  text: MissionText
  /** Display number within today's list (1-based). */
  number?: number
  /** What changed when this mission was just completed (this session only). */
  result?: Effects | null
  /** Set when the mission cannot be started yet (e.g. a prerequisite comes first). */
  blockedReason?: string | null
  now?: () => number
  /** The learning session that fills this mission, when the library has content for it (D-083). */
  learning?: PlanLearning | null
}>()
const emit = defineEmits<{ changed: []; completed: [effects?: Effects] }>()

const SKIP_REASONS = [
  ['NO_TIME', 'No time today'], ['TOO_HARD', 'Too hard right now'], ['NOT_RELEVANT', 'Not relevant'], ['OTHER', 'Other'],
] as const

const router = useRouter()
const opening = ref(false)
const clock = () => (props.now ? props.now() : Date.now())

/** Open (or resume) the session for this mission; finishing it completes the mission. */
async function openLearning(): Promise<void> {
  if (!props.learning || !props.item.skill) return
  opening.value = true
  error.value = ''
  try {
    if (props.learning.session_id !== null) await router.push({ name: 'session', params: { id: props.learning.session_id } })
    else await openSession(router, { skill: props.item.skill, stage: props.learning.stage, plan_item_id: props.item.id })
  } catch (caught) {
    error.value = caught instanceof ApiError ? caught.message : String(caught)
  } finally {
    opening.value = false
  }
}
const localStart = ref<number | null>(null)
const tick = ref(0)
const logging = ref(false)
const moreOpen = ref(false)
const skipping = ref(false)
const showWhy = ref(false)
const error = ref('')
let timer: ReturnType<typeof setInterval> | undefined

const startedMs = computed(() => localStart.value ?? (props.item.started_at ? Date.parse(props.item.started_at) : null))
const phase = computed<'not-started' | 'in-progress' | 'completed' | 'skipped' | 'deferred' | 'blocked'>(() => {
  const s = props.item.status
  if (s === 'DONE') return 'completed'
  if (s === 'SKIPPED') return 'skipped'
  if (s === 'DEFERRED') return 'deferred'
  if (props.blockedReason) return 'blocked'
  return startedMs.value !== null ? 'in-progress' : 'not-started'
})
const kind = computed(() => String(props.item.template?.observation?.kind ?? (props.item.problems.length ? 'ATTEMPT' : '')))
const limitSeconds = computed(() => {
  const limit = props.item.template?.observation?.limit_seconds
  return typeof limit === 'number' ? limit : props.item.minutes * 60
})
const elapsed = computed(() => {
  void tick.value
  return startedMs.value === null ? 0 : Math.max(0, Math.floor((clock() - startedMs.value) / 1000))
})
const mmss = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
const suggestedMinutes = computed(() => (startedMs.value === null ? null : Math.max(1, Math.round(elapsed.value / 60))))
const rule = computed(() => (props.item.template ? tidyCriteria(props.item.template.pass_rule).toLowerCase() : ''))
const index = computed(() => String(props.number ?? props.item.position).padStart(2, '0'))
const isMock = computed(() => props.item.candidate_type === 'MOCK' || props.item.candidate_type === 'FINAL_SIMULATION')
const needsBaselinePage = computed(
  () => props.item.candidate_type === 'BASELINE' && !props.item.problems.length && !kind.value,
)
const canRecordHere = computed(
  () => (kind.value === 'ATTEMPT' && props.item.problems.length > 0)
    || (kind.value !== '' && kind.value !== 'ATTEMPT' && kind.value !== 'ITEM_DEFINED' && !!props.item.skill),
)
const skipLabel = computed(() => {
  const found = SKIP_REASONS.find(([code]) => code === props.item.skip_reason)
  return found ? found[1] : null
})

function runTimer(): void {
  if (!timer) timer = setInterval(() => (tick.value += 1), 1000)
}
if (phase.value === 'in-progress') runTimer()

async function act(path: string, body: unknown = {}): Promise<boolean> {
  error.value = ''
  try {
    await props.client.post(`/plan/items/${props.item.id}/${path}`, body)
    emit('changed')
    return true
  } catch (caught) {
    error.value = caught instanceof ApiError ? caught.message : String(caught)
    return false
  }
}

async function start(): Promise<void> {
  if (phase.value !== 'not-started') return
  if (await act('start')) {
    localStart.value = clock()
    runTimer()
  }
}

function finished(effects?: Effects): void {
  if (timer) clearInterval(timer)
  timer = undefined
  logging.value = false
  emit('completed', effects)
}

defineExpose({ start, phase })
onBeforeUnmount(() => timer && clearInterval(timer))
</script>

<template>
  <li
    class="mission"
    :class="`is-${phase}`"
    :data-testid="`plan-item-${item.position}`"
    :data-phase="phase"
  >
    <!-- Completed / skipped / deferred: a compact line that keeps its place in the day -->
    <template v-if="phase === 'completed' || phase === 'skipped' || phase === 'deferred'">
      <div class="done-row">
        <span
          class="mark"
          :class="phase"
          aria-hidden="true"
        >
          <Icon
            :name="phase === 'completed' ? 'check' : phase === 'skipped' ? 'skip' : 'calendar'"
            :size="14"
          />
        </span>
        <div class="done-text">
          <p class="done-title">
            <span :class="{ struck: phase !== 'completed' }">{{ text.title }}</span>
          </p>
          <p class="meta">
            {{ formatMinutes(item.minutes) }} ·
            <template v-if="phase === 'completed'">
              Completed<template v-if="item.no_evidence">
                · marked as studied
              </template>
            </template>
            <template v-else-if="phase === 'skipped'">
              Skipped<template v-if="skipLabel">
                · {{ skipLabel }}
              </template>
            </template>
            <template v-else>
              Moved to tomorrow
            </template>
          </p>
        </div>
        <StatusPill
          v-if="phase === 'completed'"
          state="completed"
          quiet
        />
      </div>
      <EffectsPanel
        v-if="result && phase === 'completed'"
        :effects="result"
        class="after"
      />
    </template>

    <!-- Not started / in progress / blocked: the full mission -->
    <template v-else>
      <div class="head">
        <span
          class="index tabular"
          aria-hidden="true"
        >{{ index }}</span>
        <div class="titles">
          <h3>{{ text.title }}</h3>
          <p class="meta">
            <Icon
              name="clock"
              :size="14"
            /><span>{{ formatMinutes(item.minutes) }}{{ text.skillLabel ? ` · ${text.skillLabel}` : '' }}</span>
          </p>
        </div>
        <StatusPill
          v-if="phase === 'in-progress'"
          state="due"
          label="In progress"
        />
        <StatusPill
          v-else-if="phase === 'blocked'"
          state="blocked"
        />
        <StatusPill
          v-else-if="item.candidate_type === 'BASELINE'"
          state="calibration"
        />
      </div>

      <p
        v-if="text.task"
        class="task"
      >
        {{ text.task }}
      </p>

      <div
        v-if="text.why.length"
        class="why"
      >
        <p class="label">
          Why this matters
        </p>
        <p
          v-for="line in text.why"
          :key="line"
        >
          {{ line }}
        </p>
        <button
          v-if="item.reason_codes.length || item.explanation.priority != null"
          type="button"
          class="why-toggle"
          :aria-expanded="showWhy"
          :data-testid="`why-${item.position}`"
          @click="showWhy = !showWhy"
        >
          {{ showWhy ? 'Hide the numbers' : 'See the numbers' }}
        </button>
        <dl
          v-if="showWhy"
          class="numbers"
          :data-testid="`why-panel-${item.position}`"
        >
          <div v-if="item.explanation.effective != null">
            <dt>Current score</dt><dd>{{ item.explanation.effective }}</dd>
          </div>
          <div v-if="item.explanation.target != null">
            <dt>Target</dt><dd>{{ item.explanation.target }}</dd>
          </div>
          <div v-if="item.explanation.priority != null">
            <dt>Priority</dt><dd>{{ item.explanation.priority }}</dd>
          </div>
        </dl>
      </div>

      <p
        v-if="text.outcome"
        class="outcome"
      >
        <Icon
          name="target"
          :size="14"
        /> <span><strong>Expected outcome:</strong> {{ text.outcome }}</span>
      </p>

      <ul
        v-if="item.problems.length"
        class="problems"
      >
        <li
          v-for="p in item.problems"
          :key="p.id"
        >
          <Icon
            name="code"
            :size="14"
          />
          <RouterLink :to="{ name: 'problem', params: { problemKey: p.key } }">
            {{ p.title }}
          </RouterLink>
          <span class="muted">{{ p.difficulty.toLowerCase() }}</span>
        </li>
      </ul>
      <p
        v-if="item.template"
        class="rule"
      >
        <template v-if="rule && rule !== text.outcome?.toLowerCase()">
          <strong>Done when:</strong> {{ rule }} · you'll record {{ recordLabel(kind) }}
        </template>
        <template v-else>
          You'll record {{ recordLabel(kind) }}.
        </template>
      </p>

      <p
        v-if="blockedReason"
        class="blocked"
      >
        <Icon
          name="lock"
          :size="14"
        /> {{ blockedReason }}
      </p>

      <p
        v-if="phase === 'in-progress'"
        class="timer tabular"
        :data-testid="`timer-${item.position}`"
        aria-live="off"
      >
        ⏱ {{ mmss(elapsed) }} / {{ mmss(limitSeconds) }}
      </p>

      <div
        v-if="learning && (phase === 'not-started' || phase === 'in-progress')"
        class="session-preview"
        :data-testid="`session-preview-${item.position}`"
      >
        <p class="eyebrow">
          This mission's session · {{ formatMinutes(learning.minutes) }}
        </p>
        <ol>
          <li
            v-for="s in learning.steps"
            :key="s.position"
          >
            {{ s.title }}<span
              v-if="s.optional"
              class="muted"
            > (optional)</span>
            <span class="muted">· {{ s.kind === 'REFLECTION' ? 'reflection' : s.kind === 'PROBLEM' ? 'problem' : CONTENT_TYPE_LABEL[s.content_type ?? 'lesson'].toLowerCase() }}, {{ formatMinutes(s.minutes) }}</span>
          </li>
        </ol>
      </div>

      <div
        v-if="phase !== 'blocked'"
        class="actions"
      >
        <button
          v-if="learning && (phase === 'not-started' || phase === 'in-progress')"
          type="button"
          class="btn btn-primary btn-lg"
          :disabled="opening"
          :data-testid="`open-session-${item.position}`"
          @click="openLearning"
        >
          <Icon
            name="book"
            :size="14"
          /> {{ learning.session_id !== null ? 'Continue the session' : 'Start the session' }}
        </button>
        <button
          v-if="phase === 'not-started'"
          type="button"
          class="btn btn-lg"
          :class="learning ? 'btn-ghost' : 'btn-primary'"
          :data-testid="`start-${item.position}`"
          @click="start"
        >
          <Icon
            name="play"
            :size="14"
          /> {{ learning ? 'Do it my way' : 'Start' }}
        </button>
        <template v-if="phase === 'in-progress'">
          <RouterLink
            v-if="isMock"
            :to="{ name: 'mocks', query: { plan_item: String(item.id) } }"
            class="btn btn-primary btn-lg"
          >
            Log this mock
          </RouterLink>
          <RouterLink
            v-else-if="needsBaselinePage"
            :to="{ name: 'baseline', query: { item: item.battery_item_key ?? '' } }"
            class="btn btn-primary btn-lg"
          >
            Open the assessment
          </RouterLink>
          <button
            v-else
            type="button"
            class="btn btn-primary btn-lg"
            :data-testid="`log-${item.position}`"
            @click="logging = !logging"
          >
            {{ logging ? 'Close' : 'Finish & log result' }}
          </button>
        </template>
        <button
          v-else-if="phase === 'not-started' && canRecordHere"
          type="button"
          class="btn btn-ghost"
          :data-testid="`log-${item.position}`"
          @click="logging = !logging"
        >
          {{ logging ? 'Close' : "I've already done this" }}
        </button>
        <button
          type="button"
          class="btn btn-ghost btn-sm more-toggle"
          :aria-expanded="moreOpen"
          :data-testid="`more-${item.position}`"
          @click="moreOpen = !moreOpen"
        >
          <Icon
            name="more"
            :size="16"
          /> Other options
        </button>
      </div>

      <div
        v-if="moreOpen && phase !== 'blocked'"
        class="more"
      >
        <button
          type="button"
          class="btn btn-sm"
          :data-testid="`no-evidence-${item.position}`"
          @click="act('complete', { no_evidence: true })"
        >
          Mark studied (no evidence)
        </button>
        <button
          type="button"
          class="btn btn-sm"
          :data-testid="`defer-${item.position}`"
          @click="act('defer')"
        >
          Do it tomorrow
        </button>
        <button
          type="button"
          class="btn btn-sm"
          :aria-expanded="skipping"
          :data-testid="`skip-${item.position}`"
          @click="skipping = !skipping"
        >
          Skip
        </button>
        <span
          v-if="skipping"
          class="skip"
          role="group"
          aria-label="Why skip?"
        >
          <button
            v-for="[code, label] in SKIP_REASONS"
            :key="code"
            type="button"
            class="chip"
            :data-testid="`skip-${item.position}-${code}`"
            @click="act('skip', { skip_reason: code })"
          >{{ label }}</button>
        </span>
      </div>

      <div
        v-if="logging && phase !== 'blocked'"
        class="capture"
      >
        <AttemptForm
          v-if="kind === 'ATTEMPT' && item.problems.length"
          :problem-id="item.problems[0]!.id"
          :client="client"
          :plan-item-id="item.id"
          :start-logging="phase === 'in-progress'"
          :suggested-minutes="suggestedMinutes"
          @recorded="(_a, effects) => finished(effects)"
        />
        <AssessmentForm
          v-else-if="kind && kind !== 'ATTEMPT' && kind !== 'ITEM_DEFINED' && item.skill"
          :client="client"
          :kind="kind"
          :skills="[{ key: item.skill, name: text.skillLabel ?? item.skill }]"
          :source-key="`plan:${item.candidate_key}`"
          :plan-item-id="item.id"
          @recorded="finished"
        />
      </div>
      <p
        v-if="error"
        role="alert"
        class="error"
      >
        {{ error }}
      </p>
    </template>
  </li>
</template>

<style scoped>
.mission {
  list-style: none; display: grid; gap: var(--s-3); padding: var(--s-5); background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r-lg); box-shadow: var(--shadow-sm);
  transition: box-shadow var(--t-base) var(--ease), border-color var(--t-base) var(--ease), background var(--t-base) var(--ease);
}
.mission.is-not-started:hover, .mission.is-in-progress:hover { box-shadow: var(--shadow-md); border-color: var(--border-strong); }
.mission.is-in-progress { border-color: var(--accent-border); box-shadow: 0 0 0 3px var(--accent-soft); }
.mission.is-completed { background: var(--surface-2); box-shadow: none; padding: var(--s-3) var(--s-4); }
.mission.is-skipped, .mission.is-deferred { background: transparent; border-style: dashed; box-shadow: none; padding: var(--s-3) var(--s-4); }
.mission.is-blocked { background: var(--blocked-bg); }

.head { display: flex; align-items: flex-start; gap: var(--s-4); }
.index { font-size: var(--fs-xl); font-weight: 700; letter-spacing: -0.03em; color: var(--accent); min-width: 2rem; line-height: 1.2; }
.titles { flex: 1; min-width: 0; display: grid; gap: var(--s-1); }
.titles h3 { font-size: var(--fs-lg); letter-spacing: -0.015em; text-wrap: balance; }
.meta { display: flex; align-items: center; gap: var(--s-1); font-size: var(--fs-sm); color: var(--text-3); }
.task { color: var(--text-2); padding-left: calc(2rem + var(--s-4)); }

.why, .outcome, .problems, .rule, .blocked, .timer, .actions, .more, .capture, .error { margin-left: calc(2rem + var(--s-4)); }
.why { display: grid; gap: var(--s-1); color: var(--text-2); }
.label { font-size: var(--fs-xs); font-weight: 650; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-3); }
.why-toggle { width: fit-content; background: none; border: 0; padding: 0; font: inherit; font-size: var(--fs-sm); color: var(--text-3); text-decoration: underline; text-underline-offset: 2px; cursor: pointer; }
.why-toggle:hover { color: var(--text); }
.numbers { display: flex; gap: var(--s-5); font-size: var(--fs-sm); padding: var(--s-2) var(--s-3); background: var(--surface-2); border-radius: var(--r-md); width: fit-content; }
.numbers dt { color: var(--text-3); }
.numbers dd { font-weight: 650; }
.outcome { display: flex; gap: var(--s-2); align-items: flex-start; font-size: var(--fs-sm); color: var(--text-2); }
.outcome :deep(svg) { margin-top: 0.2rem; color: var(--accent); }
.problems { display: grid; gap: var(--s-1); font-size: var(--fs-sm); }
.problems li { display: flex; align-items: center; gap: var(--s-2); }
.rule { font-size: var(--fs-sm); color: var(--text-3); }
.blocked { display: flex; gap: var(--s-2); align-items: center; font-size: var(--fs-sm); color: var(--blocked-fg); }
.timer { font-size: var(--fs-xl); font-weight: 650; letter-spacing: -0.01em; color: var(--accent-text); }
.actions { display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap; margin-top: var(--s-1); }
.more-toggle { margin-left: auto; color: var(--text-3); }
.more { display: flex; gap: var(--s-2); flex-wrap: wrap; align-items: center; padding: var(--s-3); background: var(--surface-2); border-radius: var(--r-md); }
.skip { display: flex; gap: var(--s-1); flex-wrap: wrap; }
.chip { border-radius: 999px; border: 1px solid var(--border-strong); background: var(--surface); padding: 0.2rem 0.7rem; font: inherit; font-size: var(--fs-sm); cursor: pointer; }
.chip:hover { background: var(--accent-soft); border-color: var(--accent-border); }
.capture { margin-top: var(--s-1); }
.error { color: var(--critical-fg); font-size: var(--fs-sm); }

.done-row { display: flex; align-items: center; gap: var(--s-3); }
.mark { display: grid; place-items: center; flex: none; width: 1.6rem; height: 1.6rem; border-radius: 50%; }
.mark.completed { background: var(--healthy-fg); color: #fff; animation: pop 320ms var(--ease); }
.mark.skipped, .mark.deferred { background: var(--surface-3); color: var(--text-2); }
.done-text { flex: 1; min-width: 0; }
.done-title { font-weight: 600; }
.struck { color: var(--text-3); text-decoration: line-through; text-decoration-thickness: 1px; }
.after { margin-top: var(--s-3); }
@keyframes pop { from { transform: scale(0.6); opacity: 0; } to { transform: scale(1); opacity: 1; } }

@media (max-width: 767px) {
  .mission { padding: var(--s-4); }
  .why, .outcome, .problems, .rule, .blocked, .timer, .actions, .more, .capture, .error, .task { margin-left: 0; padding-left: 0; }
  .index { min-width: 1.6rem; }
  .actions .btn-primary { flex: 1 1 100%; }
}
.session-preview { display: grid; gap: var(--s-1); padding: var(--s-3); border-radius: var(--r-md); background: var(--accent-soft); }
.session-preview ol { list-style: decimal; padding-left: var(--s-5); display: grid; gap: 2px; font-size: var(--fs-sm); }
</style>

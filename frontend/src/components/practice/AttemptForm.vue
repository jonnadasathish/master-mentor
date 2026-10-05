<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import type { ApiClient } from '../../api/client'
import { ApiError } from '../../api/client'
import type { Effects, ProblemAttempt, SkillDelta, StepResult } from '../../api/types'
import Icon from '../common/Icon.vue'
import SkillDeltas from '../missions/SkillDeltas.vue'
import { buildAttemptPayload, emptyForm, formErrors, formFromAttempt, newRequestId } from '../../practice/payload'
import { MISTAKES, OUTCOMES } from '../../practice/vocabulary'

/**
 * Start → (optional) confidence before → timer → log. One screen, sensible defaults, < 60 s to log.
 * The timer only pre-fills the minutes field; the stored duration is whatever is submitted.
 */
const props = defineProps<{
  problemId: number
  client: ApiClient
  now?: () => number
  batteryItemKey?: string
  revisionItemKey?: string
  planItemId?: number
  correctionOf?: ProblemAttempt
  /** Open straight at the result form (the caller already ran a timer). */
  startLogging?: boolean
  /** Minutes to prefill when the caller timed the attempt. */
  suggestedMinutes?: number | null
  /** A learning-session step: the attempt completes that step (LEARNING_ENGINE §5). */
  sessionStep?: { sessionId: number; position: number }
}>()
const emit = defineEmits<{
  recorded: [attempt: ProblemAttempt, effects?: Effects]
  step: [result: StepResult, effects?: Effects]
}>()

const clockNow = () => (props.now ? props.now() : Date.now())
const form = reactive(props.correctionOf ? formFromAttempt(props.correctionOf) : emptyForm())
const phase = ref<'idle' | 'running' | 'logging' | 'saved'>(props.correctionOf || props.startLogging ? 'logging' : 'idle')
if (props.suggestedMinutes && form.minutes === null) form.minutes = props.suggestedMinutes
const startedAt = ref<number | null>(null)
const tick = ref(0)
const errors = ref<string[]>([])
const saving = ref(false)
const showMore = ref(false)
const requestId = ref(newRequestId())
const deltas = ref<SkillDelta[]>([])
let timer: ReturnType<typeof setInterval> | undefined

const elapsedSeconds = computed(() => {
  void tick.value
  return startedAt.value === null ? 0 : Math.max(0, Math.floor((clockNow() - startedAt.value) / 1000))
})
const elapsedLabel = computed(() => {
  const s = elapsedSeconds.value
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
})

function start(): void {
  startedAt.value = clockNow()
  phase.value = 'running'
  timer = setInterval(() => (tick.value += 1), 1000)
}

function finish(): void {
  if (timer) clearInterval(timer)
  if (startedAt.value !== null) {
    // Read the clock now (the computed label only refreshes once per second).
    const seconds = Math.max(0, Math.floor((clockNow() - startedAt.value) / 1000))
    form.minutes = Math.max(1, Math.round(seconds / 60))
  }
  phase.value = 'logging'
}

function logWithoutTimer(): void {
  phase.value = 'logging'
}

function toggleMistake(code: string): void {
  form.mistakes = form.mistakes.includes(code) ? form.mistakes.filter((m) => m !== code) : [...form.mistakes, code]
}

async function save(): Promise<void> {
  errors.value = formErrors(form)
  if (errors.value.length) return
  saving.value = true
  try {
    const payload = buildAttemptPayload(props.problemId, form, requestId.value)
    const links = {
      ...(props.batteryItemKey ? { battery_item_key: props.batteryItemKey, mode: 'BASELINE' } : {}),
      ...(props.revisionItemKey ? { revision_item_key: props.revisionItemKey, mode: 'REVISION' } : {}),
    }
    const body = { ...payload, ...links }
    let attempt: ProblemAttempt
    let effects: Effects | undefined
    if (props.correctionOf) {
      // A correction appends a new version; the original row is never modified.
      const envelope = await props.client.post<ProblemAttempt>(`/problem-attempts/${props.correctionOf.id}/corrections`, body)
      deltas.value = envelope.effects?.skill_deltas ?? []
      effects = envelope.effects
      attempt = envelope.data
    } else if (props.sessionStep) {
      const { sessionId, position } = props.sessionStep
      const envelope = await props.client.post<StepResult>(
        `/learning/sessions/${sessionId}/steps/${position}/complete`,
        { attempt: body },
      )
      deltas.value = envelope.effects?.skill_deltas ?? []
      phase.value = 'saved'
      emit('step', envelope.data, envelope.effects)
      return
    } else if (props.planItemId !== undefined) {
      // Completing a plan item: the server links the observation (and battery/revision keys) to the item.
      const envelope = await props.client.post<{ observation: ProblemAttempt }>(
        `/plan/items/${props.planItemId}/complete`,
        { observation: { type: 'ATTEMPT', body } },
      )
      deltas.value = envelope.effects?.skill_deltas ?? []
      effects = envelope.effects
      attempt = envelope.data.observation
    } else {
      const envelope = await props.client.post<ProblemAttempt>('/problem-attempts', body)
      deltas.value = envelope.effects?.skill_deltas ?? []
      effects = envelope.effects
      attempt = envelope.data
    }
    phase.value = 'saved'
    emit('recorded', attempt, effects)
  } catch (caught) {
    if (caught instanceof ApiError) {
      const details = caught.details.errors as { loc: string[]; msg: string }[] | undefined
      errors.value = details?.map((d) => `${d.loc.at(-1)}: ${d.msg}`) ?? [`${caught.code}: ${caught.message}`]
    } else {
      errors.value = [String(caught)]
    }
  } finally {
    saving.value = false
  }
}

function again(): void {
  Object.assign(form, emptyForm())
  requestId.value = newRequestId()
  startedAt.value = null
  errors.value = []
  phase.value = 'idle'
}

onBeforeUnmount(() => timer && clearInterval(timer))
</script>

<template>
  <section
    class="attempt-form"
    aria-label="Log an attempt"
  >
    <!-- 1. Before you start -->
    <div
      v-if="phase === 'idle'"
      class="stack"
    >
      <fieldset class="confidence">
        <legend>How confident are you that you can solve it? <span class="muted">(optional)</span></legend>
        <div class="chips">
          <button
            v-for="n in 5"
            :key="n"
            type="button"
            class="chip"
            :aria-pressed="form.confidenceBefore === n"
            :data-testid="`confidence-before-${n}`"
            @click="form.confidenceBefore = form.confidenceBefore === n ? null : n"
          >
            {{ n }}
          </button>
        </div>
        <p class="scale muted">
          1 = no idea · 5 = I've got this
        </p>
      </fieldset>
      <div class="row">
        <button
          type="button"
          class="btn btn-primary btn-lg"
          data-testid="start"
          @click="start"
        >
          <Icon
            name="play"
            :size="14"
          /> Start attempt
        </button>
        <button
          type="button"
          class="btn btn-ghost"
          data-testid="log-direct"
          @click="logWithoutTimer"
        >
          I already solved it
        </button>
      </div>
    </div>

    <!-- 2. Solving: nothing but the clock and a scratchpad -->
    <div
      v-else-if="phase === 'running'"
      class="solving"
    >
      <p
        class="timer tabular"
        data-testid="timer"
        aria-live="off"
      >
        {{ elapsedLabel }}
      </p>
      <label class="notes"><span>Scratch notes <span class="muted">(optional)</span></span>
        <textarea
          v-model="form.notes"
          rows="3"
          maxlength="4000"
          placeholder="Approach, edge cases, what you're stuck on…"
        />
      </label>
      <button
        type="button"
        class="btn btn-primary btn-lg"
        data-testid="finish"
        @click="finish"
      >
        Finish &amp; log result
      </button>
    </div>

    <!-- 3. How did it go? -->
    <form
      v-else-if="phase === 'logging'"
      class="stack"
      data-testid="log-form"
      @submit.prevent="save"
    >
      <fieldset class="outcomes">
        <legend>How did it go?</legend>
        <div class="chips">
          <label
            v-for="o in OUTCOMES"
            :key="o.value"
            class="outcome"
            :class="[`o-${o.value.toLowerCase()}`, { chosen: form.outcome === o.value }]"
          >
            <input
              v-model="form.outcome"
              type="radio"
              name="outcome"
              :value="o.value"
              :data-testid="`outcome-${o.value}`"
            >
            {{ o.label }}
          </label>
        </div>
      </fieldset>

      <div class="fields">
        <label>Time (minutes)
          <input
            v-model.number="form.minutes"
            type="number"
            min="0"
            step="1"
            data-testid="minutes"
          >
        </label>
        <label>Hints used
          <input
            v-model.number="form.hints"
            type="number"
            min="0"
            data-testid="hints"
          >
        </label>
        <label>Confidence now
          <select
            v-model.number="form.confidenceAfter"
            data-testid="confidence-after"
          >
            <option :value="null">—</option>
            <option
              v-for="n in 5"
              :key="n"
              :value="n"
            >{{ n }}</option>
          </select>
        </label>
        <label>How well could you explain it? (0–10)
          <select
            v-model.number="form.explanation"
            data-testid="explanation"
          >
            <option :value="null">—</option>
            <option
              v-for="n in 11"
              :key="n - 1"
              :value="n - 1"
            >{{ n - 1 }}</option>
          </select>
        </label>
        <label>Was your complexity right?
          <select
            v-model="form.complexityCorrect"
            data-testid="complexity"
          >
            <option :value="null">—</option>
            <option :value="true">Yes</option>
            <option :value="false">No</option>
          </select>
        </label>
      </div>

      <fieldset>
        <legend>What went wrong? <span class="muted">(pick any)</span></legend>
        <div class="chips">
          <button
            v-for="m in MISTAKES"
            :key="m.value"
            type="button"
            class="chip"
            :aria-pressed="form.mistakes.includes(m.value)"
            :data-testid="`mistake-${m.value}`"
            @click="toggleMistake(m.value)"
          >
            {{ m.label }}
          </button>
        </div>
      </fieldset>

      <label class="notes"><span>Notes</span>
        <textarea
          v-model="form.notes"
          rows="2"
          maxlength="4000"
        />
      </label>

      <button
        type="button"
        class="link-btn more"
        :aria-expanded="showMore"
        @click="showMore = !showMore"
      >
        {{ showMore ? 'Fewer fields' : 'More fields' }}
      </button>
      <div
        v-if="showMore"
        class="fields more-fields"
      >
        <label class="check"><input
          v-model="form.solutionViewed"
          type="checkbox"
        > I viewed the solution</label>
        <label class="check"><input
          v-model="form.seenElsewhere"
          type="checkbox"
        > I'd seen it before</label>
        <label>Did you name the pattern before any hints?
          <select v-model="form.patternIdentified">
            <option :value="null">—</option>
            <option :value="true">Yes</option>
            <option :value="false">No</option>
          </select>
        </label>
        <label>Did you solve the follow-up?
          <select v-model="form.followupSolved">
            <option :value="null">—</option>
            <option :value="true">Yes</option>
            <option :value="false">No</option>
          </select>
        </label>
        <label class="check"><input
          v-model="form.timed"
          type="checkbox"
        > It was timed</label>
        <label v-if="form.timed">Time limit (minutes)
          <input
            v-model.number="form.limitMinutes"
            type="number"
            min="1"
          >
        </label>
      </div>

      <ul
        v-if="errors.length"
        role="alert"
        class="errors"
        data-testid="form-errors"
      >
        <li
          v-for="e in errors"
          :key="e"
        >
          {{ e }}
        </li>
      </ul>
      <div class="row">
        <button
          type="submit"
          class="btn btn-primary btn-lg"
          :disabled="saving"
          data-testid="save"
        >
          {{ saving ? 'Saving…' : 'Save attempt' }}
        </button>
      </div>
    </form>

    <!-- 4. Done -->
    <div
      v-else
      class="stack saved"
    >
      <p
        class="ok"
        role="status"
        data-testid="recorded"
      >
        {{ correctionOf ? 'Correction recorded (the original is kept).' : 'Attempt recorded.' }}
      </p>
      <SkillDeltas :deltas="deltas" />
      <div class="row">
        <button
          type="button"
          class="btn"
          @click="again"
        >
          Log another attempt
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.attempt-form { padding: var(--s-5); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); }
.stack { display: grid; gap: var(--s-4); }
legend { font-weight: 650; margin-bottom: var(--s-2); font-size: var(--fs-base); color: var(--text); }
.chips { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.chip, .outcome {
  display: inline-flex; align-items: center; gap: var(--s-1); min-height: 2.4rem; padding: 0 var(--s-4); border-radius: 999px;
  border: 1px solid var(--border-strong); background: var(--surface); color: var(--text); font: inherit; font-size: var(--fs-sm); font-weight: 560; cursor: pointer;
  transition: background var(--t-fast) var(--ease), border-color var(--t-fast) var(--ease);
}
.chip:hover, .outcome:hover { background: var(--surface-2); }
.chip[aria-pressed='true'] { background: var(--accent-soft); border-color: var(--accent); color: var(--accent-text); }
.outcome { padding: 0 var(--s-5); font-size: var(--fs-base); }
.outcome input { position: absolute; opacity: 0; pointer-events: none; }
.outcome.chosen.o-pass { background: var(--healthy-bg); border-color: var(--healthy-fg); color: var(--healthy-fg); }
.outcome.chosen.o-partial { background: var(--medium-bg); border-color: var(--medium-fg); color: var(--medium-fg); }
.outcome.chosen.o-fail { background: var(--critical-bg); border-color: var(--critical-fg); color: var(--critical-fg); }
.outcome:focus-within { outline: 2px solid var(--accent); outline-offset: 2px; }
.scale { font-size: var(--fs-xs); margin-top: var(--s-2); }
.solving { display: grid; gap: var(--s-4); justify-items: center; text-align: center; }
.timer { font-size: 3.5rem; font-weight: 700; letter-spacing: -0.03em; color: var(--accent-text); line-height: 1; }
.solving .notes { width: 100%; text-align: left; }
.fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr)); gap: var(--s-3) var(--s-4); }
.fields label, .notes { display: grid; gap: var(--s-1); align-content: start; }
.fields input[type='number'] { width: 100%; }
.check { display: flex !important; flex-direction: row; align-items: center; gap: var(--s-2) !important; }
.more { width: fit-content; font-size: var(--fs-sm); }
.errors { color: var(--critical-fg); font-size: var(--fs-sm); display: grid; gap: var(--s-1); }
.ok { font-weight: 650; color: var(--healthy-fg); font-size: var(--fs-md); }
@media (max-width: 767px) {
  .attempt-form { padding: var(--s-4); }
  .timer { font-size: 3rem; }
  .row .btn-lg { flex: 1 1 100%; }
}
</style>

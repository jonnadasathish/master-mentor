<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue'
import type { ApiClient } from '../api/client'
import { ApiError } from '../api/client'
import type { Effects, ProblemAttempt, SkillDelta } from '../api/types'
import SkillDeltas from './SkillDeltas.vue'
import { buildAttemptPayload, emptyForm, formErrors, formFromAttempt, newRequestId } from '../practice/payload'
import { MISTAKES, OUTCOMES } from '../practice/vocabulary'

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
}>()
const emit = defineEmits<{ recorded: [attempt: ProblemAttempt, effects?: Effects] }>()

const clockNow = () => (props.now ? props.now() : Date.now())
const form = reactive(props.correctionOf ? formFromAttempt(props.correctionOf) : emptyForm())
const phase = ref<'idle' | 'running' | 'logging' | 'saved'>(props.correctionOf ? 'logging' : 'idle')
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
    <div
      v-if="phase === 'idle'"
      class="row"
    >
      <label>
        Confidence before (optional)
        <select
          v-model.number="form.confidenceBefore"
          data-testid="confidence-before"
        >
          <option :value="null">—</option>
          <option
            v-for="n in 5"
            :key="n"
            :value="n"
          >{{ n }}</option>
        </select>
      </label>
      <button
        type="button"
        data-testid="start"
        @click="start"
      >
        Start attempt
      </button>
      <button
        type="button"
        class="secondary"
        data-testid="log-direct"
        @click="logWithoutTimer"
      >
        Log a finished attempt
      </button>
    </div>

    <div
      v-else-if="phase === 'running'"
      class="row"
    >
      <span
        class="timer"
        data-testid="timer"
        aria-live="off"
      >{{ elapsedLabel }}</span>
      <button
        type="button"
        data-testid="finish"
        @click="finish"
      >
        Finish &amp; log
      </button>
    </div>

    <form
      v-else-if="phase === 'logging'"
      data-testid="log-form"
      @submit.prevent="save"
    >
      <fieldset class="outcomes">
        <legend>Result</legend>
        <label
          v-for="o in OUTCOMES"
          :key="o.value"
          :class="{ chosen: form.outcome === o.value }"
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
      </fieldset>

      <div class="row">
        <label>Time (min)
          <input
            v-model.number="form.minutes"
            type="number"
            min="0"
            step="1"
            data-testid="minutes"
          >
        </label>
        <label>Hints
          <input
            v-model.number="form.hints"
            type="number"
            min="0"
            data-testid="hints"
          >
        </label>
        <label>Confidence after
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
        <label>Explanation (0–10)
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
        <label>Complexity correct?
          <select
            v-model="form.complexityCorrect"
            data-testid="complexity"
          >
            <option :value="null">—</option>
            <option :value="true">yes</option>
            <option :value="false">no</option>
          </select>
        </label>
      </div>

      <fieldset>
        <legend>Mistakes</legend>
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
      </fieldset>

      <label class="notes">Notes
        <textarea
          v-model="form.notes"
          rows="2"
          maxlength="4000"
        />
      </label>

      <button
        type="button"
        class="link"
        :aria-expanded="showMore"
        @click="showMore = !showMore"
      >
        {{ showMore ? 'Fewer fields' : 'More fields' }}
      </button>
      <div
        v-if="showMore"
        class="row more"
      >
        <label><input
          v-model="form.solutionViewed"
          type="checkbox"
        > Viewed solution</label>
        <label><input
          v-model="form.seenElsewhere"
          type="checkbox"
        > Seen before elsewhere</label>
        <label>Named the pattern before hints?
          <select v-model="form.patternIdentified">
            <option :value="null">—</option>
            <option :value="true">yes</option>
            <option :value="false">no</option>
          </select>
        </label>
        <label>Follow-up solved?
          <select v-model="form.followupSolved">
            <option :value="null">—</option>
            <option :value="true">yes</option>
            <option :value="false">no</option>
          </select>
        </label>
        <label><input
          v-model="form.timed"
          type="checkbox"
        > Timed</label>
        <label v-if="form.timed">Limit (min)
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
      <button
        type="submit"
        :disabled="saving"
        data-testid="save"
      >
        {{ saving ? 'Saving…' : 'Save attempt' }}
      </button>
    </form>

    <div
      v-else
      class="row"
    >
      <p
        role="status"
        data-testid="recorded"
      >
        {{ correctionOf ? 'Correction recorded (the original is kept).' : 'Attempt recorded.' }}
      </p>
      <SkillDeltas :deltas="deltas" />
      <button
        type="button"
        class="secondary"
        @click="again"
      >
        Log another attempt
      </button>
    </div>
  </section>
</template>

<style scoped>
.attempt-form { border: 1px solid #d8d8de; border-radius: 8px; padding: 0.75rem 1rem; margin: 1rem 0; background: #fff; }
.row { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: end; margin: 0.5rem 0; }
label { display: flex; flex-direction: column; font-size: 0.85rem; gap: 0.2rem; }
.more label { flex-direction: row; align-items: center; }
input[type='number'] { width: 5rem; }
.outcomes { display: flex; gap: 0.5rem; border: none; padding: 0; }
.outcomes label { flex-direction: row; align-items: center; gap: 0.3rem; border: 1px solid #ccc; border-radius: 6px; padding: 0.3rem 0.6rem; }
.outcomes label.chosen { background: #e3ecff; border-color: #3366cc; }
fieldset { border: none; padding: 0; margin: 0.5rem 0; }
.chip { margin: 0.15rem; border-radius: 999px; border: 1px solid #bbb; background: #f6f6f8; padding: 0.2rem 0.6rem; }
.chip[aria-pressed='true'] { background: #fde8e8; border-color: #d33; }
.timer { font-size: 1.6rem; font-variant-numeric: tabular-nums; }
.notes { width: 100%; }
.notes textarea { width: 100%; }
.errors { color: #a11; }
.secondary { background: none; border: 1px solid #888; }
.link { background: none; border: none; color: #2a55b0; text-decoration: underline; cursor: pointer; padding: 0; }
</style>

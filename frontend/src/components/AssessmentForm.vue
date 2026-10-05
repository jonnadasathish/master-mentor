<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { ApiClient } from '../api/client'
import { ApiError } from '../api/client'
import type { AssessmentRecord, Effects, SkillDelta } from '../api/types'
import { assessmentErrors, buildAssessmentPayload, emptyAssessmentForm } from '../practice/assessment'
import { newRequestId } from '../practice/payload'
import SkillDeltas from './SkillDeltas.vue'

/** Generic assessment logger: one prompt/exercise, points per observed skill, practice conditions. */
const props = defineProps<{
  client: ApiClient
  kind: string
  skills: { key: string; name: string }[]
  sourceKey: string
  batteryItemKey?: string
  revisionItemKey?: string
  planItemId?: number
  correctionOf?: AssessmentRecord
}>()
const emit = defineEmits<{ recorded: [effects?: Effects] }>()

const form = reactive(emptyAssessmentForm(props.sourceKey, props.skills.map((s) => s.key)))
if (props.correctionOf) {
  const c = props.correctionOf
  for (const s of c.skills) form.points[s.skill] = s.outcome_points
  Object.assign(form, {
    notesUsed: c.notes_used, referenceUsed: c.reference_used, hints: c.hints_used, timed: c.timed,
    limitMinutes: c.time_limit_seconds === null ? null : Math.round(c.time_limit_seconds / 60),
    minutes: c.time_seconds === null ? null : Math.round(c.time_seconds / 60),
    followupPoints: c.followup_points, notes: c.notes ?? '',
  })
}
const errors = ref<string[]>([])
const saving = ref(false)
const saved = ref(false)
const deltas = ref<SkillDelta[]>([])
const requestId = ref(newRequestId())

async function save(): Promise<void> {
  errors.value = assessmentErrors(form)
  if (errors.value.length) return
  saving.value = true
  try {
    const body = buildAssessmentPayload(props.kind, form, requestId.value, props.batteryItemKey, props.revisionItemKey)
    const envelope = props.correctionOf
      ? await props.client.post(`/assessments/${props.correctionOf.id}/corrections`, {
        ...body, observed_at: props.correctionOf.observed_at,
      })
      : props.planItemId !== undefined
        ? await props.client.post(`/plan/items/${props.planItemId}/complete`, { observation: { type: 'ASSESSMENT', body } })
        : await props.client.post('/assessments', body)
    deltas.value = envelope.effects?.skill_deltas ?? []
    saved.value = true
    emit('recorded', envelope.effects)
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
</script>

<template>
  <div
    v-if="saved"
    class="assessment-form"
  >
    <p
      role="status"
      data-testid="assessment-recorded"
    >
      Assessment recorded.
    </p>
    <SkillDeltas :deltas="deltas" />
  </div>
  <form
    v-else
    class="assessment-form"
    data-testid="assessment-form"
    @submit.prevent="save"
  >
    <label>Prompt / exercise key
      <input
        v-model="form.sourceKey"
        data-testid="source-key"
        maxlength="96"
      >
    </label>
    <fieldset>
      <legend>Points per skill (0–100, blank = not observed)</legend>
      <label
        v-for="s in skills"
        :key="s.key"
        class="skill"
      >
        <span>{{ s.name }}</span>
        <input
          v-model.number="form.points[s.key]"
          type="number"
          min="0"
          max="100"
          :data-testid="`points-${s.key}`"
        >
      </label>
    </fieldset>
    <div class="row">
      <label><input
        v-model="form.notesUsed"
        type="checkbox"
        data-testid="notes-used"
      > Used notes</label>
      <label><input
        v-model="form.referenceUsed"
        type="checkbox"
      > Used a reference</label>
      <label>Hints <input
        v-model.number="form.hints"
        type="number"
        min="0"
      ></label>
      <label><input
        v-model="form.timed"
        type="checkbox"
      > Timed</label>
      <label v-if="form.timed">Limit (min) <input
        v-model.number="form.limitMinutes"
        type="number"
        min="1"
      ></label>
      <label v-if="form.timed">Took (min) <input
        v-model.number="form.minutes"
        type="number"
        min="0"
      ></label>
      <label>Follow-up points <input
        v-model.number="form.followupPoints"
        type="number"
        min="0"
        max="100"
      ></label>
    </div>
    <label class="notes">Notes
      <textarea
        v-model="form.notes"
        rows="2"
        maxlength="4000"
      />
    </label>
    <ul
      v-if="errors.length"
      role="alert"
      class="errors"
      data-testid="assessment-errors"
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
      data-testid="save-assessment"
    >
      {{ saving ? 'Saving…' : 'Save assessment' }}
    </button>
  </form>
</template>

<style scoped>
.assessment-form { border: 1px solid #d8d8de; border-radius: 8px; padding: 0.75rem 1rem; margin: 0.5rem 0; background: #fff; }
label { display: flex; flex-direction: column; font-size: 0.85rem; gap: 0.2rem; }
.row { display: flex; flex-wrap: wrap; gap: 0.75rem; margin: 0.5rem 0; }
.row label { flex-direction: row; align-items: center; }
.skill { flex-direction: row; justify-content: space-between; max-width: 32rem; }
input[type='number'] { width: 5rem; }
fieldset { border: none; padding: 0; margin: 0.5rem 0; }
.notes textarea { width: 100%; }
.errors { color: #a11; }
</style>

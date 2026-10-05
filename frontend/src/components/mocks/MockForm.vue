<script setup lang="ts">
import { reactive, ref } from 'vue'
import { api } from '../../api'
import { ApiError } from '../../api/client'
import type { Effects, MockRoundInput } from '../../api/types'
import { emptyRound, mockErrors, ROUND_COMPONENTS, ROUND_TYPES } from '../../practice/mock'
import { newRequestId } from '../../practice/payload'
import { ROUND_LABEL } from '../../presentation/language'
import { useSkillsStore } from '../../stores/data'

/** Log a mock interview: rounds, the score of each, and the skills it exposed. Validation mirrors the server's. */
const props = defineProps<{ planItemId?: number; catalog: { key: string; component: string }[] }>()
const emit = defineEmits<{ recorded: [effects: Effects | null] }>()

const skills = useSkillsStore()
const form = reactive({ source: 'PEER', isFinal: false, rounds: [emptyRound()] as MockRoundInput[], notes: '' })
const pick = reactive<Record<number, string>>({})
const errors = ref<string[]>([])
const saving = ref(false)
const requestId = ref(newRequestId())

const skillOptions = (i: number) => {
  const r = form.rounds[i]!
  return props.catalog.filter((s) => ROUND_COMPONENTS[r.round_type].includes(s.component) && !r.skills.some((x) => x.skill === s.key))
}

function addSkill(i: number): void {
  const key = pick[i]
  if (key) form.rounds[i]!.skills.push({ skill: key, outcome_points: 60, is_weakness: false })
  pick[i] = ''
}

async function save(): Promise<void> {
  errors.value = mockErrors(form.rounds)
  if (errors.value.length) return
  saving.value = true
  const body = {
    source: form.source, is_final_simulation: form.isFinal, rounds: form.rounds,
    notes: form.notes.trim() || undefined, client_request_id: requestId.value,
  }
  try {
    const envelope = props.planItemId
      ? await api.post(`/plan/items/${props.planItemId}/complete`, { observation: { type: 'MOCK', body } })
      : await api.post('/mocks', body)
    form.rounds = [emptyRound()]
    requestId.value = newRequestId()
    emit('recorded', envelope.effects ?? null)
  } catch (caught) {
    if (caught instanceof ApiError) {
      const details = caught.details.errors as { loc: string[]; msg: string }[] | undefined
      errors.value = details?.map((d) => `${d.loc.slice(1).join('.')}: ${d.msg}`) ?? [caught.message]
    } else {
      errors.value = [String(caught)]
    }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form
    class="mock-form"
    data-testid="mock-form"
    @submit.prevent="save"
  >
    <div class="row">
      <label>Who ran it?
        <select
          v-model="form.source"
          data-testid="mock-source"
        >
          <option value="PEER">A peer</option>
          <option value="PLATFORM">A platform</option>
          <option value="SELF">Myself (scores count up to 80)</option>
        </select>
      </label>
      <label class="check"><input
        v-model="form.isFinal"
        type="checkbox"
        data-testid="mock-final"
      > Full interview simulation</label>
    </div>

    <fieldset
      v-for="(r, i) in form.rounds"
      :key="i"
      class="round"
      :data-testid="`round-${i}`"
    >
      <legend>Round {{ i + 1 }}</legend>
      <div class="row">
        <label>Type
          <select
            v-model="r.round_type"
            :data-testid="`round-${i}-type`"
          >
            <option
              v-for="t in ROUND_TYPES"
              :key="t"
              :value="t"
            >{{ ROUND_LABEL[t] }}</option>
          </select>
        </label>
        <label>Minutes <input
          v-model.number="r.duration_minutes"
          type="number"
          min="1"
        ></label>
        <label>Overall score (0–100) <input
          v-model.number="r.round_score"
          type="number"
          min="0"
          max="100"
          :data-testid="`round-${i}-score`"
        ></label>
        <button
          v-if="form.rounds.length > 1"
          type="button"
          class="btn btn-ghost btn-sm"
          @click="form.rounds.splice(i, 1)"
        >
          Remove round
        </button>
      </div>
      <ul
        v-if="r.skills.length"
        class="skills"
      >
        <li
          v-for="(s, j) in r.skills"
          :key="s.skill"
        >
          <span class="sname">{{ skills.nameOf(s.skill) }}</span>
          <label>Score <input
            v-model.number="s.outcome_points"
            type="number"
            min="0"
            max="100"
            :data-testid="`round-${i}-points-${s.skill}`"
          ></label>
          <label class="check"><input
            v-model="s.is_weakness"
            type="checkbox"
            :data-testid="`round-${i}-weak-${s.skill}`"
          > This was a weakness</label>
          <button
            type="button"
            class="link-btn"
            @click="r.skills.splice(j, 1)"
          >
            Remove
          </button>
        </li>
      </ul>
      <div class="row">
        <label>Skill it exposed
          <select
            v-model="pick[i]"
            :data-testid="`round-${i}-skill`"
          >
            <option value="">Choose…</option>
            <option
              v-for="s in skillOptions(i)"
              :key="s.key"
              :value="s.key"
            >{{ skills.nameOf(s.key) }}</option>
          </select>
        </label>
        <button
          type="button"
          class="btn btn-sm"
          :data-testid="`round-${i}-add-skill`"
          @click="addSkill(i)"
        >
          Add skill
        </button>
      </div>
    </fieldset>

    <button
      type="button"
      class="btn btn-ghost btn-sm add"
      data-testid="add-round"
      @click="form.rounds.push(emptyRound('CS'))"
    >
      + Add a round
    </button>
    <label>Notes <textarea
      v-model="form.notes"
      rows="2"
      maxlength="4000"
    /></label>
    <ul
      v-if="errors.length"
      role="alert"
      class="errors"
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
      class="btn btn-primary btn-lg save"
      :disabled="saving"
      data-testid="save-mock"
    >
      {{ saving ? 'Saving…' : 'Save mock' }}
    </button>
  </form>
</template>

<style scoped>
.mock-form { display: grid; gap: var(--s-4); }
.row { display: flex; gap: var(--s-3) var(--s-4); flex-wrap: wrap; align-items: end; }
label { display: grid; gap: var(--s-1); }
.check { display: flex; align-items: center; gap: var(--s-2); }
input[type='number'] { width: 6rem; }
.round { display: grid; gap: var(--s-3); padding: var(--s-4); border: 1px solid var(--border); border-radius: var(--r-md); background: var(--surface-2); }
legend { font-weight: 650; padding: 0 var(--s-2); color: var(--text); }
.skills { display: grid; gap: var(--s-2); }
.skills li { display: flex; flex-wrap: wrap; align-items: center; gap: var(--s-3) var(--s-4); }
.sname { flex: 1 1 12rem; font-weight: 560; }
.add { width: fit-content; }
.errors { color: var(--critical-fg); font-size: var(--fs-sm); display: grid; gap: var(--s-1); }
.save { width: fit-content; }
</style>

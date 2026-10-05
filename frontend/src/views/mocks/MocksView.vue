<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../../api'
import { ApiError } from '../../api/client'
import type { Effects, MockRecord, MockRoundInput, MockSummary } from '../../api/types'
import EffectsPanel from '../../components/EffectsPanel.vue'
import { emptyRound, mockErrors, ROUND_COMPONENTS, ROUND_TYPES } from '../../practice/mock'
import { newRequestId } from '../../practice/payload'
import { useErrorStore } from '../../stores/errors'

const route = useRoute()
const planItemId = typeof route.query.plan_item === 'string' ? Number(route.query.plan_item) : undefined
const summary = ref<MockSummary | null>(null)
const mocks = ref<MockRecord[]>([])
const skills = ref<{ key: string; component: string }[]>([])
const form = reactive({ source: 'PEER', isFinal: false, rounds: [emptyRound()] as MockRoundInput[], notes: '' })
const pick = reactive<Record<number, string>>({})
const errors = ref<string[]>([])
const effects = ref<Effects | null>(null)
const saving = ref(false)
const requestId = ref(newRequestId())
const errorStore = useErrorStore()

const skillOptions = (i: number) => {
  const r = form.rounds[i]!
  return skills.value.filter((s) => ROUND_COMPONENTS[r.round_type].includes(s.component) && !r.skills.some((x) => x.skill === s.key))
}
const flagged = computed(() => summary.value?.repeated_weaknesses ?? [])

async function load(): Promise<void> {
  try {
    summary.value = (await api.get<MockSummary>('/mocks/summary')).data
    mocks.value = (await api.get<MockRecord[]>('/mocks', { limit: 20 })).data
  } catch (caught) {
    errorStore.report(caught, 'mocks')
  }
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
    const envelope = planItemId
      ? await api.post(`/plan/items/${planItemId}/complete`, { observation: { type: 'MOCK', body } })
      : await api.post('/mocks', body)
    effects.value = envelope.effects ?? null
    form.rounds = [emptyRound()]
    requestId.value = newRequestId()
    await load()
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

onMounted(async () => {
  await load()
  try {
    skills.value = (await api.get<{ key: string; component: string }[]>('/catalog/skills')).data
  } catch (caught) {
    errorStore.report(caught, 'mocks')
  }
})
</script>

<template>
  <section>
    <h1>Mocks</h1>
    <p
      v-if="planItemId"
      class="note"
    >
      Logging the mock for plan item #{{ planItemId }}.
    </p>

    <form
      class="card"
      data-testid="mock-form"
      @submit.prevent="save"
    >
      <h2>Log a mock</h2>
      <div class="row">
        <label>Source
          <select
            v-model="form.source"
            data-testid="mock-source"
          >
            <option value="PEER">Peer</option>
            <option value="PLATFORM">Platform</option>
            <option value="SELF">Self (scores capped at 80)</option>
          </select>
        </label>
        <label class="inline"><input
          v-model="form.isFinal"
          type="checkbox"
          data-testid="mock-final"
        > Final simulation</label>
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
              >{{ t.toLowerCase().replace(/_/g, ' ') }}</option>
            </select>
          </label>
          <label>Minutes <input
            v-model.number="r.duration_minutes"
            type="number"
            min="1"
          ></label>
          <label>Round score <input
            v-model.number="r.round_score"
            type="number"
            min="0"
            max="100"
            :data-testid="`round-${i}-score`"
          ></label>
          <button
            v-if="form.rounds.length > 1"
            type="button"
            class="secondary"
            @click="form.rounds.splice(i, 1)"
          >
            Remove round
          </button>
        </div>
        <table v-if="r.skills.length">
          <tbody>
            <tr
              v-for="(s, j) in r.skills"
              :key="s.skill"
            >
              <td>{{ s.skill }}</td>
              <td>
                <label>points <input
                  v-model.number="s.outcome_points"
                  type="number"
                  min="0"
                  max="100"
                  :data-testid="`round-${i}-points-${s.skill}`"
                ></label>
              </td>
              <td>
                <label class="inline"><input
                  v-model="s.is_weakness"
                  type="checkbox"
                  :data-testid="`round-${i}-weak-${s.skill}`"
                > weakness</label>
              </td>
              <td>
                <button
                  type="button"
                  class="link"
                  @click="r.skills.splice(j, 1)"
                >
                  remove
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="row">
          <label>Skill observed
            <select
              v-model="pick[i]"
              :data-testid="`round-${i}-skill`"
            >
              <option value="">Choose…</option>
              <option
                v-for="s in skillOptions(i)"
                :key="s.key"
                :value="s.key"
              >{{ s.key }}</option>
            </select>
          </label>
          <button
            type="button"
            class="secondary"
            :data-testid="`round-${i}-add-skill`"
            @click="addSkill(i)"
          >
            Add skill
          </button>
        </div>
      </fieldset>
      <button
        type="button"
        class="secondary"
        data-testid="add-round"
        @click="form.rounds.push(emptyRound('CS'))"
      >
        Add round
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
        :disabled="saving"
        data-testid="save-mock"
      >
        {{ saving ? 'Saving…' : 'Save mock' }}
      </button>
    </form>
    <EffectsPanel
      v-if="effects"
      :effects="effects"
    />

    <template v-if="summary">
      <h2>Round types (last 60 days) · G6 {{ summary.g6_passed ? '✓ passes' : '✗ failing' }}</h2>
      <table data-testid="mock-types">
        <thead>
          <tr><th>Type</th><th>Rounds</th><th>Non-self</th><th>Latest</th><th>Trend</th><th>G6</th></tr>
        </thead>
        <tbody>
          <tr
            v-for="t in summary.by_type"
            :key="t.round_type"
          >
            <td>{{ t.round_type.toLowerCase().replace(/_/g, ' ') }}</td>
            <td>{{ t.rounds_60d }}/{{ t.required_60d }}</td>
            <td>{{ t.non_self_60d }}</td>
            <td>{{ t.latest ? `${t.latest.score} (${t.latest.date})` : '—' }}</td>
            <td>{{ t.trend.map((p) => p.score).join(' → ') || '—' }}</td>
            <td>{{ t.g6_failing.length ? `✗ ${t.g6_failing.join('; ')}` : '✓' }}</td>
          </tr>
        </tbody>
      </table>
      <h2>Repeated weaknesses</h2>
      <p v-if="!flagged.length">
        None flagged in two or more rounds.
      </p>
      <ul v-else>
        <li
          v-for="[skill, n] in flagged"
          :key="skill"
        >
          {{ skill }} — flagged in {{ n }} rounds
        </li>
      </ul>
      <h2>Final simulations · G9 {{ summary.g9_passed ? '✓' : `✗ ${summary.g9_failing.join('; ')}` }}</h2>
      <ul data-testid="finals">
        <li
          v-for="f in summary.final_simulations"
          :key="f.mock_id"
        >
          {{ f.date }} ({{ f.source.toLowerCase() }}): {{ !f.valid ? 'not valid — ' + f.failure : f.passed ? '✓ pass' : `✗ ${f.failure}` }}
        </li>
      </ul>
      <p v-if="!summary.final_simulations.length">
        None yet. {{ summary.simulation_eligible ? 'Unlocked: the mentor schedules one on a day with ≥ 160 min.' : 'Unlocked when gates G0–G8 pass.' }}
      </p>
    </template>
  </section>
</template>

<style scoped>
.card { border: 1px solid #d8d8de; border-radius: 8px; padding: 0.75rem 1rem; background: #fff; display: flex; flex-direction: column; gap: 0.5rem; }
.row { display: flex; gap: 0.75rem; flex-wrap: wrap; align-items: end; }
label { display: flex; flex-direction: column; font-size: 0.85rem; }
label.inline { flex-direction: row; align-items: center; gap: 0.3rem; }
input[type='number'] { width: 5rem; }
.round { border: 1px solid #eee; border-radius: 6px; padding: 0.5rem; }
table { border-collapse: collapse; font-size: 0.9rem; }
th, td { text-align: left; padding: 0.25rem 0.5rem; border-bottom: 1px solid #eee; }
.secondary { background: none; border: 1px solid #888; }
.link { background: none; border: none; color: #2a55b0; text-decoration: underline; cursor: pointer; padding: 0; }
.errors { color: #a11; }
.note { background: #fff7e0; padding: 0.3rem 0.6rem; border-radius: 6px; }
</style>

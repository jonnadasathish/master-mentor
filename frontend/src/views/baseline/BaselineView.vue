<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../../api'
import { ApiError } from '../../api/client'
import type { Baseline, BatteryItem, Familiarity, SkillDelta } from '../../api/types'
import AssessmentForm from '../../components/AssessmentForm.vue'
import SkillDeltas from '../../components/SkillDeltas.vue'
import { buildSweepPayload } from '../../practice/assessment'
import { newRequestId } from '../../practice/payload'
import { useErrorStore } from '../../stores/errors'

interface SkillOption { key: string; name: string; required?: boolean | null; skill?: string }

const FAMILIARITY: Familiarity[] = ['NONE', 'SOME', 'SOLID']
const baseline = ref<Baseline | null>(null)
const requiredSkills = ref<SkillOption[]>([])
const answers = reactive<Record<string, Familiarity | null>>({})
const sweepDeltas = ref<SkillDelta[] | null>(null)
const sweepError = ref('')
const openItem = ref<string | null>(null)
const itemSkills = ref<SkillOption[]>([])
const errorStore = useErrorStore()

async function load(): Promise<void> {
  try {
    baseline.value = (await api.get<Baseline>('/baseline')).data
  } catch (caught) {
    errorStore.report(caught, 'baseline')
  }
}

async function loadRequired(): Promise<void> {
  try {
    const targets = (await api.get<{ skill: string }[]>('/catalog/role-profile/targets', { required: true })).data
    const names = new Map((await api.get<SkillOption[]>('/catalog/skills')).data.map((s) => [s.key, s.name]))
    requiredSkills.value = targets.map((t) => ({ key: t.skill, name: names.get(t.skill) ?? t.skill }))
    for (const s of requiredSkills.value) answers[s.key] = null
  } catch (caught) {
    errorStore.report(caught, 'baseline')
  }
}

async function submitSweep(): Promise<void> {
  sweepError.value = ''
  const payload = buildSweepPayload(answers, newRequestId())
  if (!payload.entries.length) {
    sweepError.value = 'Answer at least one skill.'
    return
  }
  try {
    const envelope = await api.post('/assessments/self-assessment-sweep', payload)
    sweepDeltas.value = envelope.effects?.skill_deltas ?? []
    await load()
  } catch (caught) {
    sweepError.value = caught instanceof ApiError ? caught.message : String(caught)
  }
}

async function openAssessment(item: BatteryItem): Promise<void> {
  openItem.value = item.key
  itemSkills.value = []
  try {
    const groups = await Promise.all(item.covers.map((g) => api.get<SkillOption[]>(`/catalog/groups/${g}/skills`)))
    itemSkills.value = groups.flatMap((g) => g.data.map((s) => ({ key: s.key, name: s.name })))
  } catch (caught) {
    errorStore.report(caught, 'baseline')
  }
}

onMounted(async () => {
  await load()
  await loadRequired()
})
</script>

<template>
  <section v-if="baseline">
    <h1>Baseline battery</h1>
    <p
      data-testid="calibration"
      :class="{ calibrating: baseline.calibration_mode }"
    >
      <template v-if="baseline.calibration_mode">
        Calibration: {{ baseline.assessed_required }}/{{ baseline.required }} required skills measured
        ({{ baseline.assessed_pct }}%), battery {{ baseline.battery_done }}/{{ baseline.battery_total }}.
        No readiness or feasibility verdicts until calibration is complete.
      </template>
      <template v-else>
        Calibration complete: {{ baseline.assessed_pct }}% of required skills measured.
      </template>
    </p>
    <ol class="battery">
      <li
        v-for="item in baseline.items"
        :key="item.key"
        :data-testid="`battery-${item.key}`"
        :class="{ done: item.complete, next: item.key === baseline.next_item }"
      >
        <strong>{{ item.key }}</strong> {{ item.name }} · {{ item.minutes }} min
        <span v-if="item.complete">✓ done</span>
        <template v-else-if="item.observation_kind === 'ATTEMPT'">
          → <RouterLink :to="{ name: 'problems', query: { battery: item.key, difficulty: 'MEDIUM' } }">
            pick unseen problems
          </RouterLink>
        </template>
        <template v-else-if="item.observation_kind !== 'SELF_ASSESSMENT'">
          → <button
            type="button"
            class="link"
            :data-testid="`open-${item.key}`"
            @click="openAssessment(item)"
          >
            log result
          </button>
        </template>
        <!-- Outside the status branches: completing the item must not unmount the form and its deltas. -->
        <AssessmentForm
          v-if="openItem === item.key && itemSkills.length"
          :client="api"
          :kind="item.observation_kind"
          :skills="itemSkills"
          :source-key="`battery:${item.key}`"
          :battery-item-key="item.key"
          @recorded="load"
        />
      </li>
    </ol>

    <h2>Familiarity sweep (M0-B01)</h2>
    <p>
      For each required skill: <em>NONE</em> = never studied (counts as measured at 0),
      <em>SOME</em>/<em>SOLID</em> = only routes the mentor; it never raises a score.
    </p>
    <form
      data-testid="sweep-form"
      @submit.prevent="submitSweep"
    >
      <table class="sweep">
        <tbody>
          <tr
            v-for="s in requiredSkills"
            :key="s.key"
          >
            <td>{{ s.name }} <small>{{ s.key }}</small></td>
            <td
              v-for="f in FAMILIARITY"
              :key="f"
            >
              <label><input
                v-model="answers[s.key]"
                type="radio"
                :name="`fam-${s.key}`"
                :value="f"
                :data-testid="`fam-${s.key}-${f}`"
              > {{ f.toLowerCase() }}</label>
            </td>
          </tr>
        </tbody>
      </table>
      <p
        v-if="sweepError"
        role="alert"
        class="errors"
      >
        {{ sweepError }}
      </p>
      <button
        type="submit"
        data-testid="submit-sweep"
      >
        Save familiarity sweep
      </button>
    </form>
    <SkillDeltas
      v-if="sweepDeltas"
      :deltas="sweepDeltas"
    />
  </section>
</template>

<style scoped>
.calibrating { background: #fff7e0; padding: 0.4rem 0.6rem; border-radius: 6px; }
.battery li { margin: 0.4rem 0; }
.battery li.done { color: #176317; }
.battery li.next { font-weight: 600; }
.sweep td { padding: 0.15rem 0.5rem; font-size: 0.85rem; }
.sweep small { color: #777; }
.link { background: none; border: none; color: #2a55b0; text-decoration: underline; cursor: pointer; padding: 0; }
.errors { color: #a11; }
</style>

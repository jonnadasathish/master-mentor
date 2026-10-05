<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '../api'
import { ApiError } from '../api/client'
import type { Baseline, BatteryItem, Familiarity, SkillDelta } from '../api/types'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import Icon from '../components/common/Icon.vue'
import PageHeader from '../components/common/PageHeader.vue'
import ProgressBar from '../components/common/ProgressBar.vue'
import SectionHeading from '../components/common/SectionHeading.vue'
import Skeleton from '../components/common/Skeleton.vue'
import StatusPill from '../components/common/StatusPill.vue'
import SkillDeltas from '../components/missions/SkillDeltas.vue'
import AssessmentForm from '../components/practice/AssessmentForm.vue'
import { buildSweepPayload } from '../practice/assessment'
import { newRequestId } from '../practice/payload'
import { formatMinutes } from '../presentation/format'
import { COMPONENT_LABEL } from '../presentation/language'
import { refreshDerivedData } from '../stores/data'

interface SkillOption { key: string; name: string; component: string }

const FAMILIARITY: { value: Familiarity; label: string }[] = [
  { value: 'NONE', label: 'New to me' }, { value: 'SOME', label: 'Some' }, { value: 'SOLID', label: 'Solid' },
]
const route = useRoute()
const baseline = ref<Baseline | null>(null)
const failure = ref<unknown>(null)
const requiredSkills = ref<SkillOption[]>([])
const answers = reactive<Record<string, Familiarity | null>>({})
const sweepDeltas = ref<SkillDelta[] | null>(null)
const sweepError = ref('')
const openItem = ref<string | null>(typeof route.query.item === 'string' ? route.query.item : null)
const itemSkills = ref<SkillOption[]>([])
const openGroups = ref<Set<string>>(new Set())

const groups = computed(() => {
  const by = new Map<string, SkillOption[]>()
  for (const s of requiredSkills.value) by.set(s.component, [...(by.get(s.component) ?? []), s])
  return [...by.entries()].map(([component, skills]) => ({
    component,
    label: COMPONENT_LABEL[component] ?? component,
    skills,
    answered: skills.filter((s) => answers[s.key]).length,
  }))
})
const answeredTotal = computed(() => Object.values(answers).filter(Boolean).length)

function parts(item: BatteryItem): { title: string; task: string } {
  const [head, ...rest] = item.name.split(':')
  return { title: head!.trim(), task: rest.join(':').trim() }
}

async function load(): Promise<void> {
  failure.value = null
  try {
    baseline.value = (await api.get<Baseline>('/baseline')).data
  } catch (caught) {
    failure.value = caught
  }
}

async function loadRequired(): Promise<void> {
  try {
    const targets = (await api.get<{ skill: string }[]>('/catalog/role-profile/targets', { required: true })).data
    const info = new Map((await api.get<SkillOption[]>('/catalog/skills')).data.map((s) => [s.key, s]))
    requiredSkills.value = targets.map((t) => ({
      key: t.skill, name: info.get(t.skill)?.name ?? t.skill, component: info.get(t.skill)?.component ?? 'other',
    }))
    for (const s of requiredSkills.value) answers[s.key] = null
  } catch (caught) {
    failure.value = caught
  }
}

function fillGroup(skills: SkillOption[], value: Familiarity): void {
  for (const s of skills) answers[s.key] = value
}
function toggleGroup(component: string): void {
  const next = new Set(openGroups.value)
  if (next.has(component)) next.delete(component)
  else next.add(component)
  openGroups.value = next
}

async function submitSweep(): Promise<void> {
  sweepError.value = ''
  const payload = buildSweepPayload(answers, newRequestId())
  if (!payload.entries.length) {
    sweepError.value = 'Answer at least one skill first.'
    return
  }
  try {
    const envelope = await api.post('/assessments/self-assessment-sweep', payload)
    sweepDeltas.value = envelope.effects?.skill_deltas ?? []
    await load()
    await refreshDerivedData()
  } catch (caught) {
    sweepError.value = caught instanceof ApiError ? caught.message : String(caught)
  }
}

async function openAssessment(item: BatteryItem): Promise<void> {
  openItem.value = openItem.value === item.key ? null : item.key
  if (!openItem.value) return
  itemSkills.value = []
  try {
    const found = await Promise.all(item.covers.map((g) => api.get<SkillOption[]>(`/catalog/groups/${g}/skills`)))
    itemSkills.value = found.flatMap((g) => g.data.map((s) => ({ key: s.key, name: s.name, component: s.component })))
  } catch (caught) {
    failure.value = caught
  }
}

async function recorded(): Promise<void> {
  await load()
  await refreshDerivedData()
}

onMounted(async () => {
  await load()
  await loadRequired()
  const wanted = baseline.value?.items.find((i) => i.key === openItem.value)
  if (wanted && !wanted.complete && wanted.observation_kind !== 'ATTEMPT' && wanted.observation_kind !== 'SELF_ASSESSMENT') {
    openItem.value = null
    await openAssessment(wanted)
  }
})
</script>

<template>
  <div class="page page-narrow">
    <PageHeader
      eyebrow="Calibration"
      title="Baseline assessments and self-rating"
      description="Log a result for a baseline assessment, or rate how familiar you are with each skill."
    />

    <Skeleton
      v-if="!baseline && !failure"
      height="16rem"
      radius="var(--r-lg)"
    />
    <ErrorState
      v-else-if="!baseline"
      :error="failure"
      @retry="load"
    />

    <template v-else>
      <section
        class="progress card"
        data-testid="calibration"
      >
        <template v-if="baseline.calibration_mode">
          <p class="lead">
            Calibration in progress
          </p>
          <p class="muted">
            Readiness and feasibility stay quiet until your baseline is complete.
          </p>
        </template>
        <p
          v-else
          class="lead done"
        >
          <Icon
            name="check-circle"
            :size="18"
          /> Your baseline is complete: {{ baseline.assessed_pct }}% of the skills you need are measured.
        </p>
        <div class="bars">
          <div>
            <p class="line">
              <span>Assessments</span><strong class="tabular">{{ baseline.battery_done }} / {{ baseline.battery_total }}</strong>
            </p>
            <ProgressBar
              :value="baseline.battery_done"
              :max="baseline.battery_total"
              label="Assessments done"
              tone="calibration"
              size="lg"
            />
          </div>
          <div>
            <p class="line">
              <span>Skills measured</span><strong class="tabular">{{ baseline.assessed_required }} / {{ baseline.required }}</strong>
            </p>
            <ProgressBar
              :value="baseline.assessed_required"
              :max="baseline.required"
              label="Skills measured"
              tone="calibration"
              size="lg"
            />
          </div>
        </div>
      </section>

      <section>
        <SectionHeading title="Assessments" />
        <ol class="battery">
          <li
            v-for="item in baseline.items"
            :key="item.key"
            class="item"
            :class="{ done: item.complete, next: item.key === baseline.next_item }"
            :data-testid="`battery-${item.key}`"
          >
            <div class="top">
              <span
                class="mark"
                aria-hidden="true"
              ><Icon
                :name="item.complete ? 'check' : 'circle'"
                :size="item.complete ? 14 : 10"
              /></span>
              <div class="titles">
                <h3>{{ parts(item).title }}</h3>
                <p
                  v-if="parts(item).task"
                  class="task muted"
                >
                  {{ parts(item).task }}
                </p>
              </div>
              <span class="mins muted small">{{ formatMinutes(item.minutes) }}</span>
              <StatusPill
                v-if="item.complete"
                state="completed"
              />
              <StatusPill
                v-else-if="item.key === baseline.next_item"
                state="calibration"
                label="Up next"
              />
            </div>
            <div
              v-if="!item.complete"
              class="actions"
            >
              <RouterLink
                v-if="item.observation_kind === 'ATTEMPT'"
                :to="{ name: 'problems', query: { battery: item.key, difficulty: 'MEDIUM' } }"
                class="btn btn-sm"
              >
                Pick unseen problems
              </RouterLink>
              <a
                v-else-if="item.observation_kind === 'SELF_ASSESSMENT'"
                href="#sweep"
                class="btn btn-sm"
              >Go to the self-rating</a>
              <button
                v-else
                type="button"
                class="btn btn-sm"
                :data-testid="`open-${item.key}`"
                @click="openAssessment(item)"
              >
                {{ openItem === item.key ? 'Close' : 'Log your result' }}
              </button>
            </div>
            <!-- Outside the status branches: completing the item must not unmount the form and its deltas. -->
            <AssessmentForm
              v-if="openItem === item.key && itemSkills.length"
              :client="api"
              :kind="item.observation_kind"
              :skills="itemSkills"
              :source-key="`battery:${item.key}`"
              :battery-item-key="item.key"
              @recorded="recorded"
            />
          </li>
        </ol>
      </section>

      <section
        id="sweep"
        class="sweep"
      >
        <SectionHeading title="Self-rating: how familiar are you?" />
        <p class="muted">
          For each required skill: <strong>New to me</strong> counts as measured at 0. <strong>Some</strong> and <strong>Solid</strong> only
          help the mentor choose what to test first. They never raise a score.
        </p>
        <form
          data-testid="sweep-form"
          class="stack"
          @submit.prevent="submitSweep"
        >
          <div
            v-for="g in groups"
            :key="g.component"
            class="group card-quiet"
          >
            <button
              type="button"
              class="group-head"
              :aria-expanded="openGroups.has(g.component)"
              @click="toggleGroup(g.component)"
            >
              <span class="gname">{{ g.label }}</span>
              <span class="muted small tabular">{{ g.answered }} of {{ g.skills.length }} answered</span>
              <Icon
                :name="openGroups.has(g.component) ? 'chevron-down' : 'chevron-right'"
                :size="16"
              />
            </button>
            <div v-if="openGroups.has(g.component)">
              <p class="bulk">
                Everything here is
                <button
                  v-for="f in FAMILIARITY"
                  :key="f.value"
                  type="button"
                  class="chip"
                  @click="fillGroup(g.skills, f.value)"
                >
                  {{ f.label.toLowerCase() }}
                </button>
              </p>
              <ul class="skills">
                <li
                  v-for="s in g.skills"
                  :key="s.key"
                >
                  <span class="sname">{{ s.name }}</span>
                  <span class="opts">
                    <label
                      v-for="f in FAMILIARITY"
                      :key="f.value"
                      class="opt"
                      :class="{ chosen: answers[s.key] === f.value }"
                    >
                      <input
                        v-model="answers[s.key]"
                        type="radio"
                        :name="`fam-${s.key}`"
                        :value="f.value"
                        :data-testid="`fam-${s.key}-${f.value}`"
                      >
                      {{ f.label }}
                    </label>
                  </span>
                </li>
              </ul>
            </div>
          </div>
          <p
            v-if="sweepError"
            role="alert"
            class="error"
          >
            {{ sweepError }}
          </p>
          <div class="row">
            <button
              type="submit"
              class="btn btn-primary btn-lg"
              data-testid="submit-sweep"
            >
              Save my self-rating
            </button>
            <span class="muted small">{{ answeredTotal }} skills answered</span>
          </div>
        </form>
        <SkillDeltas
          v-if="sweepDeltas"
          :deltas="sweepDeltas"
        />
      </section>
      <EmptyState
        v-if="!requiredSkills.length && !failure"
        icon="list"
        title="No skills to rate yet."
        body="The skill catalog isn't loaded."
      />
    </template>
  </div>
</template>

<style scoped>
.progress { display: grid; gap: var(--s-4); background: linear-gradient(135deg, var(--calibration-bg), var(--surface) 70%); border-color: var(--calibration-bd); }
.lead { font-size: var(--fs-lg); font-weight: 700; letter-spacing: -0.015em; }
.lead.done { display: flex; align-items: center; gap: var(--s-2); color: var(--healthy-fg); font-size: var(--fs-md); }
.bars { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-5); }
.line { display: flex; justify-content: space-between; margin-bottom: var(--s-2); font-size: var(--fs-sm); color: var(--text-2); }
.line strong { color: var(--text); font-size: var(--fs-md); }
.battery { display: grid; gap: var(--s-3); }
.item { display: grid; gap: var(--s-3); padding: var(--s-4) var(--s-5); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); }
.item.next { border-color: var(--calibration-fg); box-shadow: 0 0 0 3px var(--calibration-bg); }
.item.done { background: var(--surface-2); }
.top { display: flex; align-items: flex-start; gap: var(--s-3); }
.mark { display: grid; place-items: center; flex: none; width: 1.5rem; height: 1.5rem; border-radius: 50%; border: 2px solid var(--border-strong); color: var(--text-3); margin-top: 0.1rem; }
.item.done .mark { background: var(--healthy-fg); border-color: var(--healthy-fg); color: #fff; }
.titles { flex: 1; min-width: 0; display: grid; gap: 2px; }
h3 { font-size: var(--fs-md); }
.task { font-size: var(--fs-sm); }
.mins { white-space: nowrap; }
.small { font-size: var(--fs-sm); }
.actions { margin-left: calc(1.5rem + var(--s-3)); }
.sweep { display: grid; gap: var(--s-3); scroll-margin-top: var(--s-5); }
.group { padding: 0; overflow: hidden; }
.group-head { display: flex; align-items: center; gap: var(--s-3); width: 100%; padding: var(--s-3) var(--s-4); background: none; border: 0; font: inherit; cursor: pointer; text-align: left; }
.group-head:hover { background: var(--surface-2); }
.gname { flex: 1; font-weight: 650; }
.bulk { padding: var(--s-2) var(--s-4); font-size: var(--fs-sm); color: var(--text-2); border-top: 1px solid var(--border); display: flex; flex-wrap: wrap; gap: var(--s-2); align-items: center; }
.chip { border: 1px solid var(--border-strong); background: var(--surface); border-radius: 999px; padding: 0.15rem 0.7rem; font: inherit; font-size: var(--fs-sm); cursor: pointer; }
.chip:hover { background: var(--accent-soft); }
.skills { display: grid; }
.skills li { display: flex; align-items: center; justify-content: space-between; gap: var(--s-3); flex-wrap: wrap; padding: var(--s-2) var(--s-4); border-top: 1px solid var(--border); }
.sname { flex: 1 1 14rem; font-size: var(--fs-sm); }
.opts { display: flex; gap: var(--s-1); }
.opt { position: relative; display: inline-flex; padding: 0.2rem 0.7rem; border: 1px solid var(--border-strong); border-radius: 999px; font-size: var(--fs-sm); cursor: pointer; background: var(--surface); }
.opt input { position: absolute; opacity: 0; pointer-events: none; }
.opt.chosen { background: var(--accent-soft); border-color: var(--accent); color: var(--accent-text); font-weight: 650; }
.opt:focus-within { outline: 2px solid var(--accent); outline-offset: 2px; }
.error { color: var(--critical-fg); }
@media (max-width: 767px) { .bars { grid-template-columns: 1fr; } .actions { margin-left: 0; } .mins { display: none; } }
</style>

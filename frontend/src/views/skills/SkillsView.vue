<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../../api'
import type { Meta, Readiness, RoadmapView, SkillWithState } from '../../api/types'
import StatusBadge from '../../components/StatusBadge.vue'
import { useErrorStore } from '../../stores/errors'

const LABELS = ['UNASSESSED', 'WEAK', 'DEVELOPING', 'WORKING', 'STRONG', 'INTERVIEW_GRADE']
const tab = ref<'skills' | 'roadmap'>('skills')
const filters = reactive({ component: '', group: '', tier: '', label: '' })
const skills = ref<SkillWithState[]>([])
const allSkills = ref<SkillWithState[]>([])
const readiness = ref<Readiness | null>(null)
const roadmap = ref<RoadmapView | null>(null)
const meta = ref<Meta>({})
const errorStore = useErrorStore()

const groups = computed(() =>
  [...new Set(allSkills.value.filter((s) => !filters.component || s.component === filters.component).map((s) => s.group))],
)
/** Blocker count per component: conditions on the component or on one of its skills (server conditions). */
function blockerCount(component: string): number {
  const r = readiness.value
  if (!r) return 0
  const skillComponent = new Map(allSkills.value.map((s) => [s.key, s.component]))
  return r.all_failing.filter((c) => c.subject === component || skillComponent.get(c.subject) === component).length
}
const ACTIONABLE = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
const topGaps = computed(() =>
  allSkills.value
    .filter((s) => s.gap && ACTIONABLE.includes(s.gap.status))
    .sort((a, b) => a.gap!.rank - b.gap!.rank)
    .slice(0, 3),
)

async function load(): Promise<void> {
  try {
    const envelope = await api.get<SkillWithState[]>('/skills', { ...filters })
    skills.value = envelope.data
    meta.value = envelope.meta
  } catch (caught) {
    errorStore.report(caught, 'skills')
  }
}

function pickComponent(key: string): void {
  filters.component = filters.component === key ? '' : key
  filters.group = ''
  void load()
}

async function openRoadmap(): Promise<void> {
  tab.value = 'roadmap'
  if (roadmap.value) return
  try {
    roadmap.value = (await api.get<RoadmapView>('/roadmap')).data
  } catch (caught) {
    errorStore.report(caught, 'skills')
  }
}

onMounted(async () => {
  try {
    allSkills.value = (await api.get<SkillWithState[]>('/skills')).data
    readiness.value = (await api.get<Readiness>('/readiness')).data
  } catch (caught) {
    errorStore.report(caught, 'skills')
  }
  await load()
})
</script>

<template>
  <section>
    <h1>Skills</h1>
    <p class="meta">
      As of {{ meta.as_of_date }} · ruleset {{ meta.ruleset_version }} · run {{ meta.run_id }} ·
      <RouterLink :to="{ name: 'baseline' }">
        Baseline battery
      </RouterLink>
    </p>
    <div
      class="tabs"
      role="tablist"
    >
      <button
        type="button"
        role="tab"
        :aria-selected="tab === 'skills'"
        data-testid="tab-skills"
        @click="tab = 'skills'"
      >
        Skills
      </button>
      <button
        type="button"
        role="tab"
        :aria-selected="tab === 'roadmap'"
        data-testid="tab-roadmap"
        @click="openRoadmap"
      >
        Roadmap
      </button>
    </div>

    <template v-if="tab === 'skills'">
      <div
        v-if="readiness"
        class="cards"
        data-testid="component-cards"
      >
        <button
          v-for="c in readiness.components"
          :key="c.key"
          type="button"
          class="card"
          :class="{ selected: filters.component === c.key, failing: !c.passes_gate }"
          :aria-pressed="filters.component === c.key"
          :data-testid="`component-${c.key}`"
          @click="pickComponent(c.key)"
        >
          <strong>{{ c.name }}</strong>
          <span class="score">{{ c.score }} <small>/ gate {{ c.gate }}</small> {{ c.passes_gate ? '✓' : '✗' }}</span>
          <small>assessed {{ c.assessed_pct }}% · medium+ {{ c.medium_conf_pct }}%</small>
          <small v-if="blockerCount(c.key)">⚠ {{ blockerCount(c.key) }} failing conditions</small>
        </button>
      </div>

      <section
        v-if="topGaps.length"
        class="top"
        data-testid="top-gaps"
      >
        <h2>Top gaps</h2>
        <ol>
          <li
            v-for="s in topGaps"
            :key="s.key"
          >
            <RouterLink :to="{ name: 'skill', params: { key: s.key } }">
              {{ s.name }}
            </RouterLink>
            — {{ s.gap!.status.toLowerCase() }} {{ s.gap!.priority }}, {{ s.gap!.primary_gap_type?.toLowerCase() }}
            → {{ s.gap!.focus_stage?.toLowerCase() }}
          </li>
        </ol>
      </section>

      <form
        class="filters"
        @submit.prevent="load"
      >
        <label>Group
          <select
            v-model="filters.group"
            data-testid="group"
            @change="load"
          >
            <option value="">All</option>
            <option
              v-for="g in groups"
              :key="g"
              :value="g"
            >{{ g }}</option>
          </select>
        </label>
        <label>Tier
          <select
            v-model="filters.tier"
            @change="load"
          >
            <option value="">All</option>
            <option
              v-for="t in ['T1', 'T2', 'T3', 'T4']"
              :key="t"
              :value="t"
            >{{ t }}</option>
          </select>
        </label>
        <label>State
          <select
            v-model="filters.label"
            data-testid="label"
            @change="load"
          >
            <option value="">All</option>
            <option
              v-for="l in LABELS"
              :key="l"
              :value="l"
            >{{ l.toLowerCase().replace('_', ' ') }}</option>
          </select>
        </label>
      </form>
      <table data-testid="skills-table">
        <thead>
          <tr>
            <th>Skill</th><th>Tier</th><th>Score</th><th>Effective</th><th>Target</th>
            <th>Level</th><th>Confidence</th><th>State</th><th>Gap</th><th>Last practiced</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="s in skills"
            :key="s.key"
            :data-testid="`skill-row-${s.key}`"
          >
            <td>
              <RouterLink :to="{ name: 'skill', params: { key: s.key } }">
                {{ s.name }}
              </RouterLink>
              <small>{{ s.key }}</small>
            </td>
            <td>{{ s.tier ?? '—' }}</td>
            <td>{{ s.state.score ?? '—' }}</td>
            <td>{{ s.state.effective_score ?? '—' }}</td>
            <td>{{ s.target_score ?? '—' }}</td>
            <td>{{ s.state.level === null ? '—' : `L${s.state.level}` }}</td>
            <td>{{ s.state.confidence.toLowerCase() }}</td>
            <td>{{ s.state.declared_unknown ? 'declared unknown' : s.state.label.toLowerCase().replace('_', ' ') }}</td>
            <td>
              <template v-if="s.gap">
                <StatusBadge
                  :status="s.gap.status"
                  :priority="s.gap.status === 'NONE' ? null : s.gap.priority"
                />
                <small v-if="s.gap.primary_gap_type && s.gap.status !== 'NONE'">{{ s.gap.primary_gap_type.toLowerCase() }} → {{ s.gap.focus_stage?.toLowerCase() }}</small>
              </template>
              <template v-else>
                —
              </template>
            </td>
            <td>{{ s.state.last_practiced_on ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
    </template>

    <section
      v-else-if="roadmap"
      data-testid="roadmap"
    >
      <p>
        Baseline battery {{ roadmap.baseline.done }}/{{ roadmap.baseline.total }}<template v-if="roadmap.baseline.next_item">
          · next {{ roadmap.baseline.next_item }}
        </template>
      </p>
      <div
        v-for="t in roadmap.tracks"
        :key="t.track"
        class="track"
      >
        <h2>{{ t.track.replace('_', ' ') }}</h2>
        <ol class="milestones">
          <li
            v-for="m in t.milestones"
            :key="m.key"
            :class="{ current: m.current, complete: m.complete }"
            :data-testid="`milestone-${m.key}`"
          >
            <strong>{{ m.complete ? '✓' : m.current ? '▶' : '·' }} {{ m.key }} {{ m.name }}</strong>
            <span>{{ m.required_done }}/{{ m.required_total }} required skills at L3+</span>
            <span
              v-for="x in m.extra_exit"
              :key="x.text"
              class="extra"
            >{{ x.met ? '✓' : '✗' }} {{ x.text }}</span>
            <span v-if="m.current"> (current)</span>
          </li>
        </ol>
      </div>
    </section>
  </section>
</template>

<style scoped>
.meta { color: #555; font-size: 0.85rem; }
.tabs { display: flex; gap: 0.4rem; margin: 0.5rem 0; }
.tabs button { border: 1px solid #bbb; border-radius: 6px; background: #f6f6f8; padding: 0.25rem 0.8rem; }
.tabs button[aria-selected='true'] { background: #e3ecff; border-color: #3366cc; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 0.6rem; margin: 0.6rem 0; }
.card { display: flex; flex-direction: column; align-items: flex-start; gap: 0.2rem; text-align: left; border: 1px solid #d8d8de; border-radius: 8px; background: #fff; padding: 0.5rem 0.7rem; cursor: pointer; }
.card.failing { border-left: 4px solid #d33; }
.card.selected { background: #e3ecff; }
.score { font-size: 1.2rem; }
.filters { display: flex; gap: 1rem; margin: 0.5rem 0 1rem; flex-wrap: wrap; }
.filters label { display: flex; flex-direction: column; font-size: 0.85rem; }
table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
th, td { text-align: left; padding: 0.3rem 0.5rem; border-bottom: 1px solid #eee; }
td small { display: block; color: #777; }
.milestones li { margin: 0.3rem 0; display: flex; gap: 0.6rem; flex-wrap: wrap; }
.milestones li.current { font-weight: 600; }
.milestones li.complete { color: #176317; }
.extra { font-size: 0.8rem; color: #555; }
@media (max-width: 640px) { table { display: block; overflow-x: auto; } }
</style>

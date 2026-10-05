<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../../api'
import type { Readiness, ReadinessPoint } from '../../api/types'
import WeeklyReviewPanel from '../../components/WeeklyReviewPanel.vue'
import { useErrorStore } from '../../stores/errors'

const GATE_NAMES: Record<string, string> = {
  G0: 'Measured', G1: 'Foundation exit', G2: 'Component thresholds', G3: 'Coverage', G4: 'Critical skills',
  G5: 'No critical gaps', G6: 'Mocks', G7: 'Revision health', G8: 'Recency', G9: 'Final simulation',
}
const readiness = ref<Readiness | null>(null)
const history = ref<ReadinessPoint[]>([])
const errorStore = useErrorStore()

/** Headline per READINESS_MODEL §9: state, blocker count and the limiting component. Never "% ready". */
const headline = computed(() => {
  const r = readiness.value
  if (!r) return ''
  const limiting = r.components.find((c) => c.key === r.limiting_component)
  const lim = limiting ? ` · limiting: ${limiting.name} ${limiting.score}/${limiting.gate}` : ''
  return `${r.state.replace('_', ' ')} — ${r.blockers.length} blocker${r.blockers.length === 1 ? '' : 's'}${lim}`
})

onMounted(async () => {
  try {
    readiness.value = (await api.get<Readiness>('/readiness')).data
    history.value = (await api.get<ReadinessPoint[]>('/readiness/history')).data
  } catch (caught) {
    errorStore.report(caught, 'progress')
  }
})
</script>

<template>
  <section v-if="readiness">
    <h1>Progress</h1>
    <p
      class="headline"
      data-testid="readiness-headline"
    >
      {{ headline }}
    </p>
    <p class="meta">
      Internal benchmark states, not a hiring prediction. Weighted score {{ readiness.weighted_score }} is shown for trend only;
      the state comes from gates. As of {{ readiness.as_of_date }} (run {{ readiness.run_id }}).
      <span v-if="readiness.lapsed"> · <strong>lapsed</strong></span>
      <span v-if="readiness.simulation_eligible"> · final simulations unlocked</span>
    </p>

    <h2>Blockers for the next state</h2>
    <ol data-testid="blockers">
      <li
        v-for="b in readiness.blockers"
        :key="`${b.gate}-${b.subject}`"
      >
        <strong>{{ b.gate }}</strong> {{ b.message }}
        <template v-if="b.skills.length && b.kind === 'component'">
          — worst: <RouterLink
            v-for="s in b.skills"
            :key="s"
            :to="{ name: 'skill', params: { key: s } }"
            class="skill"
          >
            {{ s }}
          </RouterLink>
        </template>
      </li>
    </ol>

    <h2>Components</h2>
    <table data-testid="components">
      <thead>
        <tr><th>Component</th><th>Score</th><th>Gate</th><th>Stretch</th><th>Assessed</th><th>Medium+ confidence</th></tr>
      </thead>
      <tbody>
        <tr
          v-for="c in readiness.components"
          :key="c.key"
          :class="{ failing: !c.passes_gate }"
        >
          <td>{{ c.name }}</td><td>{{ c.score }}</td><td>{{ c.gate }}</td><td>{{ c.stretch }}</td>
          <td>{{ c.assessed_pct }}%</td><td>{{ c.medium_conf_pct }}%</td>
        </tr>
      </tbody>
    </table>

    <h2>Gates</h2>
    <ul
      class="gates"
      data-testid="gates"
    >
      <li
        v-for="g in readiness.gates"
        :key="g.gate"
        :class="{ passed: g.passed }"
      >
        {{ g.passed ? '✓' : '✗' }} {{ g.gate }} {{ GATE_NAMES[g.gate] }}<template v-if="!g.passed">
          ({{ g.failing }})
        </template>
      </li>
    </ul>

    <h2>Weekly review</h2>
    <WeeklyReviewPanel />

    <h2>History <small>(weighted score is display only)</small></h2>
    <table
      v-if="history.length"
      data-testid="history"
    >
      <thead>
        <tr><th>Date</th><th>State</th><th>Weighted</th><th>Blockers</th><th>Limiting</th></tr>
      </thead>
      <tbody>
        <tr
          v-for="h in history"
          :key="h.date"
        >
          <td>{{ h.date }}</td><td>{{ h.state }}</td><td>{{ h.weighted_score }}</td><td>{{ h.blockers }}</td><td>{{ h.limiting_component ?? '—' }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.headline { font-size: 1.2rem; font-weight: 600; }
.meta { color: #555; font-size: 0.85rem; }
table { border-collapse: collapse; font-size: 0.9rem; }
th, td { text-align: left; padding: 0.25rem 0.6rem; border-bottom: 1px solid #eee; }
tr.failing td { color: #a11; }
.gates { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; }
.gates li { color: #a11; }
.gates li.passed { color: #176317; }
.skill { margin-left: 0.4rem; display: inline-block; }
li { overflow-wrap: anywhere; }
</style>

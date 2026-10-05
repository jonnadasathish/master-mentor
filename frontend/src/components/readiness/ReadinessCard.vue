<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { Readiness, ReadinessPoint, Today } from '../../api/types'
import { COMPONENT_LABEL, READINESS_LABEL, READINESS_SUMMARY } from '../../presentation/language'
import Icon from '../common/Icon.vue'
import ProgressBar from '../common/ProgressBar.vue'
import StatusPill from '../common/StatusPill.vue'
import Sparkline from './Sparkline.vue'

/**
 * Where you stand. All numbers and the state are the server's. Not measured yet -> a calibration card, never a
 * diagnostic table; once measured -> the score, the state, a component breakdown and the trend when there is history.
 */
const props = defineProps<{
  summary: Today['readiness']
  calibration: Today['calibration']
  readiness: Readiness | null
  history: ReadinessPoint[]
}>()

const measured = computed(() => props.summary.state !== 'NOT_MEASURED')
const label = computed(() => READINESS_LABEL[props.summary.state] ?? props.summary.state)
const components = computed(() => props.readiness?.components ?? [])
const limiting = computed(() => (props.summary.limiting_component ? COMPONENT_LABEL[props.summary.limiting_component] ?? null : null))
const points = computed(() => props.history.map((p) => p.weighted_score))
const trend = computed(() => {
  if (props.history.length < 2) return null
  const first = props.history[0]!
  const last = props.history[props.history.length - 1]!
  const delta = last.weighted_score - first.weighted_score
  return { delta, since: first.date, direction: delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat' } as const
})
</script>

<template>
  <section
    class="readiness card"
    aria-labelledby="readiness-title"
    data-testid="readiness-card"
  >
    <h2
      id="readiness-title"
      class="eyebrow"
    >
      Readiness
    </h2>

    <template v-if="!measured">
      <p
        class="big muted-big"
        data-testid="readiness-state"
      >
        Not measured yet
      </p>
      <template v-if="calibration.active">
        <p class="calm">
          <StatusPill
            state="calibration"
            label="Calibrating"
          />
        </p>
        <p class="muted">
          We're calibrating your baseline. This is expected: your readiness appears once enough is measured.
        </p>
        <div
          class="measured"
          data-testid="readiness-progress"
        >
          <p class="tabular">
            <strong>{{ calibration.assessed }} / {{ calibration.required }}</strong> skills measured
          </p>
          <ProgressBar
            :value="calibration.assessed"
            :max="calibration.required"
            label="Skills measured"
            tone="calibration"
          />
        </div>
      </template>
      <template v-else>
        <p class="muted">
          Your starting profile is built. A few areas still need a first assessment before readiness can be judged.
        </p>
        <ul
          v-if="summary.blockers.length"
          class="needs"
          data-testid="readiness-needs"
        >
          <li
            v-for="b in summary.blockers"
            :key="b.message"
          >
            <Icon
              name="crosshair"
              :size="14"
            /> {{ b.message }}
          </li>
        </ul>
      </template>
    </template>

    <template v-else>
      <div class="score-row">
        <p
          class="big tabular"
          data-testid="readiness-score"
        >
          {{ summary.weighted_score }}<span class="of"> / 100</span>
        </p>
        <StatusPill
          :state="summary.state === 'INTERVIEW_READY' || summary.state === 'STRONG' ? 'ready' : 'due'"
          :label="label"
        />
      </div>
      <p
        class="muted"
        data-testid="readiness-state"
      >
        {{ READINESS_SUMMARY[summary.state] }}
      </p>
      <p
        v-if="limiting"
        class="limiter"
      >
        <Icon
          name="target"
          :size="14"
        /> Holding you back most: <strong>{{ limiting }}</strong>
      </p>

      <ul
        v-if="components.length"
        class="components"
        data-testid="readiness-components"
      >
        <li
          v-for="c in components"
          :key="c.key"
        >
          <span class="name">{{ COMPONENT_LABEL[c.key] ?? c.name }}</span>
          <ProgressBar
            :value="c.score"
            :max="100"
            :label="`${COMPONENT_LABEL[c.key] ?? c.name} score`"
            size="sm"
            :tone="c.passes_gate ? 'healthy' : 'accent'"
            :marker="c.gate"
          />
          <span class="num tabular">{{ c.score }}</span>
        </li>
      </ul>
      <p
        v-if="components.length"
        class="legend muted"
      >
        The tick on each bar marks the level you're aiming for.
      </p>

      <div
        v-if="trend"
        class="trend"
        data-testid="readiness-trend"
      >
        <Sparkline
          :points="points"
          label="Readiness score over time"
        />
        <p class="muted">
          <Icon
            :name="trend.direction === 'up' ? 'trending' : 'minus-circle'"
            :size="14"
          />
          <template v-if="trend.direction === 'up'">
            Up {{ trend.delta }} since {{ trend.since }}
          </template>
          <template v-else-if="trend.direction === 'down'">
            Down {{ -trend.delta }} since {{ trend.since }}
          </template>
          <template v-else>
            Steady since {{ trend.since }}
          </template>
        </p>
      </div>
    </template>

    <RouterLink
      :to="{ name: 'progress' }"
      class="more"
    >
      See your progress
      <Icon
        name="arrow-right"
        :size="14"
      />
    </RouterLink>
  </section>
</template>

<style scoped>
.readiness { display: grid; gap: var(--s-3); }
.big { font-size: var(--fs-3xl); font-weight: 700; letter-spacing: -0.03em; line-height: 1.1; }
.muted-big { font-size: var(--fs-xl); color: var(--text-2); }
.of { font-size: var(--fs-lg); font-weight: 500; color: var(--text-3); letter-spacing: 0; }
.score-row { display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap; }
.measured { display: grid; gap: var(--s-2); }
.limiter { display: flex; align-items: center; gap: var(--s-2); font-size: var(--fs-sm); color: var(--text-2); }
.components { display: grid; gap: var(--s-2); margin-top: var(--s-1); }
.components li { display: grid; grid-template-columns: 7.2rem minmax(0, 1fr) 2rem; align-items: center; gap: var(--s-3); font-size: var(--fs-sm); }
.name { color: var(--text-2); }
.num { text-align: right; font-weight: 650; }
.legend { font-size: var(--fs-xs); }
.calm { margin-top: calc(var(--s-1) * -1); }
.needs { display: grid; gap: var(--s-2); font-size: var(--fs-sm); color: var(--text-2); }
.needs li { display: flex; align-items: flex-start; gap: var(--s-2); }
.needs :deep(svg) { margin-top: 0.2rem; color: var(--calibration-fg); }
.trend { display: grid; gap: var(--s-1); padding-top: var(--s-2); border-top: 1px solid var(--border); }
.trend p { display: flex; align-items: center; gap: var(--s-1); font-size: var(--fs-sm); }
.more { display: inline-flex; align-items: center; gap: var(--s-1); font-size: var(--fs-sm); font-weight: 600; margin-top: var(--s-1); }
</style>

<script setup lang="ts">
import type { Baseline } from '../../api/types'
import { formatMinutes } from '../../presentation/format'
import Icon from '../common/Icon.vue'

/** What calibration is, said before it begins. Totals are the server's battery; nothing is promised beyond it. */
defineProps<{ baseline: Baseline | null }>()
</script>

<template>
  <div class="stack">
    <p class="lead">
      Calibration is a diagnostic. You'll solve and answer real tasks, we measure how you do, and the results become the
      basis of your personal roadmap.
    </p>
    <div
      class="facts"
      data-testid="ob-calibration-facts"
    >
      <div class="fact">
        <p class="big tabular">
          {{ baseline?.battery_total ?? 12 }}
        </p>
        <p class="muted">
          baseline assessments
        </p>
      </div>
      <div class="fact">
        <p class="big tabular">
          ~{{ formatMinutes(baseline?.minutes_total ?? 420) }}
        </p>
        <p class="muted">
          in total, spread across your normal schedule, not in one sitting
        </p>
      </div>
    </div>
    <ul class="points">
      <li>
        <Icon
          name="target"
          :size="18"
        /> <span><strong>Why it exists.</strong> A plan built on guesses wastes your time. Measuring first means you only study what you need.</span>
      </li>
      <li>
        <Icon
          name="list"
          :size="18"
        /> <span><strong>What we capture.</strong> Your results, timing and mistakes on each task. These become evidence.</span>
      </li>
      <li>
        <Icon
          name="check-circle"
          :size="18"
        /> <span><strong>No pass or fail.</strong> Nothing here is graded against you.</span>
      </li>
      <li>
        <Icon
          name="zap"
          :size="18"
        /> <span><strong>Honest failures are useful.</strong> A task you can't solve tells us exactly where to start.</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.lead { font-size: var(--fs-lg); color: var(--text-2); max-width: 40rem; text-wrap: pretty; }
.facts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--s-4); max-width: 34rem; }
.fact { padding: var(--s-4); background: var(--calibration-bg); border: 1px solid var(--calibration-bd); border-radius: var(--r-lg); }
.big { font-size: var(--fs-2xl); font-weight: 700; letter-spacing: -0.02em; color: var(--calibration-fg); }
.points { display: grid; gap: var(--s-3); }
.points li { display: flex; gap: var(--s-3); align-items: flex-start; }
.points :deep(svg) { margin-top: 0.2rem; color: var(--calibration-fg); flex: none; }
@media (max-width: 767px) { .facts { grid-template-columns: 1fr; } }
</style>

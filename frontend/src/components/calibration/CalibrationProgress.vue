<script setup lang="ts">
import { computed } from 'vue'
import type { Baseline } from '../../api/types'
import { formatMinutes, monthYear, plural, trimWeeks } from '../../presentation/format'
import { PHASE_LABEL } from '../../presentation/language'
import ProgressBar from '../common/ProgressBar.vue'

/** Assessments done, skills measured, time left and the timeline. Every number is the server's. */
const props = defineProps<{
  baseline: Baseline
  targetDate?: string | null
  weeksLeft?: string | null
  phase?: string | null
}>()
const remaining = computed(() => props.baseline.minutes_remaining)
const effort = computed(() => {
  const days = props.baseline.estimated_days
  return `${formatMinutes(remaining.value)} of assessments left${days ? `, roughly ${plural(days, 'day')} at your usual daily time` : ''}.`
})
</script>

<template>
  <section
    class="progress card"
    aria-labelledby="progress-title"
    data-testid="calibration-progress"
  >
    <h2
      id="progress-title"
      class="eyebrow"
    >
      Calibration progress
    </h2>
    <div class="bars">
      <div>
        <p class="line">
          <span>Assessments</span><strong class="tabular">{{ baseline.battery_done }} / {{ baseline.battery_total }}</strong>
        </p>
        <ProgressBar
          :value="baseline.battery_done"
          :max="baseline.battery_total"
          label="Baseline assessments completed"
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
          label="Required skills measured"
          tone="calibration"
          size="lg"
        />
      </div>
    </div>
    <p
      v-if="remaining > 0"
      class="effort"
      data-testid="calibration-effort"
    >
      About {{ effort }}
      <span class="muted">
        Your full baseline is about {{ formatMinutes(baseline.minutes_total) }} in total, but Master Mentor spreads it across
        your normal preparation time, not in one sitting.
      </span>
    </p>
    <dl
      v-if="weeksLeft || targetDate"
      class="timeline"
      data-testid="calibration-timeline"
    >
      <div v-if="targetDate">
        <dt>Interview target</dt>
        <dd>{{ monthYear(targetDate) }}</dd>
      </div>
      <div v-if="weeksLeft">
        <dt>Time remaining</dt>
        <dd>{{ plural(Number(trimWeeks(weeksLeft)), 'week') }}</dd>
      </div>
      <div v-if="phase">
        <dt>Phase</dt>
        <dd>{{ PHASE_LABEL[phase] ?? phase }}</dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.progress { display: grid; gap: var(--s-4); }
.bars { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--s-5); }
.line { display: flex; justify-content: space-between; margin-bottom: var(--s-2); font-size: var(--fs-sm); color: var(--text-2); }
.line strong { color: var(--text); font-size: var(--fs-md); }
.effort { color: var(--text); }
.effort .muted { display: block; margin-top: var(--s-1); font-size: var(--fs-sm); }
.timeline { display: flex; flex-wrap: wrap; gap: var(--s-3) var(--s-6); padding-top: var(--s-3); border-top: 1px solid var(--border); }
dt { font-size: var(--fs-xs); font-weight: 650; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-3); }
dd { font-weight: 650; }
@media (max-width: 767px) { .bars { grid-template-columns: 1fr; gap: var(--s-4); } }
</style>

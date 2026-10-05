<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { Baseline, StartingProfile } from '../../api/types'
import { formatMinutes, monthYear, plural, trimWeeks } from '../../presentation/format'
import Icon from '../common/Icon.vue'

/** After the starting profile is saved: the target and timeline, and the next step. Server values only. */
const props = defineProps<{ profile: StartingProfile; baseline: Baseline | null }>()
const target = computed(() => props.profile.target)
const summary = computed(() => {
  const days = props.baseline?.estimated_days
  const base = `${props.baseline?.battery_total ?? 12} baseline assessments · about ${formatMinutes(props.baseline?.minutes_total ?? 420)} in total, spread across your normal schedule`
  return days ? `${base} (roughly ${plural(days, 'day')} at your usual time).` : `${base}.`
})
</script>

<template>
  <div
    class="stack"
    data-testid="ob-ready"
  >
    <dl
      v-if="target"
      class="summary"
    >
      <div>
        <dt>Target</dt>
        <dd>{{ target.role.name }}</dd>
      </div>
      <div>
        <dt>Timeline</dt>
        <dd>
          <template v-if="target.weeks_left">
            {{ plural(Number(trimWeeks(target.weeks_left)), 'week') }}<template v-if="target.target_date">
              · {{ monthYear(target.target_date) }}
            </template>
          </template>
          <template v-else>
            No date set
          </template>
        </dd>
      </div>
      <div>
        <dt>Preparation</dt>
        <dd>{{ formatMinutes(target.weekly_minutes) }} a week</dd>
      </div>
    </dl>

    <section class="next">
      <p class="eyebrow">
        Next
      </p>
      <h2>Calibrate your skills</h2>
      <p class="muted">
        {{ summary }}
      </p>
      <RouterLink
        :to="{ name: 'calibrate' }"
        class="btn btn-primary btn-lg"
        data-testid="ob-start-calibration"
      >
        <Icon
          name="play"
          :size="14"
        /> Start calibration
      </RouterLink>
    </section>
  </div>
</template>

<style scoped>
.summary { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--s-4); }
.summary > div { padding: var(--s-4); background: var(--surface-2); border-radius: var(--r-md); }
dt { font-size: var(--fs-xs); font-weight: 650; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-3); }
dd { margin-top: var(--s-1); font-weight: 650; }
.next { display: grid; gap: var(--s-2); padding: var(--s-5); background: linear-gradient(135deg, var(--calibration-bg), var(--surface) 70%); border: 1px solid var(--calibration-bd); border-radius: var(--r-lg); }
.next .eyebrow { color: var(--calibration-fg); }
.next .btn { width: fit-content; margin-top: var(--s-2); }
@media (max-width: 767px) { .summary { grid-template-columns: 1fr; } .next .btn { width: 100%; } }
</style>

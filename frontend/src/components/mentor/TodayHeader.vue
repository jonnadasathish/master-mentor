<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { greetingFor, longDate, monthYear } from '../../presentation/format'

/** Greeting, the day of the plan and the current phase. Wording only; the day and phase come from the server. */
const props = defineProps<{
  name: string | null
  date: string
  day: number | null
  phase: string
  weeksLeft: string | null
  targetDate?: string | null
  hasGoal: boolean
  hour?: number
}>()
const greeting = computed(() => {
  const base = greetingFor(props.hour ?? new Date().getHours())
  return props.name ? `${base}, ${props.name}.` : `${base}.`
})
const weeks = computed(() => {
  if (!props.weeksLeft) return null
  const n = props.weeksLeft.replace(/\.0$/, '')
  const when = props.targetDate ? ` (${monthYear(props.targetDate)})` : ''
  return `${n} ${n === '1' ? 'week' : 'weeks'} to your interview${when}`
})
</script>

<template>
  <header
    class="today-header"
    data-testid="today-header"
  >
    <p class="eyebrow">
      Today · {{ longDate(date) }}
    </p>
    <h1>{{ greeting }}</h1>
    <p
      v-if="hasGoal"
      class="sub"
      data-testid="today-phase"
    >
      <template v-if="day">
        Day {{ day }} ·
      </template>{{ phase }}<template v-if="weeks">
        · {{ weeks }}
      </template>
    </p>
    <p
      v-else
      class="sub"
    >
      <RouterLink :to="{ name: 'settings' }">
        Set your target date and daily time
      </RouterLink> so Master Mentor can plan your days.
    </p>
  </header>
</template>

<style scoped>
.today-header { display: grid; gap: var(--s-1); }
h1 { font-size: var(--fs-3xl); letter-spacing: -0.03em; text-wrap: balance; }
.sub { font-size: var(--fs-md); color: var(--text-2); }
@media (max-width: 767px) { h1 { font-size: var(--fs-2xl); } }
</style>

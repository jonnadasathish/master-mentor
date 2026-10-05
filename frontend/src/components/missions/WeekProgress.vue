<script setup lang="ts">
import { computed } from 'vue'
import type { WeekContext } from '../../api/types'
import { formatMinutes, plural } from '../../presentation/format'
import { TRACK_LABEL } from '../../presentation/language'
import ProgressBar from '../common/ProgressBar.vue'

/** This week so far. Recorded practice minutes and revision plan counts are the server's; nothing else is derived. */
const props = defineProps<{ week: WeekContext }>()
const tracks = computed(() =>
  props.week.minutes_by_track
    .filter((t) => t.minutes > 0)
    .sort((a, b) => b.minutes - a.minutes || a.track.localeCompare(b.track))
    .slice(0, 4),
)
</script>

<template>
  <section
    class="week card"
    aria-labelledby="week-title"
    data-testid="week-progress"
  >
    <h2
      id="week-title"
      class="eyebrow"
    >
      This week
    </h2>
    <template v-if="week.practice_minutes > 0">
      <p class="big tabular">
        {{ formatMinutes(week.practice_minutes) }}<span
          v-if="week.target_minutes"
          class="of"
        > / {{ formatMinutes(week.target_minutes) }}</span>
      </p>
      <ProgressBar
        v-if="week.target_minutes"
        :value="week.practice_minutes"
        :max="week.target_minutes"
        label="Practice time this week"
      />
      <ul
        v-if="tracks.length"
        class="tracks"
      >
        <li
          v-for="t in tracks"
          :key="t.track"
        >
          <span>{{ TRACK_LABEL[t.track] ?? t.track }}</span>
          <span class="tabular">{{ formatMinutes(t.minutes) }}</span>
        </li>
      </ul>
      <p class="facts">
        {{ plural(week.active_days, 'practice day') }} so far<template v-if="week.revision.completion_pct !== null">
          · revision {{ week.revision.completion_pct }}% done
        </template>
      </p>
    </template>
    <p
      v-else
      class="muted"
    >
      Nothing logged yet this week. Your first mission sets the pace.
    </p>
  </section>
</template>

<style scoped>
.week { display: grid; gap: var(--s-3); }
.big { font-size: var(--fs-xl); font-weight: 700; letter-spacing: -0.02em; }
.of { font-size: var(--fs-md); font-weight: 500; color: var(--text-3); }
.tracks { display: grid; gap: var(--s-1); font-size: var(--fs-sm); }
.tracks li { display: flex; justify-content: space-between; color: var(--text-2); }
.facts { font-size: var(--fs-sm); color: var(--text-3); }
</style>

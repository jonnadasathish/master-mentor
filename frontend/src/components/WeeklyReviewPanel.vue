<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'
import { ApiError } from '../api/client'
import type { WeeklyReview } from '../api/types'

/** Last completed week (MENTOR_ENGINE §10) + reflection. Every number comes from the stored review. */
const FIELDS = [
  ['improved', 'What improved?'], ['still_weak', 'What is still weak?'], ['failure_causes', 'Why did things fail?'],
  ['stop_doing', 'What will you stop doing?'], ['next_priority', 'Next week’s priority'],
] as const
const review = ref<WeeklyReview | null>(null)
const reflection = reactive<Record<string, string>>({})
const message = ref('')
const unavailable = ref('')

async function load(): Promise<void> {
  try {
    review.value = (await api.get<WeeklyReview>('/weekly-reviews/latest')).data
    Object.assign(reflection, review.value.reflection ?? {})
  } catch (caught) {
    unavailable.value = caught instanceof ApiError ? caught.message : String(caught)
  }
}

async function save(): Promise<void> {
  if (!review.value) return
  review.value = (await api.post<WeeklyReview>(`/weekly-reviews/${review.value.week_start}/reflection`, { ...reflection })).data
  message.value = 'Reflection saved.'
}

onMounted(load)
</script>

<template>
  <section
    v-if="review"
    data-testid="weekly-review"
  >
    <h2>Week {{ review.metrics.week_start }} – {{ review.metrics.week_end }}</h2>
    <ul class="metrics">
      <li>Active days: {{ review.metrics.active_days }}</li>
      <li>Plan: {{ review.metrics.completed_minutes }} / {{ review.metrics.planned_minutes }} min ({{ review.metrics.plan_completion_pct ?? '—' }}%)</li>
      <li>Revisions done: {{ review.metrics.revision_completion_pct ?? '—' }}%</li>
      <li>Readiness: {{ review.metrics.readiness.start.state }} → {{ review.metrics.readiness.end.state }}</li>
      <li>Backlog at week end: {{ review.metrics.backlog_minutes }} min</li>
      <li v-if="review.metrics.strongest_improvement">
        Strongest improvement: {{ review.metrics.strongest_improvement.skill_key }}
        {{ review.metrics.strongest_improvement.before }} → {{ review.metrics.strongest_improvement.after }}
      </li>
      <li v-if="review.metrics.biggest_regression">
        Biggest regression: {{ review.metrics.biggest_regression.skill_key }}
        {{ review.metrics.biggest_regression.before }} → {{ review.metrics.biggest_regression.after }}
      </li>
    </ul>
    <h3>Minutes by track</h3>
    <ul class="metrics">
      <li
        v-for="(v, track) in review.metrics.minutes_by_track"
        :key="track"
      >
        {{ String(track).replace('_', ' ') }}: {{ v.minutes }} / {{ v.weekly_target }}
      </li>
    </ul>
    <h3>Next week’s focus</h3>
    <p>
      {{ review.next_focus.top_gaps.map((g) => `${g.skill_key} (${g.status.toLowerCase()} ${g.priority})`).join(', ') || 'No actionable gaps.' }}
      <template v-if="review.next_focus.tracks_below_floor.length">
        · Behind on: {{ review.next_focus.tracks_below_floor.join(', ') }}
      </template>
    </p>
    <form
      class="reflection"
      data-testid="reflection-form"
      @submit.prevent="save"
    >
      <label
        v-for="[key, label] in FIELDS"
        :key="key"
      >{{ label }}
        <textarea
          v-model="reflection[key]"
          rows="2"
          maxlength="2000"
          :data-testid="`reflection-${key}`"
        />
      </label>
      <button type="submit">
        Save reflection
      </button>
      <span
        v-if="message"
        role="status"
      >{{ message }}</span>
    </form>
  </section>
  <p v-else-if="unavailable">
    Weekly review: {{ unavailable }}
  </p>
</template>

<style scoped>
.metrics { display: flex; flex-wrap: wrap; gap: 0.3rem 1.2rem; padding: 0; list-style: none; font-size: 0.9rem; }
.reflection { display: flex; flex-direction: column; gap: 0.4rem; max-width: 40rem; }
.reflection label { display: flex; flex-direction: column; font-size: 0.85rem; }
</style>

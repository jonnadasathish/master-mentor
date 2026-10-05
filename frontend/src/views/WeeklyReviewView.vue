<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api'
import { ApiError } from '../api/client'
import type { WeeklyReview } from '../api/types'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import Icon from '../components/common/Icon.vue'
import PageHeader from '../components/common/PageHeader.vue'
import ProgressBar from '../components/common/ProgressBar.vue'
import SectionHeading from '../components/common/SectionHeading.vue'
import Skeleton from '../components/common/Skeleton.vue'
import StatusPill from '../components/common/StatusPill.vue'
import { formatMinutes, plural, shortDate } from '../presentation/format'
import { READINESS_LABEL, stateFromGapStatus, TRACK_LABEL } from '../presentation/language'
import { useReviewStore, useSkillsStore } from '../stores/data'

/** The weekly review as a mentor conversation: what improved, what slipped, the one gap, and next week's focus. */
const FIELDS = [
  ['improved', 'What are you proud of this week?'],
  ['still_weak', 'What still feels shaky?'],
  ['failure_causes', 'Why did things go wrong when they did?'],
  ['stop_doing', 'What will you stop doing?'],
  ['next_priority', "Next week's focus"],
] as const
const reviews = useReviewStore()
const skills = useSkillsStore()
const weekStart = ref<string | null>(null)
const review = ref<WeeklyReview | null>(null)
const failure = ref<unknown>(null)
const loading = ref(true)
const reflection = reactive<Record<string, string>>({})
const message = ref('')
const saving = ref(false)

const metrics = computed(() => review.value?.metrics ?? null)
const focus = computed(() => review.value?.next_focus ?? null)
const quiet = computed(() => !!metrics.value && metrics.value.active_days === 0 && metrics.value.planned_minutes === 0)
const improved = computed(() => {
  const m = metrics.value
  if (!m) return []
  const out: { key: string; text: string }[] = []
  if (m.strongest_improvement) {
    const s = m.strongest_improvement
    out.push({ key: s.skill_key, text: `moved from ${s.before} to ${s.after}` })
  }
  for (const g of [...m.gap_changes].filter((x) => x.delta < 0).sort((a, b) => a.delta - b.delta)) {
    if (!out.some((o) => o.key === g.skill_key)) out.push({ key: g.skill_key, text: 'is less of a gap than last week' })
  }
  return out.slice(0, 3)
})
const regressed = computed(() => {
  const m = metrics.value
  if (!m) return []
  const out: { key: string; text: string }[] = []
  if (m.biggest_regression) {
    const s = m.biggest_regression
    out.push({ key: s.skill_key, text: `slipped from ${s.before} to ${s.after}` })
  }
  for (const g of [...m.gap_changes].filter((x) => x.delta > 0).sort((a, b) => b.delta - a.delta)) {
    if (!out.some((o) => o.key === g.skill_key)) out.push({ key: g.skill_key, text: 'became more of a gap' })
  }
  return out.slice(0, 3)
})
const biggest = computed(() => focus.value?.top_gaps[0] ?? null)
const tracks = computed(() =>
  Object.entries(metrics.value?.minutes_by_track ?? {}).filter(([, v]) => v.minutes > 0 || v.weekly_target > 0),
)
const suggested = computed(() => {
  const f = focus.value
  if (!f) return ''
  const names = f.top_gaps.map((g) => skills.nameOf(g.skill_key)).join(', ')
  return names ? `Work on ${names}.` : ''
})
const weeks = computed(() => reviews.all.data ?? [])
const behind = computed(() => (focus.value?.tracks_below_floor ?? []).map((t) => TRACK_LABEL[t] ?? t).join(', '))

async function open(week: string | null): Promise<void> {
  loading.value = true
  failure.value = null
  message.value = ''
  try {
    const path = week ? `/weekly-reviews/${week}` : '/weekly-reviews/latest'
    review.value = (await api.get<WeeklyReview>(path)).data
    weekStart.value = review.value.week_start
    for (const [key] of FIELDS) reflection[key] = review.value.reflection?.[key] ?? ''
    if (!reflection.next_priority) reflection.next_priority = suggested.value
  } catch (caught) {
    failure.value = caught
  } finally {
    loading.value = false
  }
}

async function accept(): Promise<void> {
  if (!review.value) return
  saving.value = true
  message.value = ''
  try {
    review.value = (await api.post<WeeklyReview>(`/weekly-reviews/${review.value.week_start}/reflection`, { ...reflection })).data
    message.value = "Saved. Next week's focus is on record."
    await reviews.all.refresh()
  } catch (caught) {
    message.value = caught instanceof ApiError ? caught.message : String(caught)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await Promise.all([skills.ensure(), reviews.all.ensure()])
  await open(null)
})
</script>

<template>
  <div class="page page-narrow">
    <PageHeader
      eyebrow="Weekly review"
      title="This is what changed this week."
    >
      <label
        v-if="weeks.length > 1"
        class="picker"
      >
        <span class="sr-only">Choose a week</span>
        <select
          :value="weekStart ?? ''"
          data-testid="week-picker"
          @change="open(($event.target as HTMLSelectElement).value)"
        >
          <option
            v-for="w in weeks"
            :key="w.week_start"
            :value="w.week_start"
          >Week of {{ shortDate(w.week_start) }}</option>
        </select>
      </label>
    </PageHeader>

    <Skeleton
      v-if="loading"
      height="18rem"
      radius="var(--r-lg)"
    />
    <ErrorState
      v-else-if="failure"
      :error="failure"
      @retry="open(weekStart)"
    />

    <template v-else-if="review && metrics && focus">
      <EmptyState
        v-if="quiet"
        icon="calendar"
        title="A quiet week."
        :body="`Nothing was planned or practised in the week of ${shortDate(metrics.week_start)}. Your next review will have more to say.`"
      >
        <RouterLink
          :to="{ name: 'today' }"
          class="btn btn-primary"
        >
          Go to Today
        </RouterLink>
      </EmptyState>

      <template v-else>
        <p class="week-line muted">
          {{ shortDate(metrics.week_start) }} – {{ shortDate(metrics.week_end) }} ·
          {{ plural(metrics.active_days, 'active day') }} ·
          {{ formatMinutes(metrics.completed_minutes) }} of {{ formatMinutes(metrics.planned_minutes) }} planned done<template v-if="metrics.plan_completion_pct !== null">
            ({{ metrics.plan_completion_pct }}%)
          </template>
        </p>

        <section class="block">
          <SectionHeading title="You improved" />
          <ul
            v-if="improved.length"
            class="items"
            data-testid="improved"
          >
            <li
              v-for="i in improved"
              :key="i.key"
            >
              <Icon
                name="trending"
                :size="16"
                class="up"
              />
              <span><RouterLink :to="{ name: 'skill', params: { key: i.key } }">{{ skills.nameOf(i.key) }}</RouterLink> {{ i.text }}.</span>
            </li>
          </ul>
          <p
            v-else
            class="muted"
          >
            No skill moved up enough to call out this week. Steady practice is what changes that.
          </p>
        </section>

        <section class="block">
          <SectionHeading title="You regressed" />
          <ul
            v-if="regressed.length"
            class="items"
            data-testid="regressed"
          >
            <li
              v-for="i in regressed"
              :key="i.key"
            >
              <Icon
                name="alert-triangle"
                :size="16"
                class="down"
              />
              <span><RouterLink :to="{ name: 'skill', params: { key: i.key } }">{{ skills.nameOf(i.key) }}</RouterLink> {{ i.text }}.</span>
            </li>
          </ul>
          <p
            v-else
            class="muted"
          >
            Nothing slipped. 
          </p>
        </section>

        <section
          v-if="biggest"
          class="block highlight"
        >
          <SectionHeading title="Your biggest gap" />
          <RouterLink
            :to="{ name: 'skill', params: { key: biggest.skill_key } }"
            class="big-gap"
            data-testid="biggest-gap"
          >
            <span class="bg-name">{{ skills.nameOf(biggest.skill_key) }}</span>
            <StatusPill :state="stateFromGapStatus(biggest.status)" />
          </RouterLink>
        </section>

        <section class="block">
          <SectionHeading title="Revision health" />
          <p v-if="metrics.revision_completion_pct !== null">
            You did <strong>{{ metrics.revision_completion_pct }}%</strong> of the reviews planned this week.
          </p>
          <p
            v-else
            class="muted"
          >
            No reviews were planned this week.
          </p>
          <ProgressBar
            v-if="metrics.revision_completion_pct !== null"
            :value="metrics.revision_completion_pct"
            :max="100"
            label="Reviews completed this week"
            tone="healthy"
          />
          <p class="muted small">
            {{ formatMinutes(metrics.backlog_minutes) }} of reviews were waiting at the end of the week.
          </p>
        </section>

        <section
          v-if="tracks.length"
          class="block"
        >
          <SectionHeading title="Where your time went" />
          <ul class="tracks">
            <li
              v-for="[track, v] in tracks"
              :key="track"
            >
              <span>{{ TRACK_LABEL[track] ?? track }}</span>
              <ProgressBar
                :value="v.minutes"
                :max="v.weekly_target"
                :label="`${TRACK_LABEL[track] ?? track} minutes against the weekly target`"
                size="sm"
              />
              <span class="small muted tabular">{{ formatMinutes(v.minutes) }} / {{ formatMinutes(v.weekly_target) }}</span>
            </li>
          </ul>
        </section>

        <section class="block mentor">
          <SectionHeading title="Mentor recommendation" />
          <p class="lead">
            {{ suggested || 'Keep your reviews up and let the plan lead.' }}
          </p>
          <p
            v-if="focus.tracks_below_floor.length"
            class="muted small"
          >
            You're behind on: {{ behind }}.
          </p>
          <p
            v-if="metrics.readiness.start.state !== metrics.readiness.end.state"
            class="small"
          >
            Readiness moved from {{ READINESS_LABEL[metrics.readiness.start.state] ?? metrics.readiness.start.state }} to
            <strong>{{ READINESS_LABEL[metrics.readiness.end.state] ?? metrics.readiness.end.state }}</strong>.
          </p>
        </section>

        <form
          class="reflection card"
          data-testid="reflection-form"
          @submit.prevent="accept"
        >
          <h2>Your reflection</h2>
          <label
            v-for="[key, text] in FIELDS"
            :key="key"
          >{{ text }}
            <textarea
              v-model="reflection[key]"
              rows="2"
              maxlength="2000"
              :data-testid="`reflection-${key}`"
            />
          </label>
          <div class="row">
            <button
              type="submit"
              class="btn btn-primary btn-lg"
              :disabled="saving"
              data-testid="accept"
            >
              Accept next week's focus
            </button>
            <span
              v-if="message"
              role="status"
              class="saved"
            >{{ message }}</span>
          </div>
        </form>
      </template>
    </template>
  </div>
</template>

<style scoped>
.picker select { min-width: 12rem; }
.week-line { font-size: var(--fs-sm); }
.block { display: grid; gap: var(--s-3); padding: var(--s-5); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); }
.block :deep(.section-heading) { margin-bottom: 0; }
.items { display: grid; gap: var(--s-2); }
.items li { display: flex; align-items: flex-start; gap: var(--s-3); }
.items :deep(svg) { margin-top: 0.2rem; flex: none; }
.up { color: var(--healthy-fg); }
.down { color: var(--high-fg); }
.highlight { background: var(--accent-soft); border-color: var(--accent-border); }
.big-gap { display: flex; align-items: center; justify-content: space-between; gap: var(--s-3); color: var(--text); }
.bg-name { font-size: var(--fs-lg); font-weight: 700; letter-spacing: -0.015em; }
.tracks { display: grid; gap: var(--s-3); }
.tracks li { display: grid; grid-template-columns: 9.5rem minmax(0, 1fr) 8.5rem; align-items: center; gap: var(--s-3); font-size: var(--fs-sm); }
.small { font-size: var(--fs-sm); }
.mentor { border-left: 4px solid var(--accent); }
.lead { font-size: var(--fs-lg); font-weight: 560; letter-spacing: -0.01em; }
.reflection { display: grid; gap: var(--s-4); }
.reflection label { display: grid; gap: var(--s-1); font-size: var(--fs-sm); color: var(--text-2); font-weight: 560; }
.saved { color: var(--healthy-fg); font-weight: 560; }
@media (max-width: 767px) { .tracks li { grid-template-columns: 1fr; gap: var(--s-1); } }
</style>

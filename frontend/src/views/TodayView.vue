<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../api'
import { ApiError } from '../api/client'
import type { Effects } from '../api/types'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import SectionHeading from '../components/common/SectionHeading.vue'
import MentorMessage from '../components/mentor/MentorMessage.vue'
import TodayHeader from '../components/mentor/TodayHeader.vue'
import ReadinessCard from '../components/readiness/ReadinessCard.vue'
import CalibrationCta from '../components/calibration/CalibrationCta.vue'
import CalibrationProgress from '../components/calibration/CalibrationProgress.vue'
import DiagnosticList from '../components/calibration/DiagnosticList.vue'
import WhatCalibrationMeans from '../components/calibration/WhatCalibrationMeans.vue'
import MissionList from '../components/missions/MissionList.vue'
import TodaySkeleton from '../components/missions/TodaySkeleton.vue'
import WeekProgress from '../components/missions/WeekProgress.vue'
import RevisionGlance from '../components/revision/RevisionGlance.vue'
import GapList from '../components/skills/GapList.vue'
import StrengthsList from '../components/mentor/StrengthsList.vue'
import Icon from '../components/common/Icon.vue'
import { PHASE_LABEL } from '../presentation/language'
import { formatMinutes } from '../presentation/format'
import { humaniseKeys } from '../presentation/text'
import {
  refreshDerivedData, useProfileStore, useReadinessStore, useSkillsStore, useStartingProfileStore, useTodayStore,
} from '../stores/data'

/** Today is revalidated when you come back after a while, so an app left open overnight never shows yesterday. */
const STALE_MS = 10 * 60_000
const today = useTodayStore()
const skills = useSkillsStore()
const readiness = useReadinessStore()
const profile = useProfileStore()
const starting = useStartingProfileStore()

const results = ref<Record<number, Effects>>({})
const mapSeen = ref(readSeen())
const actionError = ref<unknown>(null)

const data = computed(() => today.data)
/** Calibrating until every baseline task is done (D-080); the plan follows the engines either way. */
const calibrating = computed(
  () => (data.value?.calibration.active ?? false) && today.baseline.data?.phase !== 'COMPLETE',
)
const targetDate = computed(() => starting.data?.target?.target_date ?? null)
const diagnostics = computed(() => (data.value?.plan.items ?? []).filter((i) => i.candidate_type === 'BASELINE'))
const name = computed(() => {
  const n = profile.settings.data?.display_name?.trim()
  return n && n !== 'Owner' ? n : null // "Owner" is the untouched default, not a name
})
const phaseLabel = computed(() => (calibrating.value ? PHASE_LABEL.CALIBRATION! : (PHASE_LABEL[data.value?.phase ?? ''] ?? '')))
const items = computed(() => data.value?.plan.items ?? [])
const finishedText = computed(() => {
  const spare = data.value?.plan.unallocated_minutes ?? 0
  return spare > 0
    ? `That's today's plan. ${formatMinutes(spare)} of your time is unplanned: the mentor doesn't invent work.`
    : "That's today's plan."
})
const allDone = computed(() => items.value.length > 0 && items.value.every((i) => i.status !== 'PENDING'))
const showSkillMap = computed(() => !!data.value && !calibrating.value && !mapSeen.value)
const hasStrengths = computed(() => !calibrating.value && skills.list.some((s) => s.state.assessed && s.gap?.status === 'NONE'))

function readSeen(): boolean {
  try {
    return localStorage.getItem('mm.skillMapSeen') === '1'
  } catch {
    return false
  }
}
function dismissMap(): void {
  mapSeen.value = true
  try {
    localStorage.setItem('mm.skillMapSeen', '1')
  } catch {
    // Storage can be unavailable (private window); the banner then simply shows again next visit.
  }
}

async function load(): Promise<void> {
  await today.refresh()
  await loadSupporting()
}

/** Everything the page needs besides the plan; each resource is fetched once and then served from the cache. */
async function loadSupporting(): Promise<void> {
  const jobs = [
    today.week.ensure(STALE_MS), skills.ensure(), readiness.ensure(), readiness.history.ensure(), profile.settings.ensure(),
  ]
  jobs.push(today.baseline.ensure(), starting.ensure())
  await Promise.all(jobs)
}

async function completed(itemId: number, effects?: Effects): Promise<void> {
  if (effects) results.value = { ...results.value, [itemId]: effects }
  await refreshDerivedData()
}

async function regenerate(): Promise<void> {
  actionError.value = null
  try {
    await api.post('/plan/today/regenerate', {})
    await refreshDerivedData()
  } catch (caught) {
    actionError.value = caught instanceof ApiError ? caught : new Error(String(caught))
  }
}

/** Skill and baseline-item keys inside backend sentences become names. */
const nameMap = computed(() => {
  const pairs: [string, string][] = skills.list.map((s) => [s.key, s.name])
  for (const b of today.baseline.data?.items ?? []) pairs.push([b.key, b.name.split(':')[0]!.trim()])
  return pairs
})
const humanise = (text: string) => humaniseKeys(text, nameMap.value)
const showAllStops = ref(false)
const STOPS_SHOWN = 3
const stops = computed(() => data.value?.plan.stop_list ?? [])

onMounted(async () => {
  await today.ensure(STALE_MS)
  await loadSupporting()
})
</script>

<template>
  <div class="page today">
    <TodaySkeleton v-if="!data && !today.error" />
    <ErrorState
      v-else-if="!data"
      :error="today.error"
      @retry="load"
    />

    <template v-else>
      <TodayHeader
        :name="name"
        :date="data.plan_date"
        :day="today.week.data?.preparation_day ?? null"
        :phase="phaseLabel"
        :weeks-left="data.weeks_left"
        :target-date="targetDate"
        :has-goal="data.goal_exists"
      />

      <div class="cols">
        <div class="main">
          <template v-if="calibrating">
            <CalibrationCta
              v-if="today.baseline.data"
              class="o-hero"
              :baseline="today.baseline.data"
            />
            <CalibrationProgress
              v-if="today.baseline.data"
              class="o-mentor"
              :baseline="today.baseline.data"
              :target-date="targetDate"
              :weeks-left="data.weeks_left"
              :phase="phaseLabel"
            />
            <section
              v-if="diagnostics.length"
              class="o-missions"
              aria-labelledby="diag-title"
            >
              <SectionHeading
                id="diag-title"
                title="Today's diagnostic work"
              >
                <span class="tabular muted">{{ formatMinutes(data.plan.allocated_minutes) }} planned of {{ formatMinutes(data.plan.budget_minutes) }}</span>
              </SectionHeading>
              <DiagnosticList
                :items="diagnostics"
                :battery="today.baseline.data?.items ?? []"
              />
            </section>
            <WhatCalibrationMeans class="o-gaps" />
          </template>
          <template v-else>
            <section
              v-if="showSkillMap"
              class="skill-map o-hero"
              data-testid="skill-map-ready"
            >
              <div>
                <h2>Baseline complete. Your personal roadmap is ready.</h2>
                <p class="muted skill-map-copy">
                  What was measured now drives your plan: your readiness, strengths, biggest gaps and today's missions.
                </p>
                <p class="skill-map-links">
                  <RouterLink
                    :to="{ name: 'roadmap' }"
                    class="btn btn-sm btn-primary"
                    data-testid="banner-roadmap"
                  >
                    View my roadmap
                  </RouterLink>
                  <RouterLink
                    :to="{ name: 'progress' }"
                    class="btn btn-sm"
                  >
                    Your current state
                  </RouterLink>
                </p>
              </div>
              <button
                type="button"
                class="btn btn-sm"
                @click="dismissMap"
              >
                Got it
              </button>
            </section>

            <MentorMessage
              class="o-mentor"
              :text="humanise(data.plan.message.text)"
              :payload="data.plan.message.payload"
            />

            <section
              class="missions-section o-missions"
              aria-labelledby="missions-title"
            >
              <SectionHeading
                id="missions-title"
                title="Today's mission"
              >
                <span
                  class="tabular muted"
                  data-testid="plan-budget"
                >{{ formatMinutes(data.plan.allocated_minutes) }} planned of {{ formatMinutes(data.plan.budget_minutes) }}</span>
              </SectionHeading>

              <MissionList
                v-if="items.length"
                ref="list"
                :items="items"
                :client="api"
                :battery="today.baseline.data?.items ?? []"
                :results="results"
                @changed="load"
                @completed="completed"
              />
              <EmptyState
                v-else
                icon="check-circle"
                title="Nothing is planned for today."
                body="No gap needs your attention and nothing is due. Master Mentor doesn't invent work."
              >
                <RouterLink
                  :to="{ name: 'log' }"
                  class="btn"
                >
                  Log some practice anyway
                </RouterLink>
              </EmptyState>

              <p
                v-if="allDone"
                class="finished"
                data-testid="day-finished"
              >
                <Icon
                  name="check-circle"
                  :size="18"
                />
                <span>{{ finishedText }}</span>
              </p>
              <div class="plan-actions">
                <button
                  type="button"
                  class="link-btn"
                  data-testid="regenerate"
                  @click="regenerate"
                >
                  Re-plan what's left
                </button>
                <ErrorState
                  v-if="actionError"
                  :error="actionError"
                  @retry="regenerate"
                />
              </div>
            </section>

            <section
              v-if="!calibrating || data.top_gaps.length"
              class="o-gaps"
              aria-labelledby="gaps-title"
            >
              <SectionHeading
                id="gaps-title"
                title="Your biggest gaps"
              />
              <GapList
                v-if="data.top_gaps.length"
                :gaps="data.top_gaps"
              />
              <p
                v-else
                class="quiet-empty"
              >
                <Icon
                  name="check-circle"
                  :size="16"
                /> Nothing critical right now.
              </p>
            </section>

            <section
              v-if="hasStrengths"
              class="o-strengths"
              aria-labelledby="strengths-title"
            >
              <SectionHeading
                id="strengths-title"
                title="Your strengths"
              />
              <StrengthsList />
            </section>

            <section
              v-if="stops.length"
              class="o-stop"
              aria-labelledby="stop-title"
            >
              <SectionHeading
                id="stop-title"
                title="Not today"
              />
              <ul
                class="stop-list"
                data-testid="stop-list"
              >
                <li
                  v-for="s in showAllStops ? stops : stops.slice(0, STOPS_SHOWN)"
                  :key="s.skill"
                >
                  <Icon
                    name="pause"
                    :size="15"
                  />
                  {{ humanise(s.instruction) }}
                </li>
              </ul>
              <button
                v-if="stops.length > STOPS_SHOWN"
                type="button"
                class="link-btn more-stops"
                @click="showAllStops = !showAllStops"
              >
                {{ showAllStops ? 'Show fewer' : `Show all ${stops.length}` }}
              </button>
            </section>
          </template>
        </div>

        <aside
          class="rail"
          aria-label="Your readiness and week"
        >
          <ReadinessCard
            class="o-readiness"
            :summary="data.readiness"
            :calibration="data.calibration"
            :readiness="readiness.data"
            :history="readiness.history.data ?? []"
          />
          <WeekProgress
            v-if="today.week.data"
            class="o-week"
            :week="today.week.data"
          />
          <RevisionGlance
            class="o-revision"
            :revisions="data.revisions"
          />
        </aside>
      </div>
    </template>
  </div>
</template>

<style scoped>
.today { gap: var(--s-5); }
.cols { display: grid; grid-template-columns: minmax(0, 1fr) 20rem; gap: var(--s-6); align-items: start; }
.main, .rail { display: grid; gap: var(--s-6); align-content: start; min-width: 0; }
.rail { gap: var(--s-4); position: sticky; top: var(--s-5); }
.skill-map { display: flex; align-items: center; justify-content: space-between; gap: var(--s-4); padding: var(--s-4) var(--s-5); background: var(--healthy-bg); border: 1px solid var(--healthy-bd); border-radius: var(--r-lg); }
.skill-map h2 { color: var(--healthy-fg); }
.skill-map-links { display: flex; gap: var(--s-2); flex-wrap: wrap; margin-top: var(--s-3); }
.finished { display: flex; gap: var(--s-2); align-items: flex-start; margin-top: var(--s-4); padding: var(--s-4); background: var(--healthy-bg); color: var(--healthy-fg); border-radius: var(--r-md); font-weight: 560; }
.plan-actions { margin-top: var(--s-3); display: grid; gap: var(--s-3); font-size: var(--fs-sm); }
.quiet-empty { display: flex; align-items: center; gap: var(--s-2); padding: var(--s-4); background: var(--surface); border: 1px dashed var(--border-strong); border-radius: var(--r-md); color: var(--text-2); }
.stop-list { display: grid; gap: var(--s-2); }
.more-stops { margin-top: var(--s-2); font-size: var(--fs-sm); }
.stop-list li { display: flex; gap: var(--s-2); align-items: flex-start; padding: var(--s-3) var(--s-4); background: var(--blocked-bg); border-radius: var(--r-md); color: var(--text-2); font-size: var(--fs-sm); }

@media (max-width: 1279px) {
  .cols { grid-template-columns: minmax(0, 1fr); gap: var(--s-5); }
  .rail { position: static; }
}
/* Phone: recompose, not shrink. Mentor and the day's missions first, then readiness, gaps and the week. */
@media (max-width: 767px) {
  .cols, .main, .rail { display: contents; }
  .page.today { display: grid; gap: var(--s-5); }
  .today-header { order: -1; }
  .o-hero { order: 1; }
  .o-mentor { order: 2; }
  .o-missions { order: 3; }
  .o-readiness { order: 4; }
  .o-gaps { order: 5; }
  .o-strengths { order: 6; }
  .o-stop { order: 7; }
  .o-week { order: 8; }
  .o-revision { order: 9; }
  .skill-map { padding: var(--s-3) var(--s-4); }
  .skill-map-copy, .skill-map-links { display: none; }
}
</style>

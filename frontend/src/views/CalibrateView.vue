<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '../api'
import type { Effects } from '../api/types'
import CalibrationCta from '../components/calibration/CalibrationCta.vue'
import CalibrationProgress from '../components/calibration/CalibrationProgress.vue'
import WhatCalibrationMeans from '../components/calibration/WhatCalibrationMeans.vue'
import ErrorState from '../components/common/ErrorState.vue'
import Icon from '../components/common/Icon.vue'
import PageHeader from '../components/common/PageHeader.vue'
import SectionHeading from '../components/common/SectionHeading.vue'
import Skeleton from '../components/common/Skeleton.vue'
import StatusPill from '../components/common/StatusPill.vue'
import MissionList from '../components/missions/MissionList.vue'
import { formatMinutes } from '../presentation/format'
import { batteryTitle } from '../presentation/mission'
import { stateFromGapStatus } from '../presentation/language'
import {
  refreshDerivedData, usePersonalStore, useSkillsStore, useStartingProfileStore, useTodayStore,
} from '../stores/data'

/** The calibration hub: where it stands, today's diagnostic work, what's done, and one clear next step. */
const route = useRoute()
const today = useTodayStore()
const skills = useSkillsStore()
const profile = useStartingProfileStore()
const personal = usePersonalStore()
const list = ref<InstanceType<typeof MissionList> | null>(null)
const results = ref<Record<number, Effects>>({})

const baseline = computed(() => today.baseline.data)
const target = computed(() => profile.data?.target ?? null)
const plan = computed(() => today.data?.plan ?? null)
const scheduled = computed(() => (plan.value?.items ?? []).filter((i) => i.candidate_type === 'BASELINE'))
const finishedKeys = computed(() => new Set((baseline.value?.items ?? []).filter((i) => i.complete).map((i) => i.key)))
/**
 * Today's calibration missions to show. A mission whose assessment is already complete but whose plan item is still
 * pending (recorded before D-082 closed such items) is listed under "Completed" instead and never offered again.
 */
const work = computed(() => scheduled.value.filter((i) => !(i.status === 'PENDING' && i.battery_item_key && finishedKeys.value.has(i.battery_item_key))))
const pending = computed(() => work.value.filter((i) => i.status === 'PENDING'))
/** Today's scheduled calibration work is all finished, skipped or deferred: nothing to start until the next session. */
const todayDone = computed(() => scheduled.value.length > 0 && pending.value.length === 0)
/** The first assessment still to do that is not on today's list. Named from the battery, never invented. */
const upNext = computed(() => {
  const planned = new Set(scheduled.value.map((i) => i.battery_item_key))
  const item = (baseline.value?.items ?? []).find((i) => !i.complete && !planned.has(i.key))
  return item ? batteryTitle(item).title : null
})
const finished = computed(() => (baseline.value?.items ?? []).filter((i) => i.complete))
const error = computed(() => today.error ?? today.baseline.error)
const ready = computed(() => baseline.value !== null && today.data !== null)
const state = computed(() => personal.state.data)

async function load(): Promise<void> {
  await Promise.all([today.refresh(), today.baseline.refresh()])
}

async function completed(itemId: number, effects?: Effects): Promise<void> {
  if (effects) results.value = { ...results.value, [itemId]: effects }
  await refreshDerivedData()
}

async function begin(): Promise<void> {
  await list.value?.startNext()
}

onMounted(async () => {
  await Promise.all([today.ensure(), today.baseline.ensure(), skills.ensure(), profile.ensure(), today.week.ensure()])
  if (baseline.value?.phase === 'COMPLETE') await personal.state.ensure()
  if (route.query.start === '1') await begin()
})
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="Calibration"
      title="Calibrate your skills"
      description="Short real tasks that measure where you are. Your results become your personal roadmap."
    />

    <Skeleton
      v-if="!ready && !error"
      height="18rem"
      radius="var(--r-xl)"
    />
    <ErrorState
      v-else-if="!ready"
      :error="error"
      @retry="load"
    />

    <template v-else-if="baseline">
      <CalibrationCta
        :baseline="baseline"
        hub
        @continue="begin"
      />
      <CalibrationProgress
        :baseline="baseline"
        :target-date="target?.target_date"
        :weeks-left="target?.weeks_left"
        :phase="target?.phase"
      />

      <section
        v-if="baseline.phase === 'COMPLETE' && state"
        class="summary card"
        aria-labelledby="summary-title"
        data-testid="baseline-summary"
      >
        <h2
          id="summary-title"
          class="eyebrow"
        >
          What the baseline found
        </h2>
        <div class="cols">
          <div>
            <h3>Strongest</h3>
            <ul v-if="state.strong.items.length">
              <li
                v-for="i in state.strong.items.slice(0, 3)"
                :key="i.skill_key"
              >
                <RouterLink :to="{ name: 'skill', params: { key: i.skill_key } }">
                  {{ i.name }}
                </RouterLink>
                <span class="muted tabular">{{ i.score }} / {{ i.target }}</span>
              </li>
            </ul>
            <p
              v-else
              class="muted"
            >
              Nothing at target yet.
            </p>
          </div>
          <div>
            <h3>Biggest gaps</h3>
            <ul v-if="state.critical.items.length || state.developing.items.length">
              <li
                v-for="i in [...state.critical.items, ...state.developing.items].slice(0, 3)"
                :key="i.skill_key"
              >
                <RouterLink :to="{ name: 'skill', params: { key: i.skill_key } }">
                  {{ i.name }}
                </RouterLink>
                <StatusPill
                  :state="stateFromGapStatus(i.status)"
                  quiet
                />
              </li>
            </ul>
            <p
              v-else
              class="muted"
            >
              No gap stands out.
            </p>
          </div>
          <div>
            <h3>Still unmeasured</h3>
            <p class="big tabular">
              {{ state.unknown.count }}
            </p>
            <p class="muted">
              skills have no evidence yet.
            </p>
          </div>
        </div>
      </section>

      <section
        v-if="baseline.phase !== 'COMPLETE'"
        aria-labelledby="work-title"
      >
        <SectionHeading
          id="work-title"
          title="Today's calibration work"
        >
          <span
            v-if="plan"
            class="tabular muted"
          >{{ formatMinutes(plan.allocated_minutes) }} planned of {{ formatMinutes(plan.budget_minutes) }}</span>
        </SectionHeading>
        <p
          v-if="todayDone"
          class="quiet done-note"
          role="status"
          data-testid="today-done"
        >
          <Icon
            name="check-circle"
            :size="16"
          />
          <span>
            You've finished today's calibration work.
            <template v-if="upNext">Next assessment: {{ upNext }}. The mentor schedules it in your next session.</template>
          </span>
        </p>
        <MissionList
          v-if="work.length"
          ref="list"
          :items="work"
          :client="api"
          :battery="baseline.items"
          :results="results"
          @changed="load"
          @completed="completed"
        />
        <p
          v-else-if="!scheduled.length"
          class="quiet"
          data-testid="no-work-today"
        >
          <Icon
            name="check-circle"
            :size="16"
          /> No calibration work is scheduled for the rest of today. Pick it up tomorrow.
        </p>
      </section>

      <section
        v-if="finished.length"
        aria-labelledby="done-title"
      >
        <SectionHeading
          id="done-title"
          title="Completed"
        />
        <ul
          class="done card-quiet divided"
          data-testid="completed-assessments"
        >
          <li
            v-for="i in finished"
            :key="i.key"
          >
            <span
              class="tick"
              aria-hidden="true"
            ><Icon
              name="check"
              :size="12"
            /></span>
            <span class="name">{{ batteryTitle(i).title }}</span>
            <span class="muted tabular">{{ formatMinutes(i.minutes) }}</span>
          </li>
        </ul>
      </section>

      <WhatCalibrationMeans />
    </template>
  </div>
</template>

<style scoped>
.summary { display: grid; gap: var(--s-4); }
.cols { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--s-5); }
h3 { font-size: var(--fs-md); margin-bottom: var(--s-2); }
.cols ul { display: grid; gap: var(--s-2); }
.cols li { display: flex; justify-content: space-between; gap: var(--s-2); align-items: center; }
.big { font-size: var(--fs-2xl); font-weight: 700; letter-spacing: -0.02em; }
.quiet { display: flex; align-items: center; gap: var(--s-2); padding: var(--s-4); background: var(--surface); border: 1px dashed var(--border-strong); border-radius: var(--r-md); color: var(--text-2); }
.done-note { margin-bottom: var(--s-3); }
.done li { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); }
.tick { display: grid; place-items: center; width: 1.4rem; height: 1.4rem; border-radius: 50%; background: var(--healthy-fg); color: #fff; flex: none; }
.name { flex: 1; font-weight: 560; }
@media (max-width: 767px) { .cols { grid-template-columns: 1fr; } }
</style>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import Icon from '../components/common/Icon.vue'
import PageHeader from '../components/common/PageHeader.vue'
import ProgressBar from '../components/common/ProgressBar.vue'
import SectionHeading from '../components/common/SectionHeading.vue'
import Skeleton from '../components/common/Skeleton.vue'
import StatusPill from '../components/common/StatusPill.vue'
import CommunicationReadiness from '../components/learning/CommunicationReadiness.vue'
import CurrentState from '../components/progress/CurrentState.vue'
import Sparkline from '../components/readiness/Sparkline.vue'
import TrendChart from '../components/readiness/TrendChart.vue'
import { formatMinutes, plural, shortDate } from '../presentation/format'
import { COMPONENT_LABEL, READINESS_LABEL, READINESS_SUMMARY, ROUND_LABEL } from '../presentation/language'
import { humaniseKeys } from '../presentation/text'
import {
  useMocksStore, usePersonalStore, useReadinessStore, useReviewStore, useRevisionStore, useSkillsStore,
} from '../stores/data'

/** Calm analytics: where you stand, the trend, what is holding you back, and the rhythm of your weeks. */
const readiness = useReadinessStore()
const revision = useRevisionStore()
const mocks = useMocksStore()
const reviews = useReviewStore()
const skills = useSkillsStore()
const personal = usePersonalStore()

const r = computed(() => readiness.data)
const history = computed(() => readiness.history.data ?? [])
const measured = computed(() => r.value?.state !== 'NOT_MEASURED')
const trend = computed(() => history.value.map((h) => ({ date: h.date, value: h.weighted_score })))
const names = computed<[string, string][]>(() => skills.list.map((s) => [s.key, s.name]))
const blockers = computed(() => (r.value?.blockers ?? []).slice(0, 5).map((b) => ({ ...b, text: humaniseKeys(b.message, names.value) })))
const areas = computed(() =>
  (r.value?.components ?? []).map((c) => {
    const series = history.value.map((h) => h.components[c.key]).filter((v): v is number => typeof v === 'number')
    return { key: c.key, label: COMPONENT_LABEL[c.key] ?? c.name, now: c.score, target: c.gate, series, first: series[0] ?? null }
  }),
)
const weeks = computed(() => (reviews.all.data ?? []).slice(0, 8).reverse())
const latestReview = computed(() => (reviews.all.data ?? [])[0] ?? null)
const eased = computed(() =>
  (latestReview.value?.metrics.gap_changes ?? []).filter((g) => g.delta < 0).sort((a, b) => a.delta - b.delta).slice(0, 3),
)
const counts = computed(() => revision.data?.counts ?? {})
const mockTypes = computed(() => (mocks.summary.data?.by_type ?? []).filter((t) => t.trend.length > 0))
const GATE_NAMES: Record<string, string> = {
  G0: 'Enough skills measured', G1: 'Foundations in place', G2: 'Each area at its level', G3: 'Coverage of required skills',
  G4: 'Critical skills proven', G5: 'No critical gaps', G6: 'Mock interviews', G7: 'Revision health', G8: 'Recent practice',
  G9: 'Full simulations',
}
const error = computed(() => readiness.error)

async function load(): Promise<void> {
  await Promise.all([readiness.refresh(), readiness.history.refresh()])
}
onMounted(() =>
  Promise.all([
    readiness.ensure(), readiness.history.ensure(), revision.ensure(), mocks.summary.ensure(), reviews.all.ensure(), skills.ensure(),
    personal.state.ensure(),
  ]),
)
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="Progress"
      title="How you're doing"
      description="Where you stand, how it's changing, and what's holding you back."
    >
      <RouterLink
        :to="{ name: 'review' }"
        class="btn"
      >
        <Icon
          name="calendar"
          :size="16"
        /> Weekly review
      </RouterLink>
    </PageHeader>

    <Skeleton
      v-if="!r && !error"
      height="16rem"
      radius="var(--r-lg)"
    />
    <ErrorState
      v-else-if="!r"
      :error="error"
      @retry="load"
    />

    <template v-else>
      <section class="hero card">
        <div>
          <p class="eyebrow">
            Readiness
          </p>
          <p
            class="state"
            data-testid="readiness-headline"
          >
            {{ READINESS_LABEL[r.state] ?? r.state }}
          </p>
          <p class="muted">
            {{ READINESS_SUMMARY[r.state] }}
          </p>
          <p
            v-if="measured"
            class="score tabular"
          >
            <strong>{{ r.weighted_score }}</strong> / 100
          </p>
          <p
            v-if="r.lapsed"
            class="lapsed"
          >
            <Icon
              name="alert-triangle"
              :size="14"
            /> Your readiness has slipped from where it was. Recent practice will bring it back.
          </p>
        </div>
        <div>
          <p class="eyebrow">
            Readiness over time
          </p>
          <TrendChart
            v-if="trend.length > 1"
            :points="trend"
            label="Readiness score over time"
          />
          <p
            v-else
            class="muted small"
          >
            Your trend appears after a second day of history.
          </p>
        </div>
      </section>

      <CurrentState
        v-if="personal.state.data"
        :state="personal.state.data"
      />

      <section aria-labelledby="holding">
        <SectionHeading
          id="holding"
          title="What's holding you back"
        />
        <ol
          v-if="blockers.length"
          class="blockers card-quiet divided"
          data-testid="blockers"
        >
          <li
            v-for="b in blockers"
            :key="`${b.gate}-${b.subject}`"
          >
            <Icon
              name="target"
              :size="16"
            />
            <span>{{ b.text }}</span>
            <RouterLink
              v-if="b.kind === 'skill'"
              :to="{ name: 'skill', params: { key: b.subject } }"
              class="small"
            >
              Open skill
            </RouterLink>
          </li>
        </ol>
        <EmptyState
          v-else
          icon="check-circle"
          title="Nothing is holding you back."
          body="Every readiness check is passing right now."
        />
      </section>

      <section
        v-if="areas.length"
        aria-labelledby="areas"
      >
        <SectionHeading
          id="areas"
          title="Growth by area"
        />
        <ul
          class="areas"
          data-testid="areas"
        >
          <li
            v-for="a in areas"
            :key="a.key"
          >
            <span class="aname">{{ a.label }}</span>
            <Sparkline
              v-if="a.series.length > 1"
              :points="a.series"
              :label="`${a.label} score over time`"
              :width="110"
              :height="26"
            />
            <span
              v-else
              class="muted small nowrap"
            >More history soon</span>
            <span class="tabular small"><strong>{{ a.now }}</strong> <span class="muted">/ {{ a.target }} needed</span></span>
          </li>
        </ul>
      </section>

      <div class="two">
        <section aria-labelledby="rev">
          <SectionHeading
            id="rev"
            title="Revision health"
          >
            <RouterLink :to="{ name: 'revision' }">
              Open revision
            </RouterLink>
          </SectionHeading>
          <div
            v-if="revision.data"
            class="card-quiet health"
            data-testid="revision-health"
          >
            <p class="chips">
              <StatusPill
                v-if="counts.overdue"
                state="overdue"
                :label="`${counts.overdue} overdue`"
              />
              <StatusPill
                v-if="counts.due"
                state="due"
                :label="`${counts.due} due`"
              />
              <StatusPill
                v-if="counts.graduated"
                state="completed"
                :label="`${counts.graduated} graduated`"
              />
              <span
                v-if="!counts.overdue && !counts.due && !counts.graduated"
                class="muted small"
              >No reviews scheduled yet.</span>
            </p>
            <p class="small muted">
              {{ formatMinutes(revision.data.backlog_minutes) }} waiting · a comfortable day is {{ formatMinutes(revision.data.cap_minutes) }}
            </p>
            <ProgressBar
              :value="revision.data.backlog_minutes"
              :max="revision.data.triage_threshold_minutes"
              label="Review backlog"
              :tone="revision.data.backlog_minutes > revision.data.cap_minutes ? 'high' : 'healthy'"
              size="sm"
            />
          </div>
        </section>

        <section aria-labelledby="mocktrend">
          <SectionHeading
            id="mocktrend"
            title="Mock trend"
          >
            <RouterLink :to="{ name: 'mocks' }">
              Open mocks
            </RouterLink>
          </SectionHeading>
          <ul
            v-if="mockTypes.length"
            class="card-quiet mocklist"
          >
            <li
              v-for="t in mockTypes"
              :key="t.round_type"
            >
              <span>{{ ROUND_LABEL[t.round_type] ?? t.round_type }}</span>
              <Sparkline
                v-if="t.trend.length > 1"
                :points="t.trend.map((p) => p.score)"
                :label="`${t.round_type} mock scores over time`"
                :width="90"
                :height="24"
              />
              <strong class="tabular">{{ t.latest?.score }}</strong>
            </li>
          </ul>
          <p
            v-else
            class="quiet"
          >
            No mocks yet. Your scores will chart here.
          </p>
        </section>
      </div>

      <section aria-labelledby="rhythm">
        <SectionHeading
          id="rhythm"
          title="Weekly consistency"
        />
        <ul
          v-if="weeks.length"
          class="weeks card-quiet"
          data-testid="weeks"
        >
          <li
            v-for="w in weeks"
            :key="w.week_start"
          >
            <span
              class="column"
              role="img"
              :aria-label="`${plural(w.metrics.active_days, 'active day')} in the week of ${shortDate(w.week_start)}`"
            >
              <span
                class="fill"
                :style="{ height: `${(w.metrics.active_days / 7) * 100}%` }"
              />
            </span>
            <span class="wk small">{{ shortDate(w.week_start) }}</span>
            <span class="muted small tabular">{{ w.metrics.active_days }}/7</span>
          </li>
        </ul>
        <p
          v-else
          class="quiet"
        >
          Your weekly rhythm appears after your first full week.
        </p>
      </section>

      <section v-if="eased.length">
        <SectionHeading title="Gaps that are shrinking" />
        <ul class="eased card-quiet divided">
          <li
            v-for="g in eased"
            :key="g.skill_key"
          >
            <RouterLink :to="{ name: 'skill', params: { key: g.skill_key } }">
              {{ skills.nameOf(g.skill_key) }}
            </RouterLink>
            <span class="muted small">less of a gap than a week ago</span>
          </li>
        </ul>
      </section>

      <details class="advanced">
        <summary>Readiness checks in detail</summary>
        <ul
          class="gates"
          data-testid="gates"
        >
          <li
            v-for="g in r.gates"
            :key="g.gate"
          >
            <Icon
              :name="g.passed ? 'check-circle' : 'circle'"
              :size="14"
              :label="g.passed ? 'Passing' : 'Not passing'"
              :class="g.passed ? 'ok' : 'no'"
            />
            {{ GATE_NAMES[g.gate] ?? g.gate }}<span
              v-if="!g.passed"
              class="muted"
            > · {{ g.failing }} to go</span>
          </li>
        </ul>
      </details>
    </template>
    <CommunicationReadiness />
  </div>
</template>

<style scoped>
.hero { display: grid; grid-template-columns: 1fr 1.4fr; gap: var(--s-6); align-items: start; }
.state { font-size: var(--fs-2xl); font-weight: 700; letter-spacing: -0.025em; margin: var(--s-1) 0; }
.score { font-size: var(--fs-lg); color: var(--text-3); margin-top: var(--s-2); }
.score strong { color: var(--text); font-size: var(--fs-xl); }
.lapsed { display: flex; gap: var(--s-2); align-items: center; margin-top: var(--s-3); padding: var(--s-2) var(--s-3); background: var(--high-bg); color: var(--high-fg); border-radius: var(--r-md); font-size: var(--fs-sm); }
.small { font-size: var(--fs-sm); }
.nowrap { white-space: nowrap; }
.blockers li { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); }
.blockers li span { flex: 1; }
.blockers :deep(svg) { color: var(--calibration-fg); flex: none; }
.areas { display: grid; gap: var(--s-1); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); padding: var(--s-2) var(--s-4); }
.areas li { display: grid; grid-template-columns: minmax(0, 1fr) 8.5rem 9.5rem; align-items: center; gap: var(--s-4); padding: var(--s-3) 0; }
.areas li + li { border-top: 1px solid var(--border); }
.aname { font-weight: 600; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-6); }
.health { display: grid; gap: var(--s-3); }
.chips { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.mocklist { display: grid; gap: var(--s-3); }
.mocklist li { display: grid; grid-template-columns: minmax(0, 1fr) auto 2.5rem; align-items: center; gap: var(--s-3); }
.mocklist strong { text-align: right; }
.weeks { display: flex; gap: var(--s-4); align-items: flex-end; overflow-x: auto; padding: var(--s-5); }
.weeks li { display: grid; justify-items: center; gap: var(--s-1); min-width: 3rem; }
.column { display: flex; align-items: flex-end; width: 1.6rem; height: 5rem; background: var(--surface-3); border-radius: var(--r-sm); overflow: hidden; }
.fill { display: block; width: 100%; background: var(--accent); border-radius: var(--r-sm); transition: height 600ms var(--ease); }
.eased li { display: flex; justify-content: space-between; gap: var(--s-3); padding: var(--s-3) var(--s-4); flex-wrap: wrap; }
.quiet { padding: var(--s-4); background: var(--surface); border: 1px dashed var(--border-strong); border-radius: var(--r-md); color: var(--text-2); }
.advanced { font-size: var(--fs-sm); color: var(--text-2); }
.advanced summary { cursor: pointer; color: var(--text-3); }
.gates { display: grid; grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr)); gap: var(--s-2) var(--s-4); margin-top: var(--s-3); }
.gates li { display: flex; align-items: center; gap: var(--s-2); }
.ok { color: var(--healthy-fg); }
.no { color: var(--text-3); }
@media (max-width: 1099px) { .hero, .two { grid-template-columns: 1fr; } }
@media (max-width: 767px) { .areas li { grid-template-columns: minmax(0, 1fr) auto; } .areas li :deep(svg) { display: none; } }
</style>

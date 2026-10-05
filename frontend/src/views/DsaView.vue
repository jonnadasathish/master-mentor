<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import ErrorState from '../components/common/ErrorState.vue'
import EmptyState from '../components/common/EmptyState.vue'
import Icon from '../components/common/Icon.vue'
import PageHeader from '../components/common/PageHeader.vue'
import ProgressBar from '../components/common/ProgressBar.vue'
import SectionHeading from '../components/common/SectionHeading.vue'
import Skeleton from '../components/common/Skeleton.vue'
import StatusPill from '../components/common/StatusPill.vue'
import GapList from '../components/skills/GapList.vue'
import { formatMinutes, shortDate } from '../presentation/format'
import { missionText } from '../presentation/mission'
import { stateFromGapStatus } from '../presentation/language'
import { summarizeCategory } from '../presentation/prepare'
import CurriculumSection from '../components/learning/CurriculumSection.vue'
import { PREPARE_CATEGORIES } from '../presentation/language'
import { outcomeLabel } from '../practice/vocabulary'
import {
  useAttemptsStore, useCatalogSkillsStore, useProblemsStore, useReadinessStore, useRevisionStore, useSkillsStore, useTodayStore,
} from '../stores/data'

/** DSA home: today's DSA work, weak patterns, recent attempts, reviews due and progress by pattern. */
const skills = useSkillsStore()
const readiness = useReadinessStore()
const today = useTodayStore()
const attempts = useAttemptsStore()
const revision = useRevisionStore()
const catalog = useCatalogSkillsStore()
const problems = useProblemsStore()

const category = PREPARE_CATEGORIES[0]
const loaded = computed(() => skills.data !== null && readiness.data !== null)
const error = computed(() => skills.error ?? readiness.error ?? today.error)
const summary = computed(() => summarizeCategory(category, skills.list, readiness.data))
const dsaKeys = computed(() => new Set(skills.list.filter((s) => ['dsa', 'coding'].includes(s.component)).map((s) => s.key)))

const weakPatterns = computed(() =>
  summary.value.gaps.slice(0, 5).map((s) => ({
    skill_key: s.key,
    status: s.gap!.status,
    priority: s.gap!.priority,
    primary_gap_type: s.gap!.primary_gap_type,
    focus_stage: s.gap!.focus_stage,
    reason_codes: s.gap!.reason_codes,
  })),
)
const todayItems = computed(() =>
  (today.data?.plan.items ?? []).filter(
    (i) => i.problems.length > 0 || (i.skill !== null && dsaKeys.value.has(i.skill)),
  ),
)
const reviews = computed(() =>
  (revision.data?.items ?? []).filter(
    (i) => dsaKeys.value.has(i.skill) && (i.bucket === 'overdue' || i.bucket === 'due'),
  ),
)
const patterns = computed(() => {
  const isPattern = new Set(catalog.data?.filter((c) => c.is_pattern && c.component === 'dsa').map((c) => c.key) ?? [])
  return skills.list
    .filter((s) => isPattern.has(s.key))
    .sort((a, b) => (a.gap?.rank ?? 9999) - (b.gap?.rank ?? 9999) || a.name.localeCompare(b.name))
    .slice(0, 8)
})
const ctx = computed(() => ({ nameOf: skills.nameOf, componentOf: skills.componentOf, battery: today.baseline.data?.items ?? [] }))
const TONE = { critical: 'critical', high: 'high', medium: 'medium', healthy: 'healthy', calibration: 'calibration' } as const

async function load(): Promise<void> {
  await Promise.all([skills.refresh(), readiness.refresh(), today.refresh()])
}
onMounted(() =>
  Promise.all([
    skills.ensure(), readiness.ensure(), today.ensure(), attempts.ensure(), revision.ensure(), catalog.ensure(),
    problems.ensure(), today.baseline.ensure(),
  ]),
)
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="Prepare"
      title="DSA"
    >
      <RouterLink
        :to="{ name: 'problems' }"
        class="btn btn-primary"
        data-testid="browse-problems"
      >
        <Icon
          name="search"
          :size="16"
        /> Browse problems
      </RouterLink>
    </PageHeader>

    <div
      v-if="!loaded && !error"
      class="stack"
      aria-busy="true"
    >
      <Skeleton
        height="7rem"
        radius="var(--r-lg)"
      />
      <Skeleton
        height="12rem"
        radius="var(--r-lg)"
      />
    </div>
    <ErrorState
      v-else-if="error"
      :error="error"
      @retry="load"
    />

    <template v-else>
      <section class="summary card">
        <div>
          <p class="eyebrow">
            Where you are
          </p>
          <p
            v-if="summary.assessedPct"
            class="score tabular"
          >
            <strong>{{ summary.score }}</strong><span class="of"> / {{ summary.target }} needed</span>
          </p>
          <p
            v-else
            class="score muted"
          >
            Not measured yet
          </p>
          <ProgressBar
            v-if="summary.assessedPct"
            :value="summary.score"
            :max="summary.target"
            label="DSA score against the level you're aiming for"
          />
        </div>
        <div>
          <p class="eyebrow">
            Next best step
          </p>
          <p class="next-title">
            {{ summary.nextLabel ?? 'Nothing urgent. Keep your reviews up.' }}
          </p>
        </div>
      </section>

      <section aria-labelledby="dsa-today">
        <SectionHeading
          id="dsa-today"
          title="Today's DSA missions"
        >
          <RouterLink :to="{ name: 'today' }">
            Open Today
          </RouterLink>
        </SectionHeading>
        <ul
          v-if="todayItems.length"
          class="list card-quiet divided"
          data-testid="dsa-today"
        >
          <li
            v-for="i in todayItems"
            :key="i.id"
          >
            <span class="title">{{ missionText(i, ctx).title }}</span>
            <span class="muted tabular">{{ formatMinutes(i.minutes) }}</span>
            <StatusPill
              v-if="i.status === 'DONE'"
              state="completed"
            />
            <StatusPill
              v-else
              state="due"
              label="To do"
            />
          </li>
        </ul>
        <p
          v-else
          class="quiet"
        >
          No DSA mission today. Browse problems any time to practise.
        </p>
      </section>

      <section aria-labelledby="dsa-weak">
        <SectionHeading
          id="dsa-weak"
          title="Weak spots"
        />
        <GapList
          v-if="weakPatterns.length"
          :gaps="weakPatterns"
        />
        <EmptyState
          v-else
          icon="check-circle"
          title="Nothing critical right now."
          body="No DSA skill needs urgent attention."
        />
      </section>

      <div class="two">
        <section aria-labelledby="dsa-recent">
          <SectionHeading
            id="dsa-recent"
            title="Recent attempts"
          />
          <ul
            v-if="attempts.data?.length"
            class="list card-quiet divided"
            data-testid="recent-attempts"
          >
            <li
              v-for="a in attempts.data"
              :key="a.id"
            >
              <RouterLink
                :to="{ name: 'attempt', params: { id: a.id } }"
                class="title"
              >
                {{ a.problem.title }}
              </RouterLink>
              <span class="muted small">{{ shortDate(a.attempted_on) }}</span>
              <StatusPill
                :state="a.outcome === 'PASS' ? 'healthy' : a.outcome === 'PARTIAL' ? 'medium' : 'critical'"
                :label="outcomeLabel(a.outcome)"
              />
            </li>
          </ul>
          <EmptyState
            v-else
            icon="code"
            title="No attempts yet."
            body="Your first problem attempt shows up here."
          />
        </section>

        <section aria-labelledby="dsa-reviews">
          <SectionHeading
            id="dsa-reviews"
            title="Reviews waiting"
          >
            <RouterLink :to="{ name: 'revision' }">
              Open revision
            </RouterLink>
          </SectionHeading>
          <ul
            v-if="reviews.length"
            class="list card-quiet divided"
          >
            <li
              v-for="r in reviews"
              :key="r.item_key"
            >
              <span class="title">{{ r.item_type === 'PROBLEM' ? (problems.titleOf(r.subject_ref) ?? r.skill_name) : r.skill_name }}</span>
              <span class="muted small">{{ formatMinutes(r.minutes) }}</span>
              <StatusPill
                :state="r.bucket === 'overdue' ? 'overdue' : 'due'"
              />
            </li>
          </ul>
          <p
            v-else
            class="quiet"
          >
            <Icon
              name="check-circle"
              :size="16"
            /> You're clear for today.
          </p>
        </section>
      </div>

      <section
        v-if="patterns.length"
        aria-labelledby="dsa-patterns"
      >
        <SectionHeading
          id="dsa-patterns"
          title="Progress by pattern"
        />
        <ul
          class="patterns card-quiet"
          data-testid="patterns"
        >
          <li
            v-for="p in patterns"
            :key="p.key"
          >
            <RouterLink
              :to="{ name: 'skill', params: { key: p.key } }"
              class="name"
            >
              {{ p.name }}
            </RouterLink>
            <ProgressBar
              :value="p.state.effective_score"
              :max="p.target_score"
              :label="`${p.name} progress`"
              size="sm"
              :tone="TONE[stateFromGapStatus(p.gap?.status ?? 'UNASSESSED') as keyof typeof TONE] ?? 'accent'"
            />
            <span class="tabular small muted">{{ p.state.effective_score ?? '—' }} / {{ p.target_score ?? '—' }}</span>
          </li>
        </ul>
      </section>
      <CurriculumSection track="dsa" />
    </template>
  </div>
</template>

<style scoped>
.summary { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-6); }
.score { font-size: var(--fs-2xl); letter-spacing: -0.02em; margin: var(--s-1) 0 var(--s-2); }
.score strong { font-weight: 700; }
.of { font-size: var(--fs-md); color: var(--text-3); font-weight: 500; }
.next-title { font-size: var(--fs-lg); font-weight: 650; letter-spacing: -0.01em; margin-top: var(--s-1); }
.list li { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-2); }
.list .title { flex: 1; font-weight: 560; color: var(--text); min-width: 0; overflow: hidden; text-overflow: ellipsis; }
.small { font-size: var(--fs-sm); }
.quiet { display: flex; align-items: center; gap: var(--s-2); padding: var(--s-4); background: var(--surface); border: 1px dashed var(--border-strong); border-radius: var(--r-md); color: var(--text-2); }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-6); }
.patterns { display: grid; gap: var(--s-3); padding: var(--s-4) var(--s-5); }
.patterns li { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(5rem, 1fr) 4.5rem; align-items: center; gap: var(--s-4); }
.name { font-weight: 560; color: var(--text); }
@media (max-width: 1099px) { .two { grid-template-columns: 1fr; } }
@media (max-width: 767px) { .summary { grid-template-columns: 1fr; gap: var(--s-5); } .patterns li { grid-template-columns: minmax(0, 1fr) auto; } .patterns li :deep(.bar) { grid-column: 1 / -1; order: 3; } }
</style>

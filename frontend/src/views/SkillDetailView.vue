<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { api } from '../api'
import { ApiError } from '../api/client'
import type { GapDetail, LearningTab, SkillLearning, SkillStateDetail } from '../api/types'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import Icon from '../components/common/Icon.vue'
import ProgressBar from '../components/common/ProgressBar.vue'
import SectionHeading from '../components/common/SectionHeading.vue'
import Skeleton from '../components/common/Skeleton.vue'
import StatusPill from '../components/common/StatusPill.vue'
import ContentList from '../components/learning/ContentList.vue'
import { openSession } from '../learning/session'
import { formatMinutes, shortDate } from '../presentation/format'
import {
  CONTENT_TYPE_LABEL, COVERAGE_LABEL, COVERAGE_TONE, NEXT_REASON_TEXT, PRACTICE_CASE_TEXT, PRACTICE_STATE_LABEL,
  PRACTICE_STATE_TONE, RELATION_TEXT, TAB_EMPTY, TAB_LABEL,
} from '../presentation/learning'
import {
  COMPONENT_LABEL, CONFIDENCE_LABEL, GAP_TYPE_LABEL, REVIEW_KIND_LABEL, ROUND_LABEL, STAGE_LABEL, TRACK_OF_SLUG, prepareRoute, stateFromGapStatus,
} from '../presentation/language'
import { recordLabel } from '../presentation/mission'
import { evidenceDetail, evidenceTitle, whyWeak } from '../presentation/skill'
import { tidyCriteria } from '../presentation/text'
import { useGapDetailStore, useSkillsStore } from '../stores/data'

/** A skill, explained: where you are, why, what it depends on, the evidence, and the next best action. */
const route = useRoute()
const router = useRouter()
const skills = useSkillsStore()
const learning = ref<SkillLearning | null>(null)
const tab = ref<LearningTab>('learn')
const TABS: LearningTab[] = ['learn', 'practice', 'test', 'revision']
const sessionError = ref('')
const starting = ref(false)
const gapStore = useGapDetailStore()
const skill = ref<SkillStateDetail | null>(null)
const gap = ref<GapDetail | null>(null)
const error = ref<unknown>(null)
const showAllEvidence = ref(false)

const key = computed(() => String(route.params.key))
const score = computed(() => skill.value?.state.effective_score ?? skill.value?.state.score ?? null)
const status = computed(() => skill.value?.gap?.status ?? 'UNASSESSED')
const reasons = computed(() => (gap.value ? whyWeak(gap.value, skills.nameOf) : []))
const evidence = computed(() => {
  const rows = skill.value?.evidence ?? []
  return showAllEvidence.value ? rows : rows.slice(0, 6)
})
const focus = computed(() => skill.value?.focus ?? null)
const component = computed(() => COMPONENT_LABEL[skill.value?.component ?? ''] ?? '')
const isCodingSkill = computed(() => ['dsa', 'coding'].includes(skill.value?.component ?? ''))
const hasDirectProblems = computed(() => learning.value === null || (learning.value.practice.direct.length ?? 0) > 0)
/** Self-logging is always possible; a coding skill without its own problems is never sent to an empty list. */
const startTo = computed(() =>
  isCodingSkill.value && hasDirectProblems.value
    ? { name: 'problems', query: { skill: key.value } }
    : { name: 'log', query: { skill: key.value, kind: focus.value?.observation_kind ?? '' } },
)
const next = computed(() => learning.value?.next_action ?? null)
const tabCount = (t: LearningTab) =>
  (learning.value?.tabs[t].length ?? 0) +
  (t === 'practice' ? (learning.value?.practice.direct.length ?? 0) + (learning.value?.practice.related.length ?? 0) : 0)
const practice = computed(() => learning.value?.practice ?? null)
const why = computed(() => learning.value?.why_it_matters ?? null)
const roundsText = computed(() => (why.value?.rounds ?? []).map((r) => ROUND_LABEL[r] ?? r).join(', '))
const relatedSkills = computed(() => (learning.value?.related_skills ?? []).filter((r) => r.relation !== 'PREREQUISITE'))

async function startSession(): Promise<void> {
  if (!next.value) return
  sessionError.value = ''
  starting.value = true
  try {
    if (next.value.kind === 'RESUME_SESSION' && next.value.session_id !== null) {
      await router.push({ name: 'session', params: { id: next.value.session_id } })
    } else {
      await openSession(router, { skill: key.value, stage: next.value.stage })
    }
  } catch (caught) {
    sessionError.value = caught instanceof ApiError ? caught.message : String(caught)
  } finally {
    starting.value = false
  }
}
const nextTitle = computed(() => {
  const f = focus.value
  const g = skill.value?.gap
  if (!f) return null
  const target = g?.focus_skill && g.focus_skill !== key.value ? skills.nameOf(g.focus_skill) : (skill.value?.name ?? '')
  return `${STAGE_LABEL[f.stage] ?? f.stage}: ${target}`
})
const prereqs = computed(() => skill.value?.prerequisites ?? [])
const trackTo = (track: string) =>
  prepareRoute(Object.entries(TRACK_OF_SLUG).find(([, t]) => t === track)?.[0] ?? '')

async function load(): Promise<void> {
  error.value = null
  skill.value = null
  gap.value = null
  learning.value = null
  try {
    skill.value = (await api.get<SkillStateDetail>(`/skills/${encodeURIComponent(key.value)}`)).data
  } catch (caught) {
    error.value = caught
    return
  }
  const [gapResult, learningResult] = await Promise.allSettled([
    gapStore.load(key.value),
    api.get<SkillLearning>(`/skills/${encodeURIComponent(key.value)}/learning`),
  ])
  // Both are optional: the rest of the page works without the gap explanation or the learning layer.
  gap.value = gapResult.status === 'fulfilled' ? gapResult.value : null
  learning.value = learningResult.status === 'fulfilled' ? learningResult.value.data : null
  if (learning.value) {
    const first = TABS.find((t) => tabCount(t) > 0)
    tab.value = learning.value.practice.case === 'UNCOVERED' ? 'practice' : (first ?? 'learn')
  }
}

onMounted(async () => {
  await Promise.all([skills.ensure(), load()])
})
watch(key, load)
</script>

<template>
  <div class="page page-narrow">
    <Skeleton
      v-if="!skill && !error"
      height="18rem"
      radius="var(--r-lg)"
    />
    <ErrorState
      v-else-if="!skill"
      :error="error"
      @retry="load"
    />

    <template v-else>
      <RouterLink
        :to="{ name: 'prepare' }"
        class="back"
      >
        <Icon
          name="arrow-left"
          :size="14"
        /> Prepare
      </RouterLink>

      <header class="head">
        <p class="eyebrow">
          {{ component }}
        </p>
        <h1 data-testid="skill-name">
          {{ skill.name }}
        </h1>
      </header>

      <section
        class="tiles"
        data-testid="skill-state"
      >
        <div class="tile">
          <p class="label">
            Score
          </p>
          <p class="value tabular">
            <strong>{{ score ?? '—' }}</strong><span class="of"> / {{ skill.target_score ?? '—' }}</span>
          </p>
          <ProgressBar
            :value="score"
            :max="skill.target_score"
            :label="`${skill.name} score against target`"
            size="sm"
            :tone="status === 'CRITICAL' ? 'critical' : status === 'HIGH' ? 'high' : status === 'NONE' ? 'healthy' : 'accent'"
          />
        </div>
        <div class="tile">
          <p class="label">
            Status
          </p>
          <p class="value">
            <StatusPill :state="stateFromGapStatus(status)" />
          </p>
        </div>
        <div class="tile">
          <p class="label">
            Confidence
          </p>
          <p class="value small-value">
            {{ CONFIDENCE_LABEL[skill.state.confidence] ?? skill.state.confidence }}
          </p>
        </div>
        <div class="tile">
          <p class="label">
            Evidence
          </p>
          <p class="value small-value">
            {{ skill.state.evidence_count }} {{ skill.state.evidence_count === 1 ? 'observation' : 'observations' }}
          </p>
        </div>
      </section>

      <p
        v-if="skill.state.declared_unknown"
        class="note"
      >
        <Icon
          name="info"
          :size="16"
        /> You told us this is new to you, so it counts as measured at 0 until you practise it.
      </p>
      <p
        v-if="skill.state.reality_capped"
        class="note"
      >
        <Icon
          name="info"
          :size="16"
        /> A recent mock interview result held this score down.
      </p>
      <p
        v-if="skill.gap?.parked_reason"
        class="note"
      >
        <Icon
          name="pause"
          :size="16"
        /> Parked: no missions for this until after your interview date. It still counts toward readiness.
      </p>

      <section
        v-if="why"
        class="why card-quiet"
        data-testid="why-it-matters"
        aria-labelledby="why-title"
      >
        <h2
          id="why-title"
          class="eyebrow"
        >
          Why this skill matters
        </h2>
        <p>
          <strong v-if="why.tier_label">{{ why.tier_label.charAt(0) + why.tier_label.slice(1).toLowerCase() }} for your target role</strong><template v-else>
            Optional for your target role
          </template><template v-if="why.target_score">
            · the bar is {{ why.target_score }}
          </template><template v-if="why.rounds.length">
            · tested in {{ roundsText }} rounds
          </template><template v-if="why.unlocks.length">
            · {{ why.unlocks.length }} {{ why.unlocks.length === 1 ? 'skill builds' : 'skills build' }} on it
          </template>
        </p>
        <p
          v-if="why.topic"
          class="muted small"
        >
          Part of <RouterLink :to="trackTo(why.topic.track)">
            {{ why.topic.title }}
          </RouterLink>
          <StatusPill
            v-if="learning"
            :state="COVERAGE_TONE[learning.coverage_state]"
            :label="COVERAGE_LABEL[learning.coverage_state]"
            quiet
          />
        </p>
      </section>

      <section
        v-if="reasons.length && !['NONE'].includes(status)"
        data-testid="skill-gap"
      >
        <SectionHeading title="Why this needs work" />
        <p
          v-if="skill.gap?.primary_gap_type"
          class="type"
        >
          <strong>{{ GAP_TYPE_LABEL[skill.gap.primary_gap_type] ?? skill.gap.primary_gap_type }}.</strong>
        </p>
        <ul class="bullets">
          <li
            v-for="line in reasons"
            :key="line"
          >
            {{ line }}
          </li>
        </ul>
      </section>

      <section
        v-if="focus"
        class="next"
        data-testid="skill-focus"
      >
        <p class="eyebrow">
          Next best action
        </p>
        <h2>{{ nextTitle }}</h2>
        <p class="muted">
          <template v-if="focus.minutes">
            {{ formatMinutes(focus.minutes) }} ·
          </template>
          <template v-if="focus.observation_kind">
            you'll record {{ recordLabel(focus.observation_kind) }}
          </template>
          <template v-if="focus.pass_rule">
            · done when {{ tidyCriteria(focus.pass_rule).toLowerCase() }}
          </template>
        </p>
        <div class="next-actions">
          <button
            v-if="next && (next.kind === 'START_SESSION' || next.kind === 'RESUME_SESSION')"
            type="button"
            class="btn btn-primary btn-lg"
            :disabled="starting"
            data-testid="start-session"
            @click="startSession"
          >
            <Icon
              name="play"
              :size="14"
            /> {{ next.kind === 'RESUME_SESSION' ? 'Continue the session' : 'Start a learning session' }}
          </button>
          <RouterLink
            :to="startTo"
            class="btn btn-lg"
            :class="{ 'btn-primary': !next || (next.kind !== 'START_SESSION' && next.kind !== 'RESUME_SESSION') }"
            data-testid="start-practice"
          >
            <Icon
              :name="next && (next.kind === 'START_SESSION' || next.kind === 'RESUME_SESSION') ? 'plus' : 'play'"
              :size="14"
            /> {{ next && (next.kind === 'START_SESSION' || next.kind === 'RESUME_SESSION') ? 'Log practice yourself' : 'Start' }}
          </RouterLink>
        </div>
        <p
          v-if="sessionError"
          class="error small"
          role="alert"
        >
          {{ sessionError }}
        </p>
      </section>

      <section
        v-if="next && next.kind !== 'NONE'"
        class="plan card-quiet"
        data-testid="next-action"
      >
        <p class="muted small">
          {{ NEXT_REASON_TEXT[next.reason] }}
        </p>
        <ol
          v-if="next.steps.length"
          class="preview"
        >
          <li
            v-for="s in next.steps"
            :key="s.position"
          >
            <span class="tabular muted">{{ s.position }}.</span>
            {{ s.title }}
            <span class="muted small">{{ s.kind === 'REFLECTION' ? 'reflection' : s.kind === 'PROBLEM' ? 'problem' : CONTENT_TYPE_LABEL[s.content_type ?? 'lesson'].toLowerCase() }} · {{ formatMinutes(s.minutes) }}</span>
          </li>
        </ol>
        <p v-if="next.kind === 'FALLBACK' && next.fallback_skill">
          <RouterLink
            :to="{ name: 'skill', params: { key: next.fallback_skill } }"
            data-testid="prerequisite-first"
          >
            Start with {{ skills.nameOf(next.fallback_skill) }}
          </RouterLink>
        </p>
      </section>

      <section
        v-if="learning"
        class="learning"
        data-testid="skill-learning"
      >
        <div
          class="tabs"
          role="tablist"
          aria-label="Learning for this skill"
        >
          <button
            v-for="t in TABS"
            :id="`tab-${t}`"
            :key="t"
            type="button"
            class="tab"
            role="tab"
            :aria-selected="tab === t"
            :aria-controls="`panel-${t}`"
            :data-testid="`tab-${t}`"
            @click="tab = t"
          >
            {{ TAB_LABEL[t] }} <span class="count">{{ tabCount(t) }}</span>
          </button>
        </div>
        <div
          :id="`panel-${tab}`"
          role="tabpanel"
          :aria-labelledby="`tab-${tab}`"
          class="panel"
        >
          <template v-if="tab === 'practice' && practice">
            <p
              class="case"
              :data-case="practice.case"
              data-testid="practice-case"
            >
              <Icon
                :name="practice.case === 'UNCOVERED' ? 'alert-triangle' : 'info'"
                :size="16"
              />
              {{ PRACTICE_CASE_TEXT[practice.case] }}
            </p>
            <ul
              v-if="practice.direct.length"
              class="problems card-quiet divided"
              data-testid="direct-problems"
            >
              <li
                v-for="p in practice.direct"
                :key="p.id"
              >
                <RouterLink
                  :to="{ name: 'problem', params: { problemKey: p.key.split(':').slice(1).join(':') } }"
                  class="ptitle"
                >
                  {{ p.title }}
                </RouterLink>
                <span class="muted small">{{ p.difficulty.toLowerCase() }}</span>
                <StatusPill
                  :state="PRACTICE_STATE_TONE[p.practice_state]"
                  :label="PRACTICE_STATE_LABEL[p.practice_state]"
                  quiet
                />
              </li>
            </ul>
            <ul
              v-if="practice.related.length"
              class="problems card-quiet divided"
              data-testid="related-problems"
            >
              <li
                v-for="r in practice.related"
                :key="r.problem.id"
              >
                <RouterLink
                  :to="{ name: 'problem', params: { problemKey: r.problem.key.split(':').slice(1).join(':') } }"
                  class="ptitle"
                >
                  {{ r.problem.title }}
                </RouterLink>
                <span class="muted small">via {{ r.via_name }} ({{ RELATION_TEXT[r.relation] }})</span>
                <StatusPill
                  :state="PRACTICE_STATE_TONE[r.problem.practice_state]"
                  :label="PRACTICE_STATE_LABEL[r.problem.practice_state]"
                  quiet
                />
              </li>
            </ul>
            <div
              v-if="practice.case === 'UNCOVERED'"
              class="gap-note"
              data-testid="content-gap"
            >
              <p v-if="practice.fallback_skill">
                Meanwhile, practise
                <RouterLink :to="{ name: 'skill', params: { key: practice.fallback_skill } }">
                  {{ practice.fallback_name }}
                </RouterLink>
                ({{ RELATION_TEXT[practice.fallback_relation ?? 'SAME_GROUP'] }}), or record your own practice.
              </p>
              <p v-else>
                Record your own practice for it; the mentor still counts it.
              </p>
              <RouterLink
                :to="{ name: 'log', query: { skill: key } }"
                class="btn"
              >
                Log practice
              </RouterLink>
            </div>
          </template>
          <ContentList
            v-if="learning.tabs[tab].length"
            :items="learning.tabs[tab]"
            :testid="`content-${tab}`"
          />
          <EmptyState
            v-else-if="tab !== 'practice' || practice?.case === 'CONCEPT'"
            icon="book"
            :title="TAB_EMPTY[tab]"
            body="The other tabs, and logging your own practice, still count."
          />
        </div>
      </section>

      <section v-if="prereqs.length">
        <SectionHeading title="Prerequisites" />
        <ul class="prereqs card-quiet divided">
          <li
            v-for="p in prereqs"
            :key="p.skill"
          >
            <Icon
              :name="p.satisfied ? 'check-circle' : 'alert-triangle'"
              :size="16"
              :class="p.satisfied ? 'ok' : 'warn'"
              :label="p.satisfied ? 'Ready' : 'Needs work'"
            />
            <RouterLink
              :to="{ name: 'skill', params: { key: p.skill } }"
              class="pname"
            >
              {{ skills.nameOf(p.skill) }}
            </RouterLink>
            <span
              v-if="!p.satisfied"
              class="muted small"
            >needs {{ p.min_score }}, you're at {{ p.effective_score ?? 'not measured yet' }}</span>
          </li>
        </ul>
      </section>

      <section>
        <SectionHeading title="Recent evidence">
          <button
            v-if="skill.evidence.length > 6"
            type="button"
            class="link-btn"
            @click="showAllEvidence = !showAllEvidence"
          >
            {{ showAllEvidence ? 'Show fewer' : `Show all ${skill.evidence.length}` }}
          </button>
        </SectionHeading>
        <EmptyState
          v-if="!skill.evidence.length"
          icon="search"
          title="No evidence yet."
          body="Practice this skill and every observation shows up here."
        />
        <ol
          v-else
          class="timeline card-quiet"
          data-testid="evidence-table"
        >
          <li
            v-for="e in evidence"
            :key="`${e.source_type}-${e.source_id}`"
          >
            <span class="dot" />
            <div>
              <p class="t">
                <RouterLink
                  v-if="e.source_type === 'ATTEMPT'"
                  :to="{ name: 'attempt', params: { id: e.source_id } }"
                >
                  {{ evidenceTitle(e) }}
                </RouterLink>
                <template v-else>
                  {{ evidenceTitle(e) }}
                </template>
              </p>
              <p class="muted small">
                {{ shortDate(e.observed_on) }}<template v-if="evidenceDetail(e)">
                  · {{ evidenceDetail(e) }}
                </template>
              </p>
            </div>
          </li>
        </ol>
      </section>

      <section v-if="skill.revision_items.length">
        <SectionHeading title="Scheduled reviews">
          <RouterLink :to="{ name: 'revision' }">
            Open revision
          </RouterLink>
        </SectionHeading>
        <ul
          class="bullets"
          data-testid="skill-revisions"
        >
          <li
            v-for="r in skill.revision_items"
            :key="r.item_key"
          >
            <template v-if="r.state === 'ACTIVE'">
              {{ REVIEW_KIND_LABEL[r.item_type] ?? 'Review' }} due {{ r.due_date ? shortDate(r.due_date) : 'soon' }}
            </template>
            <template v-else-if="r.state === 'GRADUATED'">
              Graduated: no more reviews
            </template>
            <template v-else>
              Paused
            </template>
            <span
              v-if="r.lapses"
              class="muted"
            > · slipped {{ r.lapses }} {{ r.lapses === 1 ? 'time' : 'times' }}</span>
          </li>
        </ul>
      </section>

      <section v-if="relatedSkills.some((r) => r.relation === 'SAME_TOPIC')">
        <SectionHeading title="Same topic" />
        <p class="chips">
          <RouterLink
            v-for="r in relatedSkills.filter((x) => x.relation === 'SAME_TOPIC')"
            :key="r.key"
            :to="{ name: 'skill', params: { key: r.key } }"
            class="chip"
          >
            {{ r.name }}
          </RouterLink>
        </p>
      </section>

      <section v-if="skill.dependents.length">
        <SectionHeading title="This unlocks" />
        <p class="chips">
          <RouterLink
            v-for="d in skill.dependents"
            :key="d"
            :to="{ name: 'skill', params: { key: d } }"
            class="chip"
          >
            {{ skills.nameOf(d) }}
          </RouterLink>
        </p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.back { display: inline-flex; align-items: center; gap: var(--s-1); font-size: var(--fs-sm); color: var(--text-3); width: fit-content; }
.head { display: grid; gap: var(--s-1); }
h1 { font-size: var(--fs-2xl); text-wrap: balance; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)); gap: var(--s-3); }
.tile { display: grid; gap: var(--s-2); align-content: start; padding: var(--s-4); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); }
.label { font-size: var(--fs-xs); font-weight: 650; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-3); }
.value { font-size: var(--fs-xl); letter-spacing: -0.02em; }
.value strong { font-weight: 700; }
.of { font-size: var(--fs-md); color: var(--text-3); font-weight: 500; }
.small-value { font-size: var(--fs-md); font-weight: 650; }
.note { display: flex; align-items: flex-start; gap: var(--s-2); padding: var(--s-3) var(--s-4); background: var(--calibration-bg); color: var(--text); border-radius: var(--r-md); font-size: var(--fs-sm); }
.note :deep(svg) { margin-top: 0.15rem; color: var(--calibration-fg); }
.type { margin-bottom: var(--s-2); }
.bullets { display: grid; gap: var(--s-2); padding-left: var(--s-5); list-style: disc; }
.bullets li::marker { color: var(--text-3); }
.next { display: grid; gap: var(--s-2); padding: var(--s-5); background: var(--accent-soft); border: 1px solid var(--accent-border); border-radius: var(--r-lg); }
.next .eyebrow { color: var(--accent-text); }
.next-actions { display: flex; gap: var(--s-2); flex-wrap: wrap; margin-top: var(--s-2); }
.why { display: grid; gap: var(--s-2); }
.plan { display: grid; gap: var(--s-2); }
.preview { display: grid; gap: var(--s-1); }
.preview li { display: flex; gap: var(--s-2); flex-wrap: wrap; align-items: baseline; }
.learning { display: grid; gap: var(--s-4); }
.tab .count { margin-left: var(--s-1); font-size: var(--fs-xs); color: var(--text-3); font-variant-numeric: tabular-nums; }
.panel { display: grid; gap: var(--s-3); }
.case { display: flex; gap: var(--s-2); align-items: flex-start; color: var(--text-2); font-size: var(--fs-sm); }
.case :deep(svg) { margin-top: 0.15rem; flex: none; }
.case[data-case='UNCOVERED'] { color: var(--high-fg); }
.problems li { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); flex-wrap: wrap; }
.ptitle { font-weight: 600; flex: 1 1 12rem; }
.gap-note { display: grid; gap: var(--s-2); justify-items: start; padding: var(--s-4); border: 1px dashed var(--border-strong); border-radius: var(--r-md); }
.error { color: var(--critical-fg); }
.prereqs li { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); }
.pname { font-weight: 600; }
.small { font-size: var(--fs-sm); }
.ok { color: var(--healthy-fg); }
.warn { color: var(--high-fg); }
.timeline { display: grid; gap: var(--s-4); padding: var(--s-5); position: relative; }
.timeline li { display: grid; grid-template-columns: 0.9rem 1fr; gap: var(--s-3); align-items: start; }
.dot { width: 0.65rem; height: 0.65rem; border-radius: 50%; background: var(--accent); margin-top: 0.4rem; box-shadow: 0 0 0 3px var(--accent-soft); }
.t { font-weight: 600; }
.chips { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.chip { padding: 0.25rem 0.8rem; border-radius: 999px; background: var(--surface); border: 1px solid var(--border-strong); font-size: var(--fs-sm); color: var(--text); }
.chip:hover { text-decoration: none; background: var(--surface-2); }
</style>

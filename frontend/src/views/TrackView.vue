<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import Icon from '../components/common/Icon.vue'
import PageHeader from '../components/common/PageHeader.vue'
import ProgressBar from '../components/common/ProgressBar.vue'
import SectionHeading from '../components/common/SectionHeading.vue'
import Skeleton from '../components/common/Skeleton.vue'
import CurriculumSection from '../components/learning/CurriculumSection.vue'
import GapList from '../components/skills/GapList.vue'
import SkillRow from '../components/skills/SkillRow.vue'
import { PREPARE_CATEGORIES, STAGE_LABEL, TRACK_OF_SLUG } from '../presentation/language'
import { skillsInCategory, summarizeCategory } from '../presentation/prepare'
import { useReadinessStore, useSkillsStore } from '../stores/data'

/** One preparation area (CS, System Design, LLD, Behavioral): where you are, what matters, what's next. */
const route = useRoute()
const skills = useSkillsStore()
const readiness = useReadinessStore()
const showAll = ref(false)

const category = computed(() => PREPARE_CATEGORIES.find((c) => c.slug === route.params.slug) ?? PREPARE_CATEGORIES[1])
const track = computed(() => TRACK_OF_SLUG[category.value.slug] ?? 'cs')
const loaded = computed(() => skills.data !== null && readiness.data !== null)
const error = computed(() => skills.error ?? readiness.error)
const summary = computed(() => summarizeCategory(category.value, skills.list, readiness.data))
const all = computed(() =>
  skillsInCategory(category.value, skills.list).sort(
    (a, b) => (a.gap?.rank ?? 9999) - (b.gap?.rank ?? 9999) || a.name.localeCompare(b.name),
  ),
)
const focusGaps = computed(() =>
  summary.value.gaps.slice(0, 4).map((s) => ({
    skill_key: s.key,
    status: s.gap!.status,
    priority: s.gap!.priority,
    primary_gap_type: s.gap!.primary_gap_type,
    focus_stage: s.gap!.focus_stage,
    reason_codes: s.gap!.reason_codes,
  })),
)
const measured = computed(() => summary.value.assessedPct !== null && summary.value.assessedPct > 0)

async function load(): Promise<void> {
  await Promise.all([skills.refresh(), readiness.refresh()])
}
onMounted(() => Promise.all([skills.ensure(), readiness.ensure()]))
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="Prepare"
      :title="category.label"
    >
      <RouterLink
        :to="{ name: 'log' }"
        class="btn"
      >
        <Icon
          name="plus"
          :size="16"
        /> Log practice
      </RouterLink>
    </PageHeader>

    <div
      v-if="!loaded && !error"
      class="stack"
      aria-busy="true"
    >
      <Skeleton
        height="8rem"
        radius="var(--r-lg)"
      />
      <Skeleton
        height="10rem"
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
          <template v-if="measured">
            <p class="score tabular">
              <strong>{{ summary.score }}</strong><span class="of"> / {{ summary.target }} needed</span>
            </p>
            <ProgressBar
              :value="summary.score"
              :max="summary.target"
              :label="`${category.label} score against the level you're aiming for`"
            />
          </template>
          <p
            v-else
            class="score muted"
          >
            Not measured yet
          </p>
        </div>
        <div class="next">
          <p class="eyebrow">
            Next best step
          </p>
          <template v-if="summary.topGap">
            <p class="next-title">
              {{ STAGE_LABEL[summary.topGap.gap?.focus_stage ?? ''] ?? 'Practice' }}: {{ summary.topGap.name }}
            </p>
            <RouterLink
              :to="{ name: 'skill', params: { key: summary.topGap.key } }"
              class="btn btn-primary"
            >
              See the plan <Icon
                name="arrow-right"
                :size="14"
              />
            </RouterLink>
          </template>
          <p
            v-else
            class="muted"
          >
            Nothing urgent here. Keep your reviews up.
          </p>
        </div>
      </section>

      <section v-if="focusGaps.length">
        <SectionHeading title="Needs attention" />
        <GapList :gaps="focusGaps" />
      </section>
      <EmptyState
        v-else-if="measured"
        icon="check-circle"
        title="Nothing critical right now."
        body="This area has no gap that needs your attention today."
      />
      <EmptyState
        v-else
        icon="crosshair"
        title="This area hasn't been measured yet."
        body="Finish your baseline and the mentor will show where to focus first."
      >
        <RouterLink
          :to="{ name: 'calibrate' }"
          class="btn btn-primary"
        >
          Calibrate your skills
        </RouterLink>
      </EmptyState>

      <section v-if="all.length">
        <SectionHeading title="All skills in this area">
          <button
            type="button"
            class="link-btn"
            :aria-expanded="showAll"
            data-testid="toggle-all"
            @click="showAll = !showAll"
          >
            {{ showAll ? 'Hide' : `Show ${all.length}` }}
          </button>
        </SectionHeading>
        <div
          v-if="showAll"
          class="card-quiet divided"
          data-testid="all-skills"
        >
          <SkillRow
            v-for="s in all"
            :key="s.key"
            :skill="s"
          />
        </div>
      </section>
      <CurriculumSection
        :key="track"
        :track="track"
      />
    </template>
  </div>
</template>

<style scoped>
.summary { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-6); }
.score { font-size: var(--fs-2xl); letter-spacing: -0.02em; margin: var(--s-1) 0 var(--s-2); }
.score strong { font-weight: 700; }
.of { font-size: var(--fs-md); color: var(--text-3); font-weight: 500; }
.next { display: grid; gap: var(--s-3); align-content: start; }
.next-title { font-size: var(--fs-lg); font-weight: 650; letter-spacing: -0.01em; }
.next .btn { width: fit-content; }
@media (max-width: 767px) { .summary { grid-template-columns: 1fr; gap: var(--s-5); } }
</style>

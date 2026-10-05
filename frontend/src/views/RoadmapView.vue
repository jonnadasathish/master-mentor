<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import Icon from '../components/common/Icon.vue'
import PageHeader from '../components/common/PageHeader.vue'
import ProgressBar from '../components/common/ProgressBar.vue'
import Skeleton from '../components/common/Skeleton.vue'
import { ACTIONABLE_GAP_STATUSES, TRACK_LABEL } from '../presentation/language'
import PersonalRoadmap from '../components/roadmap/PersonalRoadmap.vue'
import { usePersonalStore, useRoadmapStore, useSkillsStore } from '../stores/data'

/** The planned order of topics, shown next to what the mentor says matters most for you right now. */
const roadmap = useRoadmapStore()
const personal = usePersonalStore()
const view = ref<'personal' | 'planned'>('personal')
const skills = useSkillsStore()
const picked = ref<string | null>(null)
const showCompleted = ref(false)
const showAllUpcoming = ref(false)

const data = computed(() => roadmap.data)
const tracks = computed(() => data.value?.tracks ?? [])
const trackKey = computed(
  () => picked.value ?? tracks.value.find((t) => t.current_milestone)?.track ?? tracks.value[0]?.track ?? null,
)
const track = computed(() => tracks.value.find((t) => t.track === trackKey.value) ?? null)
const completed = computed(() => track.value?.milestones.filter((m) => m.complete) ?? [])
const current = computed(() => track.value?.milestones.find((m) => m.current) ?? null)
const upcoming = computed(() => track.value?.milestones.filter((m) => !m.complete && !m.current) ?? [])
const upcomingShown = computed(() => (showAllUpcoming.value ? upcoming.value : upcoming.value.slice(0, 3)))

const topGap = computed(() =>
  skills.list
    .filter((s) => s.gap && (ACTIONABLE_GAP_STATUSES as readonly string[]).includes(s.gap.status))
    .sort((a, b) => a.gap!.rank - b.gap!.rank)[0] ?? null,
)
const roadmapNext = computed(() => {
  const t = tracks.value.find((x) => x.current_milestone)
  const m = t?.milestones.find((x) => x.current)
  return m && t ? { track: t.track, milestone: m } : null
})
const agree = computed(() => {
  if (!topGap.value || !roadmapNext.value) return null
  return roadmapNext.value.milestone.skills.some((s) => s.key === topGap.value!.key)
})
const skillName = (key: string) => skills.nameOf(key)
const trackLabel = (key: string) => TRACK_LABEL[key] ?? key.replace(/_/g, ' ')

async function load(): Promise<void> {
  await Promise.all([roadmap.refresh(), skills.refresh()])
}
onMounted(() => Promise.all([personal.roadmap.ensure(), roadmap.ensure(), skills.ensure()]))
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="Roadmap"
      title="Your personal roadmap"
      description="Built from what was measured, your target role and your date. The planned order of topics sits beside it."
    />

    <div
      class="tabs"
      role="tablist"
      aria-label="Roadmap views"
    >
      <button
        type="button"
        class="tab"
        role="tab"
        :aria-selected="view === 'personal'"
        data-testid="view-personal"
        @click="view = 'personal'"
      >
        Your roadmap
      </button>
      <button
        type="button"
        class="tab"
        role="tab"
        :aria-selected="view === 'planned'"
        data-testid="view-planned"
        @click="view = 'planned'"
      >
        Planned order
      </button>
    </div>

    <template v-if="view === 'personal'">
      <Skeleton
        v-if="!personal.roadmap.data && !personal.roadmap.error"
        height="18rem"
        radius="var(--r-lg)"
      />
      <ErrorState
        v-else-if="!personal.roadmap.data"
        :error="personal.roadmap.error"
        @retry="personal.roadmap.refresh()"
      />
      <PersonalRoadmap
        v-else
        :roadmap="personal.roadmap.data"
      />
    </template>

    <Skeleton
      v-else-if="!data && !roadmap.error"
      height="18rem"
      radius="var(--r-lg)"
    />
    <ErrorState
      v-else-if="!data"
      :error="roadmap.error"
      @retry="load"
    />

    <template v-else>
      <section
        v-if="roadmapNext || topGap"
        class="compare"
        data-testid="roadmap-vs-priority"
      >
        <div class="side">
          <p class="eyebrow">
            Roadmap order
          </p>
          <p
            v-if="roadmapNext"
            class="line"
          >
            Next on the roadmap: <strong>{{ roadmapNext.milestone.name }}</strong>
            <span class="muted"> ({{ trackLabel(roadmapNext.track) }})</span>
          </p>
          <p
            v-else
            class="line muted"
          >
            Every milestone is complete.
          </p>
        </div>
        <div class="side personal">
          <p class="eyebrow">
            Your personal priority
          </p>
          <p
            v-if="topGap"
            class="line"
          >
            The mentor says <RouterLink :to="{ name: 'skill', params: { key: topGap.key } }">
              <strong>{{ topGap.name }}</strong>
            </RouterLink> matters most right now.
          </p>
          <p
            v-else
            class="line muted"
          >
            No gap needs urgent attention.
          </p>
        </div>
        <p
          v-if="agree !== null"
          class="verdict"
        >
          <Icon
            :name="agree ? 'check-circle' : 'info'"
            :size="16"
          />
          {{ agree
            ? 'The roadmap and your priorities agree.'
            : "They differ, and that's intended: the mentor works on your biggest weakness first, then returns to the roadmap." }}
        </p>
      </section>

      <div
        class="tabs"
        role="tablist"
        aria-label="Roadmap tracks"
      >
        <button
          v-for="t in tracks"
          :key="t.track"
          type="button"
          class="tab"
          role="tab"
          :aria-selected="trackKey === t.track"
          :data-testid="`track-${t.track}`"
          @click="picked = t.track; showCompleted = false; showAllUpcoming = false"
        >
          {{ trackLabel(t.track) }}
        </button>
      </div>

      <EmptyState
        v-if="!track"
        icon="roadmap"
        title="No roadmap loaded."
        body="The roadmap comes with the skill catalog."
      />
      <div
        v-else
        class="track"
        data-testid="roadmap"
      >
        <button
          v-if="completed.length"
          type="button"
          class="done-toggle"
          :aria-expanded="showCompleted"
          @click="showCompleted = !showCompleted"
        >
          <Icon
            name="check-circle"
            :size="16"
          /> {{ completed.length }} completed
          <Icon
            :name="showCompleted ? 'chevron-down' : 'chevron-right'"
            :size="14"
          />
        </button>
        <ol
          v-if="showCompleted"
          class="steps"
        >
          <li
            v-for="m in completed"
            :key="m.key"
            class="step complete"
          >
            <span class="node"><Icon
              name="check"
              :size="12"
            /></span>
            <p class="name">
              {{ m.name }}
            </p>
          </li>
        </ol>

        <article
          v-if="current"
          class="now"
          :data-testid="`milestone-${current.key}`"
        >
          <p class="eyebrow now-label">
            <Icon
              name="arrow-right"
              :size="14"
            /> Current milestone
          </p>
          <h2>{{ current.name }}</h2>
          <p
            v-if="current.content"
            class="muted"
          >
            {{ current.content }}
          </p>
          <div
            v-if="current.required_total > 0"
            class="progress"
          >
            <p class="tabular">
              <strong>{{ current.required_done }} of {{ current.required_total }}</strong> core skills ready
            </p>
            <ProgressBar
              :value="current.required_done"
              :max="current.required_total"
              label="Core skills ready in this milestone"
            />
          </div>
          <ul class="skills">
            <li
              v-for="s in current.skills"
              :key="s.key"
              :class="{ done: s.done }"
            >
              <RouterLink
                :to="{ name: 'skill', params: { key: s.key } }"
                class="skill-chip"
              >
                <Icon
                  :name="s.done ? 'check-circle' : 'circle'"
                  :size="14"
                  :label="s.done ? 'Ready' : 'Not ready yet'"
                />
                {{ skillName(s.key) }}
              </RouterLink>
            </li>
          </ul>
          <ul
            v-if="current.extra_exit.length"
            class="exit"
          >
            <li
              v-for="x in current.extra_exit"
              :key="x.text"
            >
              <Icon
                :name="x.met ? 'check-circle' : 'circle'"
                :size="14"
              /> {{ x.text }}
            </li>
          </ul>
        </article>
        <p
          v-else-if="!upcoming.length"
          class="muted"
        >
          Every milestone in this track is complete.
        </p>

        <div v-if="upcoming.length">
          <p class="eyebrow up-label">
            Up next
          </p>
          <ol class="steps">
            <li
              v-for="m in upcomingShown"
              :key="m.key"
              class="step"
              :data-testid="`milestone-${m.key}`"
            >
              <span class="node"><Icon
                name="circle"
                :size="10"
              /></span>
              <div>
                <p class="name">
                  {{ m.name }}
                </p>
                <p
                  v-if="m.required_total > 0"
                  class="muted small"
                >
                  {{ m.required_total }} core skills
                </p>
              </div>
            </li>
          </ol>
          <button
            v-if="upcoming.length > 3"
            type="button"
            class="link-btn show"
            @click="showAllUpcoming = !showAllUpcoming"
          >
            {{ showAllUpcoming ? 'Show fewer' : `Show all ${upcoming.length}` }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.compare { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-4); padding: var(--s-5); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); box-shadow: var(--shadow-sm); }
.side { display: grid; gap: var(--s-2); align-content: start; }
.side.personal { padding-left: var(--s-5); border-left: 1px solid var(--border); }
.line { font-size: var(--fs-md); }
.verdict { grid-column: 1 / -1; display: flex; align-items: flex-start; gap: var(--s-2); padding-top: var(--s-3); border-top: 1px solid var(--border); font-size: var(--fs-sm); color: var(--text-2); }
.verdict :deep(svg) { margin-top: 0.15rem; color: var(--accent); }
.track { display: grid; gap: var(--s-5); max-width: 50rem; }
.done-toggle { display: inline-flex; align-items: center; gap: var(--s-2); width: fit-content; padding: var(--s-2) var(--s-3); background: var(--healthy-bg); color: var(--healthy-fg); border: 1px solid var(--healthy-bd); border-radius: 999px; font: inherit; font-size: var(--fs-sm); font-weight: 650; cursor: pointer; }
.steps { display: grid; gap: var(--s-3); position: relative; padding-left: var(--s-2); }
.step { display: flex; align-items: center; gap: var(--s-3); }
.node { display: grid; place-items: center; width: 1.4rem; height: 1.4rem; border-radius: 50%; background: var(--surface); border: 2px solid var(--border-strong); color: var(--text-3); flex: none; }
.step.complete .node { background: var(--healthy-fg); border-color: var(--healthy-fg); color: #fff; }
.name { font-weight: 600; }
.small { font-size: var(--fs-sm); }
.now { display: grid; gap: var(--s-3); padding: var(--s-5); background: var(--surface); border: 1px solid var(--accent-border); border-left: 4px solid var(--accent); border-radius: var(--r-lg); box-shadow: var(--shadow-sm); }
.now-label { display: flex; align-items: center; gap: var(--s-1); color: var(--accent-text); }
.progress { display: grid; gap: var(--s-2); max-width: 28rem; }
.skills { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.skill-chip { display: inline-flex; align-items: center; gap: var(--s-1); padding: 0.25rem 0.7rem; border-radius: 999px; background: var(--surface-2); border: 1px solid var(--border); font-size: var(--fs-sm); color: var(--text); }
.skill-chip:hover { text-decoration: none; background: var(--surface-3); }
.skills .done .skill-chip { background: var(--healthy-bg); border-color: var(--healthy-bd); color: var(--healthy-fg); }
.exit { display: grid; gap: var(--s-1); font-size: var(--fs-sm); color: var(--text-2); }
.exit li { display: flex; align-items: center; gap: var(--s-2); }
.up-label { margin-bottom: var(--s-3); }
.show { margin-top: var(--s-3); font-size: var(--fs-sm); }
@media (max-width: 767px) {
  .compare { grid-template-columns: 1fr; }
  .side.personal { padding-left: 0; border-left: 0; padding-top: var(--s-3); border-top: 1px solid var(--border); }
}
</style>

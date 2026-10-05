<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import type { PersonalRoadmap, RoadmapItem } from '../../api/types'
import { monthYear, plural, trimWeeks } from '../../presentation/format'
import { BUCKET_HINT, BUCKET_LABEL, PHASE_LABEL } from '../../presentation/language'
import { reasonPhrases } from '../../presentation/reasons'
import { whyWeak } from '../../presentation/skill'
import { useSkillsStore } from '../../stores/data'
import EmptyState from '../common/EmptyState.vue'
import Icon from '../common/Icon.vue'
import SectionHeading from '../common/SectionHeading.vue'
import RoadmapItemCard from './RoadmapItemCard.vue'

/**
 * Your personal roadmap: focus now, already strong, later, parked and unmeasured. Which skill is in which group, the
 * reasons and every number come from the server (the gap engine); this only presents them.
 */
const props = defineProps<{ roadmap: PersonalRoadmap }>()
const skills = useSkillsStore()
const showWhy = ref(false)
const showParked = ref(false)

const ready = computed(
  () => props.roadmap.available && ['ENOUGH_MEASURED', 'COMPLETE'].includes(props.roadmap.calibration_phase),
)
const based = computed(() => props.roadmap.based_on)
const sections = computed(() => props.roadmap.sections)
const phaseLabel = computed(() => PHASE_LABEL[based.value.phase] ?? based.value.phase)
const bucketOf = (i: RoadmapItem) => BUCKET_LABEL[i.bucket]
/** "moved into your focus: it showed up as a weakness in a mock", from the engine's own reason codes. */
function enteredText(codes: string[]): string {
  const reason = reasonPhrases(codes, skills.nameOf, 1)[0]
  return reason ? `moved into your focus: ${reason.replace(/\.$/, '').replace(/^./, (m) => m.toLowerCase())}.` : 'moved into your focus.'
}
const why = computed(() =>
  props.roadmap.why.map((w) => ({
    ...w,
    lines: whyWeak({ component: w.component, metrics: w.metrics, reason_codes: w.reason_codes }, skills.nameOf),
  })),
)
</script>

<template>
  <div
    class="stack"
    data-testid="personal-roadmap"
  >
    <EmptyState
      v-if="!ready"
      icon="roadmap"
      title="Your personal roadmap appears after calibration."
      :body="`${based.measured_skills} of ${based.required_skills} required skills are measured so far. Once enough is measured, your roadmap is built from the evidence, your target role and your date.`"
    >
      <RouterLink
        :to="{ name: 'calibrate' }"
        class="btn btn-primary"
        data-testid="roadmap-to-calibrate"
      >
        {{ roadmap.calibration_phase === 'NOT_STARTED' ? 'Start calibration' : 'Continue calibration' }}
      </RouterLink>
    </EmptyState>

    <template v-else>
      <section
        class="phase card"
        data-testid="roadmap-phase"
      >
        <div>
          <p class="eyebrow">
            Current phase
          </p>
          <p class="big">
            {{ phaseLabel }}
          </p>
        </div>
        <dl class="timeline">
          <div v-if="based.target_date">
            <dt>Interview target</dt>
            <dd>{{ monthYear(based.target_date) }}</dd>
          </div>
          <div v-if="based.weeks_left">
            <dt>Time remaining</dt>
            <dd>{{ plural(Number(trimWeeks(based.weeks_left)), 'week') }}</dd>
          </div>
        </dl>
      </section>

      <p
        v-if="roadmap.calibration_phase === 'ENOUGH_MEASURED'"
        class="initial"
        data-testid="roadmap-initial"
      >
        <Icon
          name="info"
          :size="16"
        /> This is your initial roadmap. It sharpens as the remaining calibration is completed.
      </p>

      <section
        v-if="roadmap.changes.changed"
        class="changed"
        data-testid="roadmap-changed"
        aria-labelledby="changed-title"
      >
        <h2 id="changed-title">
          <Icon
            name="refresh"
            :size="16"
          /> Your plan changed
        </h2>
        <ul>
          <li
            v-for="c in roadmap.changes.entered"
            :key="`in-${c.skill_key}`"
          >
            <strong>{{ c.name }}</strong> {{ enteredText(c.reason_codes) }}
          </li>
          <li
            v-for="c in roadmap.changes.left"
            :key="`out-${c.skill_key}`"
          >
            <strong>{{ c.name }}</strong> moved out of your focus.
          </li>
        </ul>
      </section>

      <section aria-labelledby="focus-title">
        <SectionHeading
          id="focus-title"
          title="Focus now"
        />
        <ul
          v-if="roadmap.focus_now.length"
          class="cards"
          data-testid="focus-now"
        >
          <RoadmapItemCard
            v-for="i in roadmap.focus_now"
            :key="i.skill_key"
            :item="i"
          />
        </ul>
        <p
          v-else
          class="quiet"
        >
          Nothing needs focus right now.
        </p>
      </section>

      <section
        v-if="sections.maintain.count"
        aria-labelledby="strong-title"
      >
        <SectionHeading
          id="strong-title"
          title="Already strong"
        >
          <span class="muted tabular">{{ sections.maintain.count }}</span>
        </SectionHeading>
        <p class="hint">
          {{ BUCKET_HINT.maintain }} They won't be taught again.
        </p>
        <ul
          class="chips"
          data-testid="strong-skills"
        >
          <li
            v-for="i in sections.maintain.items"
            :key="i.skill_key"
          >
            <RouterLink
              :to="{ name: 'skill', params: { key: i.skill_key } }"
              class="chip"
            >
              {{ i.name }} <span class="tabular muted">{{ i.score }}</span>
            </RouterLink>
          </li>
        </ul>
        <p
          v-if="sections.maintain.count > sections.maintain.items.length"
          class="muted small"
        >
          and {{ sections.maintain.count - sections.maintain.items.length }} more
        </p>
      </section>

      <section
        v-if="sections.later.count"
        aria-labelledby="later-title"
      >
        <SectionHeading
          id="later-title"
          title="Later"
        >
          <span class="muted tabular">{{ sections.later.count }}</span>
        </SectionHeading>
        <ul
          class="later card-quiet divided"
          data-testid="later"
        >
          <li
            v-for="i in sections.later.items"
            :key="i.skill_key"
          >
            <RouterLink
              :to="{ name: 'skill', params: { key: i.skill_key } }"
              class="name"
            >
              {{ i.name }}
            </RouterLink>
            <span class="muted small">{{ bucketOf(i) }}</span>
            <span class="tabular muted small">{{ i.score ?? '—' }} / {{ i.target }}</span>
          </li>
        </ul>
        <p
          v-if="sections.later.count > sections.later.items.length"
          class="muted small more"
        >
          and {{ sections.later.count - sections.later.items.length }} more
        </p>
      </section>

      <section
        v-if="sections.unmeasured.count"
        class="unmeasured card-quiet"
        data-testid="unmeasured"
      >
        <p>
          <strong class="tabular">{{ sections.unmeasured.count }}</strong> skills have no evidence yet, so they aren't on your
          roadmap. They appear as you practise them.
        </p>
      </section>

      <section
        v-if="sections.parked.count"
        aria-labelledby="parked-title"
      >
        <SectionHeading
          id="parked-title"
          title="Parked"
        >
          <button
            type="button"
            class="link-btn"
            :aria-expanded="showParked"
            @click="showParked = !showParked"
          >
            {{ showParked ? 'Hide' : `Show ${sections.parked.count}` }}
          </button>
        </SectionHeading>
        <p class="hint">
          {{ BUCKET_HINT.parked }}
        </p>
        <ul
          v-if="showParked"
          class="chips"
        >
          <li
            v-for="i in sections.parked.items"
            :key="i.skill_key"
          >
            <span class="chip">{{ i.name }}</span>
          </li>
        </ul>
      </section>

      <section class="whybox card-quiet">
        <button
          type="button"
          class="why-toggle"
          :aria-expanded="showWhy"
          data-testid="why-roadmap"
          @click="showWhy = !showWhy"
        >
          Why is this my roadmap?
          <Icon
            :name="showWhy ? 'chevron-down' : 'chevron-right'"
            :size="14"
          />
        </button>
        <div
          v-if="showWhy"
          class="why-body"
          data-testid="why-roadmap-body"
        >
          <h3>It's based on</h3>
          <ul class="based">
            <li v-if="based.role">
              Your target role: <strong>{{ based.role.name }}</strong>
            </li>
            <li v-if="based.target_date">
              Your target date: <strong>{{ monthYear(based.target_date) }}</strong><template v-if="based.weeks_left">
                ({{ plural(Number(trimWeeks(based.weeks_left)), 'week') }} left)
              </template>
            </li>
            <li>What was measured: <strong>{{ based.measured_skills }} of {{ based.required_skills }}</strong> required skills</li>
            <li v-if="roadmap.focus_now.length">
              Your biggest gaps: {{ roadmap.focus_now.map((i) => i.name).join('; ') }}
            </li>
            <li v-if="based.blocked_skills">
              Prerequisites: {{ plural(based.blocked_skills, 'skill') }} wait for a weaker prerequisite
            </li>
            <li>Revision: {{ based.overdue_reviews ? plural(based.overdue_reviews, 'review') + ' overdue' : 'no reviews overdue' }}</li>
          </ul>
          <template v-if="why.length">
            <h3>Why these skills come first</h3>
            <div
              v-for="w in why"
              :key="w.skill_key"
              class="reason"
              :data-testid="`why-${w.skill_key}`"
            >
              <p>
                <strong>{{ w.name }}</strong> is prioritized because your current score is
                <strong class="tabular">{{ w.score ?? 'not measured' }}</strong> against a target of
                <strong class="tabular">{{ w.target }}</strong>.
              </p>
              <ul>
                <li
                  v-for="line in w.lines"
                  :key="line"
                >
                  {{ line }}
                </li>
              </ul>
            </div>
          </template>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.phase { display: flex; justify-content: space-between; align-items: center; gap: var(--s-5); flex-wrap: wrap; }
.big { font-size: var(--fs-2xl); font-weight: 700; letter-spacing: -0.025em; }
.timeline { display: flex; gap: var(--s-6); flex-wrap: wrap; }
dt { font-size: var(--fs-xs); font-weight: 650; letter-spacing: 0.06em; text-transform: uppercase; color: var(--text-3); }
dd { font-weight: 650; }
.initial { display: flex; gap: var(--s-2); align-items: center; padding: var(--s-3) var(--s-4); background: var(--calibration-bg); color: var(--text); border-radius: var(--r-md); font-size: var(--fs-sm); }
.changed { padding: var(--s-4) var(--s-5); background: var(--accent-soft); border: 1px solid var(--accent-border); border-radius: var(--r-lg); display: grid; gap: var(--s-2); }
.changed h2 { display: flex; gap: var(--s-2); align-items: center; font-size: var(--fs-md); color: var(--accent-text); }
.changed ul { display: grid; gap: var(--s-1); font-size: var(--fs-sm); }
.cards { display: grid; gap: var(--s-3); }
.quiet { padding: var(--s-4); background: var(--surface); border: 1px dashed var(--border-strong); border-radius: var(--r-md); color: var(--text-2); }
.hint { font-size: var(--fs-sm); color: var(--text-3); margin-bottom: var(--s-3); }
.chips { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.chip { display: inline-flex; gap: var(--s-2); align-items: center; padding: 0.25rem 0.75rem; border-radius: 999px; background: var(--healthy-bg); border: 1px solid var(--healthy-bd); font-size: var(--fs-sm); color: var(--text); }
.chip:hover { text-decoration: none; }
.later li { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); }
.later .name { flex: 1; font-weight: 560; min-width: 0; }
.small { font-size: var(--fs-sm); }
.more { margin-top: var(--s-2); }
.why-toggle { display: inline-flex; align-items: center; gap: var(--s-1); background: none; border: 0; padding: 0; font: inherit; font-weight: 650; color: var(--accent-text); cursor: pointer; }
.why-body { display: grid; gap: var(--s-3); margin-top: var(--s-4); }
.why-body h3 { font-size: var(--fs-sm); text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-3); }
.based, .reason ul { display: grid; gap: var(--s-1); padding-left: var(--s-5); list-style: disc; font-size: var(--fs-sm); color: var(--text-2); }
.reason { display: grid; gap: var(--s-1); }
</style>

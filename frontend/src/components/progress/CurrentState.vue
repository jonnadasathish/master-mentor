<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { CurrentState } from '../../api/types'
import Icon from '../common/Icon.vue'
import SectionHeading from '../common/SectionHeading.vue'
import SelfReportVsObserved from './SelfReportVsObserved.vue'

/** "Your current state": what is known about you, measured, and what you said, kept apart (D-080). */
defineProps<{ state: CurrentState }>()
const BLOCKS = [
  { key: 'strong', label: 'Strong', hint: 'At or above target', icon: 'check-circle' },
  { key: 'developing', label: 'Developing', hint: 'Below target, moving', icon: 'trending' },
  { key: 'critical', label: 'Critical gaps', hint: 'Your highest-priority weaknesses', icon: 'alert-circle' },
  { key: 'unknown', label: 'Unknown', hint: 'Not enough evidence yet', icon: 'help' },
] as const
</script>

<template>
  <section
    class="current-state"
    aria-labelledby="state-title"
    data-testid="current-state"
  >
    <SectionHeading
      id="state-title"
      title="Your current state"
    >
      <RouterLink :to="{ name: 'roadmap' }">
        See your roadmap
      </RouterLink>
    </SectionHeading>
    <p class="lead">
      What Master Mentor <strong>measured</strong> about you so far.
    </p>

    <div class="blocks">
      <article
        v-for="b in BLOCKS"
        :key="b.key"
        class="block"
        :class="`k-${b.key}`"
        :data-testid="`state-${b.key}`"
      >
        <p class="head">
          <Icon
            :name="b.icon"
            :size="16"
          /> {{ b.label }}
        </p>
        <p class="n tabular">
          {{ state[b.key].count }}
        </p>
        <p class="hint muted">
          {{ b.hint }}
        </p>
        <ul v-if="state[b.key].items.length && b.key !== 'unknown'">
          <li
            v-for="i in state[b.key].items.slice(0, 3)"
            :key="i.skill_key"
          >
            <RouterLink :to="{ name: 'skill', params: { key: i.skill_key } }">
              {{ i.name }}
            </RouterLink>
            <span class="tabular muted">{{ i.score ?? '—' }} / {{ i.target }}</span>
          </li>
        </ul>
      </article>
    </div>

    <div
      class="reported"
      aria-labelledby="reported-title"
    >
      <SectionHeading
        id="reported-title"
        title="What you told us, and what was measured"
      >
        <RouterLink :to="{ name: 'onboarding' }">
          Edit starting profile
        </RouterLink>
      </SectionHeading>
      <p
        v-if="state.self_reported.length"
        class="notice"
      >
        <strong>Self-reported context — not yet verified.</strong> Your own assessments never change a score.
      </p>
      <SelfReportVsObserved
        v-if="state.self_reported.length"
        :groups="state.self_reported"
      />
      <p
        v-else
        class="quiet"
      >
        You haven't added any self-reported context. It's optional, and it appears here beside what is measured.
      </p>
    </div>
  </section>
</template>

<style scoped>
.current-state { display: grid; gap: var(--s-4); }
.lead { color: var(--text-2); margin-top: calc(var(--s-2) * -1); }
.blocks { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--s-3); }
.block { display: grid; gap: var(--s-1); align-content: start; padding: var(--s-4); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); }
.head { display: flex; align-items: center; gap: var(--s-2); font-weight: 650; }
.k-strong .head { color: var(--healthy-fg); }
.k-critical .head { color: var(--critical-fg); }
.k-developing .head { color: var(--due-fg); }
.n { font-size: var(--fs-2xl); font-weight: 700; letter-spacing: -0.03em; line-height: 1.1; }
.hint { font-size: var(--fs-xs); }
.block ul { display: grid; gap: var(--s-1); margin-top: var(--s-2); font-size: var(--fs-sm); }
.block li { display: flex; justify-content: space-between; gap: var(--s-2); }
.reported { display: grid; gap: var(--s-3); margin-top: var(--s-3); }
.notice { padding: var(--s-3) var(--s-4); background: var(--medium-bg); border: 1px dashed var(--medium-bd); border-radius: var(--r-md); font-size: var(--fs-sm); }
.quiet { padding: var(--s-4); background: var(--surface); border: 1px dashed var(--border-strong); border-radius: var(--r-md); color: var(--text-2); }
@media (max-width: 1099px) { .blocks { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 599px) { .blocks { grid-template-columns: minmax(0, 1fr); } }
</style>

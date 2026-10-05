<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { CurrentState } from '../../api/types'
import { CLAIM_LABEL, CONFIDENCE_LABEL, stateFromGapStatus } from '../../presentation/language'
import Icon from '../common/Icon.vue'
import StatusPill from '../common/StatusPill.vue'

/**
 * What you told us next to what Master Mentor measured. The two are kept visibly apart: the left is a claim (dashed,
 * "not verified"), the right is evidence (solid). Measured values are the server's; a claim never changes them.
 */
defineProps<{ groups: CurrentState['self_reported'] }>()
type Skill = CurrentState['self_reported'][number]['skills'][number]
/** Task results first, then the ones you only rated yourself on. */
const shown = (skills: Skill[]): Skill[] =>
  [...skills].sort((a, b) => Number(a.declared_unknown) - Number(b.declared_unknown)).slice(0, 4)
</script>

<template>
  <ul
    class="groups"
    data-testid="self-report-vs-observed"
  >
    <li
      v-for="g in groups"
      :key="g.group_key"
      class="group"
      :data-testid="`compare-${g.group_key}`"
    >
      <h3>{{ g.name }}</h3>
      <div class="pair">
        <div
          class="said"
          data-testid="self-reported"
        >
          <p class="label">
            <Icon
              name="message"
              :size="13"
            /> You said
          </p>
          <p class="claims">
            <span
              v-for="c in g.claims"
              :key="c"
              class="claim"
            >{{ CLAIM_LABEL[c] }}</span>
          </p>
          <p class="note">
            Self-reported · not verified
          </p>
        </div>
        <div
          class="measured"
          data-testid="observed"
        >
          <p class="label">
            <Icon
              name="check-circle"
              :size="13"
            /> Measured
          </p>
          <template v-if="g.skills.length">
            <p class="count tabular">
              {{ g.measured }} of {{ g.total }} skills measured by tasks
            </p>
            <ul class="skills">
              <li
                v-for="s in shown(g.skills)"
                :key="s.skill_key"
                :class="{ declared: s.declared_unknown }"
                :data-testid="s.declared_unknown ? 'declared-unknown' : 'task-measured'"
              >
                <RouterLink :to="{ name: 'skill', params: { key: s.skill_key } }">
                  {{ s.name }}
                </RouterLink>
                <template v-if="s.declared_unknown">
                  <span class="declared-tag">You marked this as new to you</span>
                </template>
                <template v-else>
                  <span class="tabular">{{ s.score ?? '—' }} / {{ s.target ?? '—' }}</span>
                  <span class="muted small">{{ (CONFIDENCE_LABEL[s.confidence] ?? s.confidence).toLowerCase() }} confidence</span>
                  <StatusPill
                    :state="stateFromGapStatus(s.status)"
                    quiet
                  />
                </template>
              </li>
            </ul>
            <p
              v-if="g.skills.length > shown(g.skills).length"
              class="muted small"
            >
              and {{ g.skills.length - shown(g.skills).length }} more
            </p>
          </template>
          <p
            v-else
            class="none"
          >
            Not measured yet
          </p>
        </div>
      </div>
    </li>
  </ul>
</template>

<style scoped>
.groups { display: grid; gap: var(--s-3); }
.group { padding: var(--s-4) var(--s-5); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); display: grid; gap: var(--s-3); }
h3 { font-size: var(--fs-md); }
.pair { display: grid; grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.4fr); gap: var(--s-4); }
.label { display: flex; align-items: center; gap: var(--s-1); font-size: var(--fs-xs); font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: var(--s-2); }
.said { padding: var(--s-3) var(--s-4); background: var(--medium-bg); border: 1px dashed var(--medium-fg); border-radius: var(--r-md); color: var(--medium-fg); }
.claims { display: flex; flex-wrap: wrap; gap: var(--s-1); }
.claim { padding: 0.1rem 0.6rem; border-radius: 999px; border: 1px dashed var(--medium-fg); font-weight: 650; font-size: var(--fs-sm); }
.note { margin-top: var(--s-2); font-size: var(--fs-xs); font-style: italic; }
.measured { padding: var(--s-3) var(--s-4); background: var(--surface); border: 1px solid var(--accent-border); border-left: 4px solid var(--accent); border-radius: var(--r-md); }
.measured .label { color: var(--accent-text); }
.count { font-weight: 650; margin-bottom: var(--s-2); }
.skills { display: grid; gap: var(--s-1); font-size: var(--fs-sm); }
.skills li { display: flex; flex-wrap: wrap; gap: var(--s-1) var(--s-3); align-items: center; }
.skills li a { font-weight: 560; }
.none { color: var(--text-2); font-weight: 560; }
.declared-tag { padding: 0.05rem 0.55rem; border-radius: 999px; border: 1px dashed var(--medium-fg); background: var(--medium-bg); color: var(--medium-fg); font-size: var(--fs-xs); font-weight: 650; }
.small { font-size: var(--fs-sm); }
@media (max-width: 767px) { .pair { grid-template-columns: 1fr; } }
</style>

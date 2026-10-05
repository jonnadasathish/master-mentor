<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import type { RoadmapItem } from '../../api/types'
import { formatMinutes } from '../../presentation/format'
import { BUCKET_ICON, BUCKET_LABEL, GAP_TYPE_LABEL, STAGE_LABEL } from '../../presentation/language'
import { reasonPhrases } from '../../presentation/reasons'
import { useSkillsStore } from '../../stores/data'
import Icon from '../common/Icon.vue'
import ProgressBar from '../common/ProgressBar.vue'

/** One skill in "focus now": where you are, why it is here, what it waits on, and the next step. Server values only. */
const props = defineProps<{ item: RoadmapItem }>()
const skills = useSkillsStore()

const reason = computed(() => reasonPhrases(props.item.reason_codes, skills.nameOf, 1)[0] ?? null)
const gapType = computed(() => (props.item.primary_gap_type ? (GAP_TYPE_LABEL[props.item.primary_gap_type] ?? null) : null))
const next = computed(() => {
  const stage = props.item.focus_stage ? (STAGE_LABEL[props.item.focus_stage] ?? props.item.focus_stage) : null
  if (!stage) return null
  return `${stage}${props.item.next_step_minutes ? ` · ${formatMinutes(props.item.next_step_minutes)}` : ''}`
})
const waiting = computed(() => props.item.prerequisites[0] ?? null)
</script>

<template>
  <li
    class="item"
    :data-testid="`roadmap-item-${item.skill_key}`"
  >
    <div class="top">
      <RouterLink
        :to="{ name: 'skill', params: { key: item.skill_key } }"
        class="name"
      >
        {{ item.name }}
      </RouterLink>
      <span
        class="bucket"
        :class="`b-${item.bucket}`"
      >
        <Icon
          :name="BUCKET_ICON[item.bucket] ?? 'circle'"
          :size="13"
        /> {{ BUCKET_LABEL[item.bucket] }}
      </span>
    </div>
    <div class="score">
      <span class="tabular value"><strong>{{ item.score ?? '—' }}</strong> / {{ item.target }}</span>
      <ProgressBar
        :value="item.score"
        :max="item.target"
        :label="`${item.name}: ${item.score ?? 'not measured'} of ${item.target}`"
        size="sm"
      />
    </div>
    <p
      v-if="item.declared_unknown"
      class="declared"
      data-testid="declared-unknown"
    >
      <Icon
        name="message"
        :size="13"
      /> You marked this as new to you (self-rating, not a task result)
    </p>
    <p
      v-if="gapType || reason"
      class="why"
    >
      <strong v-if="gapType">{{ gapType }}.</strong> {{ reason }}
    </p>
    <p class="meta">
      <span v-if="next"><Icon
        name="arrow-right"
        :size="13"
      /> Next: {{ next }}</span>
      <span
        v-if="waiting"
        class="wait"
        data-testid="waiting-on"
      ><Icon
        name="lock"
        :size="13"
      /> Needs {{ waiting.name }} first
        ({{ waiting.score === null ? 'not measured' : waiting.score }} of {{ waiting.min_score }})</span>
      <span
        v-else
        class="ok"
      ><Icon
        name="check-circle"
        :size="13"
      /> Prerequisites ready</span>
    </p>
  </li>
</template>

<style scoped>
.item { list-style: none; display: grid; gap: var(--s-2); padding: var(--s-4) var(--s-5); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg); box-shadow: var(--shadow-sm); }
.top { display: flex; justify-content: space-between; align-items: center; gap: var(--s-3); }
.name { font-weight: 700; font-size: var(--fs-md); color: var(--text); letter-spacing: -0.01em; }
.bucket { display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: var(--fs-xs); font-weight: 650; background: var(--surface-3); color: var(--text-2); white-space: nowrap; }
.b-build { background: var(--high-bg); color: var(--high-fg); }
.b-consolidate { background: var(--due-bg); color: var(--due-fg); }
.b-sharpen { background: var(--healthy-bg); color: var(--healthy-fg); }
.score { display: grid; grid-template-columns: 5.5rem minmax(0, 1fr); align-items: center; gap: var(--s-3); }
.value { font-size: var(--fs-sm); color: var(--text-3); }
.value strong { color: var(--text); font-size: var(--fs-md); }
.why { font-size: var(--fs-sm); color: var(--text-2); }
.declared { display: inline-flex; align-items: center; gap: 0.3rem; width: fit-content; padding: 0.1rem 0.6rem; border-radius: 999px; border: 1px dashed var(--medium-fg); background: var(--medium-bg); color: var(--medium-fg); font-size: var(--fs-xs); font-weight: 650; }
.meta { display: flex; flex-wrap: wrap; gap: var(--s-1) var(--s-4); font-size: var(--fs-sm); color: var(--text-3); }
.meta span { display: inline-flex; align-items: center; gap: 0.3rem; }
.wait { color: var(--blocked-fg); }
.ok { color: var(--healthy-fg); }
</style>

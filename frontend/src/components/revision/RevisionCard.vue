<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import type { RevisionItem } from '../../api/types'
import { formatMinutes, plural, shortDate } from '../../presentation/format'
import { REVIEW_KIND_LABEL } from '../../presentation/language'
import { recordLabel } from '../../presentation/mission'
import { useProblemsStore, useSkillsStore } from '../../stores/data'
import AssessmentForm from '../practice/AssessmentForm.vue'
import Icon from '../common/Icon.vue'
import StatusPill from '../common/StatusPill.vue'
import type { HttpClient } from '../../api/client'

/** One review. What it is, when it is due, how long it takes, and a single clear action. Server values only. */
const props = defineProps<{ item: RevisionItem; client: HttpClient }>()
const emit = defineEmits<{ suspend: []; resume: []; reviewed: [] }>()

const skills = useSkillsStore()
const problems = useProblemsStore()
const open = ref(false)

const title = computed(() => {
  const i = props.item
  const verb = REVIEW_KIND_LABEL[i.item_type] ?? 'Review'
  if (i.item_type === 'PROBLEM') return `${verb}: ${problems.titleOf(i.subject_ref) ?? i.skill_name}`
  return `${verb}: ${i.skill_name}`
})
const canReview = computed(
  () => props.item.state === 'ACTIVE' && ['overdue', 'due', 'maintenance', 'upcoming'].includes(props.item.bucket),
)
const dueText = computed(() => {
  const i = props.item
  if (i.state === 'GRADUATED') return 'Graduated: no more scheduled reviews'
  if (i.state === 'SUSPENDED') return `Paused${i.suspend_reason ? ` · ${i.suspend_reason.toLowerCase().replace(/_/g, ' ')}` : ''}`
  if (!i.due_date) return ''
  if (i.days_overdue > 0) return `Overdue by ${plural(i.days_overdue, 'day')}`
  if (i.bucket === 'due' || i.bucket === 'maintenance') return 'Due today'
  return `Due ${shortDate(i.due_date)}`
})
const pill = computed<'overdue' | 'due' | 'completed' | 'blocked' | null>(() => {
  const i = props.item
  if (i.state === 'GRADUATED') return 'completed'
  if (i.state === 'SUSPENDED') return 'blocked'
  if (i.bucket === 'overdue') return 'overdue'
  if (i.bucket === 'due' || i.bucket === 'maintenance') return 'due'
  return null
})
</script>

<template>
  <li
    class="review"
    :class="{ overdue: item.bucket === 'overdue' && item.state === 'ACTIVE' }"
    :data-testid="`item-${item.item_key}`"
  >
    <div class="top">
      <div class="titles">
        <h2>{{ title }}</h2>
        <p class="meta">
          <Icon
            name="clock"
            :size="14"
          /><span>{{ formatMinutes(item.minutes) }}{{ dueText ? ` · ${dueText}` : '' }}</span>
        </p>
      </div>
      <StatusPill
        v-if="pill"
        :state="pill"
      />
    </div>

    <p class="facts muted">
      <span>{{ item.last_reviewed_on ? `Last reviewed ${shortDate(item.last_reviewed_on)}` : 'Not reviewed yet' }}</span>
      <span v-if="item.lapses">· Slipped {{ plural(item.lapses, 'time') }}</span>
      <span v-if="item.needs_reinforcement">· Brush up on the basics first</span>
      <span v-if="item.parked">· Parked skill</span>
    </p>

    <div class="actions">
      <template v-if="canReview">
        <RouterLink
          v-if="item.item_type === 'PROBLEM'"
          :to="{ name: 'problem', params: { problemKey: item.subject_ref }, query: { revision: item.item_key } }"
          class="btn btn-primary"
          :data-testid="`review-${item.item_key}`"
        >
          Review
        </RouterLink>
        <button
          v-else
          type="button"
          class="btn btn-primary"
          :data-testid="`review-${item.item_key}`"
          @click="open = !open"
        >
          {{ open ? 'Close' : 'Review' }}
        </button>
      </template>
      <button
        v-if="item.state === 'ACTIVE'"
        type="button"
        class="btn btn-ghost btn-sm"
        :data-testid="`suspend-${item.item_key}`"
        @click="emit('suspend')"
      >
        Pause this
      </button>
      <button
        v-if="item.state === 'SUSPENDED'"
        type="button"
        class="btn btn-sm"
        :data-testid="`resume-${item.item_key}`"
        @click="emit('resume')"
      >
        Resume
      </button>
    </div>

    <div
      v-if="open"
      class="form"
    >
      <p class="muted hint">
        Closed-book. You'll record {{ recordLabel(item.review_kind) }}.
      </p>
      <AssessmentForm
        :client="client"
        :kind="item.review_kind"
        :skills="[{ key: item.skill, name: skills.nameOf(item.skill) }]"
        :source-key="`revision:${item.item_key}`"
        :revision-item-key="item.item_key"
        @recorded="emit('reviewed')"
      />
    </div>
  </li>
</template>

<style scoped>
.review {
  display: grid; gap: var(--s-3); padding: var(--s-5); background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-lg);
  box-shadow: var(--shadow-sm); transition: box-shadow var(--t-base) var(--ease), border-color var(--t-base) var(--ease);
}
.review:hover { box-shadow: var(--shadow-md); border-color: var(--border-strong); }
.review.overdue { border-left: 4px solid var(--overdue-fg); }
.top { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--s-3); }
.titles { display: grid; gap: var(--s-1); min-width: 0; }
h2 { font-size: var(--fs-md); letter-spacing: -0.01em; }
.meta { display: flex; align-items: center; gap: var(--s-1); font-size: var(--fs-sm); color: var(--text-3); }
.facts { display: flex; flex-wrap: wrap; gap: var(--s-1) var(--s-2); font-size: var(--fs-sm); }
.actions { display: flex; align-items: center; gap: var(--s-2); flex-wrap: wrap; }
.hint { font-size: var(--fs-sm); margin-bottom: var(--s-2); }
</style>

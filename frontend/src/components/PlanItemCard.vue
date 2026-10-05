<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { RouterLink } from 'vue-router'
import type { HttpClient } from '../api/client'
import { ApiError } from '../api/client'
import type { Effects, PlanItem } from '../api/types'
import AssessmentForm from './AssessmentForm.vue'
import AttemptForm from './AttemptForm.vue'

/** One frozen plan item: mission view (template, problems, pass rule, timer) + actions. Display only. */
const props = defineProps<{ item: PlanItem; client: HttpClient; now?: () => number }>()
const emit = defineEmits<{ changed: []; completed: [effects?: Effects] }>()

const SKIP_REASONS = ['NO_TIME', 'TOO_HARD', 'NOT_RELEVANT', 'OTHER'] as const
const TYPE_ICON: Record<string, string> = {
  REVISION: '⟳', GAP: '◎', FOLLOW_UP: '↳', DIAGNOSTIC: '?', BASELINE: '⌖', MAINTENANCE: '♺', MOCK: '🎤', FINAL_SIMULATION: '🏁',
}
const open = ref(false)
const showWhy = ref(false)
const skipping = ref(false)
const error = ref('')
const startedAt = ref<number | null>(null)
const tick = ref(0)
let timer: ReturnType<typeof setInterval> | undefined
const clock = () => (props.now ? props.now() : Date.now())

const kind = computed(() => String(props.item.template?.observation?.kind ?? (props.item.problems.length ? 'ATTEMPT' : '')))
const pending = computed(() => props.item.status === 'PENDING')
const label = computed(() => {
  const i = props.item
  if (i.candidate_type === 'BASELINE') return `Baseline ${i.battery_item_key}`
  if (i.candidate_type === 'REVISION') return `Revision ${i.revision_item_key}`
  if (i.candidate_type === 'MOCK') return `Mock round: ${i.round_type}`
  if (i.candidate_type === 'FINAL_SIMULATION') return 'Final simulation'
  return `${i.skill}`
})
/** Display only: the template's own limit (seconds) or the item minutes. */
const limitSeconds = computed(() => {
  const limit = props.item.template?.observation?.limit_seconds
  return typeof limit === 'number' ? limit : props.item.minutes * 60
})
const elapsed = computed(() => {
  void tick.value
  return startedAt.value === null ? 0 : Math.max(0, Math.floor((clock() - startedAt.value) / 1000))
})
const mmss = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

async function act(path: string, body: unknown = {}): Promise<void> {
  error.value = ''
  try {
    await props.client.post(`/plan/items/${props.item.id}/${path}`, body)
    emit('changed')
  } catch (caught) {
    error.value = caught instanceof ApiError ? caught.message : String(caught)
  }
}

async function start(): Promise<void> {
  await act('start')
  startedAt.value = clock()
  open.value = true
  timer = setInterval(() => (tick.value += 1), 1000)
}

function done(effects?: Effects): void {
  if (timer) clearInterval(timer)
  emit('completed', effects)
}

onBeforeUnmount(() => timer && clearInterval(timer))
</script>

<template>
  <li
    class="card"
    :class="item.status.toLowerCase()"
    :data-testid="`plan-item-${item.position}`"
  >
    <div class="head">
      <span
        class="icon"
        :aria-label="item.candidate_type.toLowerCase()"
      >{{ TYPE_ICON[item.candidate_type] ?? '•' }}</span>
      <strong>{{ item.position }}. {{ label }}</strong>
      <span class="stage">{{ item.stage?.toLowerCase().replace('_', ' ') }}</span>
      <span>{{ item.minutes }} min</span>
      <span
        v-if="item.explanation.priority != null"
        class="score"
      >priority {{ item.explanation.priority }}</span>
      <span class="status">{{ item.status.toLowerCase() + (item.skip_reason ? ` (${item.skip_reason.toLowerCase().replace('_', ' ')})` : '') }}</span>
    </div>
    <p
      v-if="item.explanation.expected_outcome"
      class="why"
    >
      Expected: {{ item.explanation.expected_outcome }}
      <button
        type="button"
        class="link"
        :aria-expanded="showWhy"
        :data-testid="`why-${item.position}`"
        @click="showWhy = !showWhy"
      >
        why {{ showWhy ? '▾' : '▸' }}
      </button>
    </p>
    <dl
      v-if="showWhy"
      class="metrics"
      :data-testid="`why-panel-${item.position}`"
    >
      <div
        v-for="(value, key) in item.explanation"
        :key="key"
      >
        <dt>{{ String(key).replace('_', ' ') }}</dt><dd>{{ value ?? '—' }}</dd>
      </div>
      <div><dt>reasons</dt><dd>{{ item.reason_codes.join(', ') || '—' }}</dd></div>
      <div><dt>score</dt><dd>{{ item.candidate_score }}</dd></div>
    </dl>
    <ul
      v-if="item.problems.length"
      class="problems"
    >
      <li
        v-for="p in item.problems"
        :key="p.id"
      >
        <RouterLink :to="{ name: 'problem', params: { problemKey: p.key } }">
          {{ p.title }}
        </RouterLink> ({{ p.difficulty.toLowerCase() }})
      </li>
    </ul>
    <p
      v-if="item.template"
      class="rule"
    >
      Done when: {{ item.template.pass_rule }} · record: {{ kind.toLowerCase().replace('_', ' ') }}
    </p>
    <p
      v-if="startedAt !== null && pending"
      class="timer"
      :data-testid="`timer-${item.position}`"
      aria-live="off"
    >
      ⏱ {{ mmss(elapsed) }} / {{ mmss(limitSeconds) }}
    </p>
    <div
      v-if="pending"
      class="actions"
    >
      <button
        v-if="startedAt === null"
        type="button"
        :data-testid="`start-${item.position}`"
        @click="start"
      >
        Start
      </button>
      <button
        type="button"
        :class="{ secondary: startedAt === null }"
        :data-testid="`log-${item.position}`"
        @click="open = !open"
      >
        {{ open ? 'Close' : 'Complete' }}
      </button>
      <button
        type="button"
        class="secondary"
        :data-testid="`no-evidence-${item.position}`"
        @click="act('complete', { no_evidence: true })"
      >
        Mark studied (no evidence)
      </button>
      <button
        type="button"
        class="secondary"
        :data-testid="`defer-${item.position}`"
        @click="act('defer')"
      >
        Tomorrow
      </button>
      <button
        type="button"
        class="secondary"
        :aria-expanded="skipping"
        :data-testid="`skip-${item.position}`"
        @click="skipping = !skipping"
      >
        Skip
      </button>
      <span
        v-if="skipping"
        class="skip"
        role="group"
        aria-label="Skip reason"
      >
        <button
          v-for="r in SKIP_REASONS"
          :key="r"
          type="button"
          class="chip"
          :data-testid="`skip-${item.position}-${r}`"
          @click="act('skip', { skip_reason: r })"
        >{{ r.toLowerCase().replace('_', ' ') }}</button>
      </span>
    </div>
    <template v-if="pending && open">
      <AttemptForm
        v-if="kind === 'ATTEMPT' && item.problems.length"
        :problem-id="item.problems[0]!.id"
        :client="client"
        :plan-item-id="item.id"
        @recorded="(_a, effects) => done(effects)"
      />
      <AssessmentForm
        v-else-if="kind && kind !== 'ATTEMPT' && kind !== 'ITEM_DEFINED' && item.skill"
        :client="client"
        :kind="kind"
        :skills="[{ key: item.skill, name: item.skill }]"
        :source-key="`plan:${item.candidate_key}`"
        :plan-item-id="item.id"
        @recorded="done"
      />
      <p v-else-if="item.candidate_type === 'BASELINE'">
        Log this battery item on the <RouterLink :to="{ name: 'baseline' }">
          Baseline page
        </RouterLink> (it completes automatically), or mark it studied.
      </p>
      <p v-else-if="item.candidate_type === 'MOCK' || item.candidate_type === 'FINAL_SIMULATION'">
        <RouterLink :to="{ name: 'mocks', query: { plan_item: item.id } }">
          Log this mock on the Mocks page
        </RouterLink> (it completes this item).
      </p>
      <p v-else>
        Record this on its own page, then mark the item done.
      </p>
    </template>
    <p
      v-if="error"
      role="alert"
      class="errors"
    >
      {{ error }}
    </p>
  </li>
</template>

<style scoped>
.card { border: 1px solid #d8d8de; border-radius: 8px; padding: 0.6rem 0.9rem; margin: 0.6rem 0; background: #fff; list-style: none; }
.card.done { background: #f1f8f1; }
.card.skipped, .card.deferred { opacity: 0.7; }
.head { display: flex; gap: 0.6rem; align-items: baseline; flex-wrap: wrap; }
.icon { font-size: 1.1rem; }
.stage { background: #e3ecff; border-radius: 999px; padding: 0 0.5rem; font-size: 0.8rem; }
.score { font-size: 0.8rem; color: #444; }
.status { margin-left: auto; font-size: 0.8rem; color: #555; }
.why, .rule { font-size: 0.85rem; color: #444; margin: 0.3rem 0; }
.metrics { display: flex; flex-wrap: wrap; gap: 0.3rem 1.2rem; font-size: 0.8rem; background: #f7f7f9; padding: 0.4rem 0.6rem; border-radius: 6px; }
.metrics dt { color: #666; }
.metrics dd { margin: 0; }
.problems { margin: 0.2rem 0; padding-left: 1.2rem; font-size: 0.9rem; }
.timer { font-variant-numeric: tabular-nums; font-size: 1.2rem; margin: 0.3rem 0; }
.actions { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
.secondary { background: none; border: 1px solid #888; }
.chip { border-radius: 999px; border: 1px solid #bbb; background: #f6f6f8; padding: 0.1rem 0.6rem; }
.link { background: none; border: none; color: #2a55b0; text-decoration: underline; cursor: pointer; padding: 0; }
.errors { color: #a11; }
</style>

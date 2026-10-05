<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../../api'
import { ApiError } from '../../api/client'
import type { RevisionItem, RevisionList } from '../../api/types'
import AssessmentForm from '../../components/AssessmentForm.vue'
import { useErrorStore } from '../../stores/errors'

const BUCKETS = ['overdue', 'due', 'upcoming', 'maintenance', 'suspended', 'graduated'] as const
const listing = ref<RevisionList | null>(null)
const bucket = ref<(typeof BUCKETS)[number]>('overdue')
const reviewing = ref<string | null>(null)
const actionError = ref('')
const errorStore = useErrorStore()

const shown = computed(() => (listing.value?.items ?? []).filter((i) => i.bucket === bucket.value))

async function load(): Promise<void> {
  try {
    listing.value = (await api.get<RevisionList>('/revisions')).data
    const counts = listing.value.counts
    if (!counts[bucket.value]) bucket.value = BUCKETS.find((b) => counts[b]) ?? 'overdue'
  } catch (caught) {
    errorStore.report(caught, 'revision')
  }
}

async function act(item: RevisionItem, action: 'suspend' | 'resume'): Promise<void> {
  actionError.value = ''
  try {
    await api.post(`/revisions/${encodeURIComponent(item.item_key)}/${action}`, {})
    await load()
  } catch (caught) {
    actionError.value = caught instanceof ApiError ? caught.message : String(caught)
  }
}

function problemKey(item: RevisionItem): string {
  return item.subject_ref
}

onMounted(load)
</script>

<template>
  <section v-if="listing">
    <h1>Revision</h1>
    <p
      class="meta"
      data-testid="backlog"
    >
      Backlog {{ listing.backlog_minutes }} min · daily cap {{ listing.cap_minutes }} min
      · triage above {{ listing.triage_threshold_minutes }} min. Reviews are closed-book; missing a day is never a fail.
    </p>
    <nav
      class="tabs"
      aria-label="Revision buckets"
    >
      <button
        v-for="b in BUCKETS"
        :key="b"
        type="button"
        :aria-pressed="bucket === b"
        :data-testid="`bucket-${b}`"
        @click="bucket = b"
      >
        {{ b }} ({{ listing.counts[b] ?? 0 }})
      </button>
    </nav>
    <p
      v-if="actionError"
      role="alert"
      class="errors"
    >
      {{ actionError }}
    </p>
    <p v-if="!shown.length">
      Nothing here.
    </p>
    <ul
      v-else
      class="items"
      data-testid="revision-items"
    >
      <li
        v-for="item in shown"
        :key="item.item_key"
        :data-testid="`item-${item.item_key}`"
      >
        <div class="row">
          <strong>{{ item.item_key }}</strong>
          <span>{{ item.skill_name }} ({{ item.tier ?? '—' }})</span>
          <span>{{ item.minutes }} min</span>
          <span v-if="item.due_date">{{ `due ${item.due_date}` + (item.days_overdue ? ` · ${item.days_overdue} d overdue` : '') }}</span>
          <span v-if="item.lapses">lapses {{ item.lapses }}</span>
          <span
            v-if="item.needs_reinforcement"
            class="badge"
          >reinforce first</span>
          <span
            v-if="item.parked"
            class="badge"
          >parked skill</span>
          <span
            v-if="item.suspend_reason"
            class="badge"
          >{{ item.suspend_reason.toLowerCase() }}</span>
        </div>
        <div class="row">
          <template v-if="item.state !== 'SUSPENDED' && (item.bucket === 'overdue' || item.bucket === 'due' || item.bucket === 'maintenance' || item.bucket === 'upcoming')">
            <RouterLink
              v-if="item.item_type === 'PROBLEM'"
              :to="{ name: 'problem', params: { problemKey: problemKey(item) }, query: { revision: item.item_key } }"
              :data-testid="`review-${item.item_key}`"
            >
              Review (re-solve)
            </RouterLink>
            <button
              v-else
              type="button"
              class="link"
              :data-testid="`review-${item.item_key}`"
              @click="reviewing = reviewing === item.item_key ? null : item.item_key"
            >
              Review ({{ item.review_kind.toLowerCase().replace('_', ' ') }})
            </button>
          </template>
          <button
            v-if="item.state === 'ACTIVE'"
            type="button"
            class="secondary"
            :data-testid="`suspend-${item.item_key}`"
            @click="act(item, 'suspend')"
          >
            Suspend
          </button>
          <button
            v-if="item.state === 'SUSPENDED'"
            type="button"
            class="secondary"
            :data-testid="`resume-${item.item_key}`"
            @click="act(item, 'resume')"
          >
            Resume
          </button>
        </div>
        <AssessmentForm
          v-if="reviewing === item.item_key"
          :client="api"
          :kind="item.review_kind"
          :skills="[{ key: item.skill, name: item.skill_name }]"
          :source-key="`revision:${item.item_key}`"
          :revision-item-key="item.item_key"
          @recorded="load"
        />
      </li>
    </ul>
  </section>
</template>

<style scoped>
.meta { color: #555; font-size: 0.85rem; }
.tabs { display: flex; gap: 0.4rem; margin: 0.5rem 0 1rem; flex-wrap: wrap; }
.tabs button { border: 1px solid #bbb; border-radius: 999px; background: #f6f6f8; padding: 0.2rem 0.7rem; }
.tabs button[aria-pressed='true'] { background: #e3ecff; border-color: #3366cc; }
.items { list-style: none; padding: 0; }
.items li { border-bottom: 1px solid #eee; padding: 0.5rem 0; }
.row { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; font-size: 0.9rem; }
.badge { background: #fff1d6; border-radius: 999px; padding: 0 0.5rem; font-size: 0.8rem; }
.link { background: none; border: none; color: #2a55b0; text-decoration: underline; cursor: pointer; padding: 0; }
.secondary { background: none; border: 1px solid #888; }
.errors { color: #a11; }
</style>

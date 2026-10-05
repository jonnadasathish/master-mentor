<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { ApiError } from '../api/client'
import type { RevisionItem } from '../api/types'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorState from '../components/common/ErrorState.vue'
import PageHeader from '../components/common/PageHeader.vue'
import Skeleton from '../components/common/Skeleton.vue'
import RevisionCard from '../components/revision/RevisionCard.vue'
import { formatMinutes } from '../presentation/format'
import { refreshDerivedData, useProblemsStore, useRevisionStore, useSkillsStore } from '../stores/data'

type Tab = 'due' | 'overdue' | 'upcoming' | 'completed' | 'paused'
const TABS: { key: Tab; label: string; buckets: RevisionItem['bucket'][] }[] = [
  { key: 'due', label: 'Due', buckets: ['due', 'maintenance'] },
  { key: 'overdue', label: 'Overdue', buckets: ['overdue'] },
  { key: 'upcoming', label: 'Upcoming', buckets: ['upcoming'] },
  { key: 'completed', label: 'Completed', buckets: ['graduated'] },
  { key: 'paused', label: 'Paused', buckets: ['suspended'] },
]
const EMPTY: Record<Tab, { icon: string; title: string; body: string }> = {
  due: { icon: 'check-circle', title: "You're clear for today.", body: 'Nothing is due right now. Reviews appear here on the day they are due.' },
  overdue: { icon: 'check-circle', title: 'Nothing overdue.', body: "You're on top of your reviews." },
  upcoming: { icon: 'calendar', title: 'Nothing scheduled yet.', body: 'When you practise something, Master Mentor schedules its reviews here.' },
  completed: { icon: 'trending', title: 'Nothing graduated yet.', body: 'Topics graduate after you recall them correctly at every review.' },
  paused: { icon: 'pause', title: 'Nothing paused.', body: 'Reviews you pause, or the mentor parks, wait here.' },
}

const revision = useRevisionStore()
useSkillsStore()
const problems = useProblemsStore()
const tab = ref<Tab>('due')
const actionError = ref('')
const listing = computed(() => revision.data)
const counts = computed(() =>
  Object.fromEntries(
    TABS.map((t) => [t.key, (listing.value?.items ?? []).filter((i) => t.buckets.includes(i.bucket)).length]),
  ) as Record<Tab, number>,
)
const shown = computed(() => {
  const buckets = TABS.find((t) => t.key === tab.value)!.buckets
  return (listing.value?.items ?? []).filter((i) => buckets.includes(i.bucket))
})

async function load(): Promise<void> {
  await revision.refresh()
}

function pickStartingTab(): void {
  tab.value = (['overdue', 'due', 'upcoming', 'completed', 'paused'] as Tab[]).find((t) => counts.value[t] > 0) ?? 'due'
}

async function act(item: RevisionItem, action: 'suspend' | 'resume'): Promise<void> {
  actionError.value = ''
  try {
    await api.post(`/revisions/${encodeURIComponent(item.item_key)}/${action}`, {})
    await refreshDerivedData()
  } catch (caught) {
    actionError.value = caught instanceof ApiError ? caught.message : String(caught)
  }
}

onMounted(async () => {
  await Promise.all([revision.ensure(), useSkillsStore().ensure(), problems.ensure()])
  pickStartingTab()
})
</script>

<template>
  <div class="page">
    <PageHeader
      eyebrow="Revise"
      title="What do you need to recover today?"
      description="Closed-book reviews keep what you've learned. Missing a day is never a failure."
    />

    <Skeleton
      v-if="!listing && !revision.error"
      height="14rem"
      radius="var(--r-lg)"
    />
    <ErrorState
      v-else-if="!listing"
      :error="revision.error"
      @retry="load"
    />

    <template v-else>
      <div
        class="tabs"
        role="tablist"
        aria-label="Reviews"
      >
        <button
          v-for="t in TABS"
          :key="t.key"
          type="button"
          class="tab"
          role="tab"
          :aria-selected="tab === t.key"
          :data-testid="`bucket-${t.key}`"
          @click="tab = t.key"
        >
          {{ t.label }} <span class="count tabular">{{ counts[t.key] }}</span>
        </button>
      </div>

      <p
        class="backlog muted"
        data-testid="backlog"
      >
        About {{ formatMinutes(listing.backlog_minutes) }} of reviews waiting. A comfortable day is up to {{ formatMinutes(listing.cap_minutes) }}.
      </p>
      <p
        v-if="actionError"
        role="alert"
        class="error"
      >
        {{ actionError }}
      </p>

      <ul
        v-if="shown.length"
        class="cards"
        data-testid="revision-items"
      >
        <RevisionCard
          v-for="item in shown"
          :key="item.item_key"
          :item="item"
          :client="api"
          @suspend="act(item, 'suspend')"
          @resume="act(item, 'resume')"
          @reviewed="refreshDerivedData"
        />
      </ul>
      <EmptyState
        v-else
        :icon="EMPTY[tab].icon"
        :title="EMPTY[tab].title"
        :body="EMPTY[tab].body"
      />
    </template>
  </div>
</template>

<style scoped>
.count { margin-left: var(--s-1); font-size: var(--fs-xs); color: var(--text-3); }
.tab[aria-selected='true'] .count { color: var(--accent-text); }
.backlog { font-size: var(--fs-sm); }
.cards { display: grid; gap: var(--s-3); max-width: 50rem; }
.error { color: var(--critical-fg); }
</style>

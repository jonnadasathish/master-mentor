<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api } from '../../api'
import type { CompletionInput, CompletionResult, ContentDetail } from '../../api/types'
import ErrorState from '../../components/common/ErrorState.vue'
import Icon from '../../components/common/Icon.vue'
import Skeleton from '../../components/common/Skeleton.vue'
import StatusPill from '../../components/common/StatusPill.vue'
import ContentRunner from '../../components/learning/ContentRunner.vue'
import { formatMinutes } from '../../presentation/format'
import { CONTENT_TYPE_ICON, CONTENT_TYPE_LABEL, formatLimit, RECORDS_LABEL } from '../../presentation/learning'
import { refreshDerivedData, useSkillsStore } from '../../stores/data'

/** One learning item, outside a session: read it, check yourself or practise, and see what it changed. */
const route = useRoute()
const skills = useSkillsStore()
const content = ref<ContentDetail | null>(null)
const error = ref<unknown>(null)
const key = computed(() => String(route.params.key))
const primary = computed(() => content.value?.skills[0] ?? null)

async function load(): Promise<void> {
  error.value = null
  try {
    content.value = (await api.get<ContentDetail>(`/learning/content/${encodeURIComponent(key.value)}`)).data
  } catch (caught) {
    error.value = caught
  }
}

async function submit(input: CompletionInput) {
  const envelope = await api.post<CompletionResult>(`/learning/content/${encodeURIComponent(key.value)}/complete`, input)
  return { result: envelope.data, effects: envelope.effects }
}

async function completed(): Promise<void> {
  await refreshDerivedData()
  if (content.value?.type === 'project') await load() // milestone progress
}

onMounted(() => Promise.all([load(), skills.ensure()]))
watch(key, load)
</script>

<template>
  <div class="page page-narrow">
    <Skeleton
      v-if="!content && !error"
      height="20rem"
      radius="var(--r-lg)"
    />
    <ErrorState
      v-else-if="!content"
      :error="error"
      @retry="load"
    />
    <template v-else>
      <RouterLink
        v-if="primary"
        :to="{ name: 'skill', params: { key: primary } }"
        class="back"
      >
        <Icon
          name="arrow-left"
          :size="14"
        /> {{ skills.nameOf(primary) }}
      </RouterLink>
      <header class="head">
        <p class="eyebrow">
          <Icon
            :name="CONTENT_TYPE_ICON[content.type]"
            :size="14"
          /> {{ CONTENT_TYPE_LABEL[content.type] }}<template v-if="content.topic">
            · {{ content.topic.title }}
          </template>
        </p>
        <h1 data-testid="content-title">
          {{ content.title }}
        </h1>
        <p class="meta">
          <span><Icon
            name="clock"
            :size="14"
          /> {{ formatMinutes(content.minutes) }}</span>
          <span v-if="content.time_limit_seconds">{{ formatLimit(content.time_limit_seconds) }} (optional timer)</span>
          <span v-if="content.difficulty">{{ content.difficulty.toLowerCase() }}</span>
          <StatusPill
            v-if="content.progress?.passed"
            state="completed"
            :label="content.progress.best_points !== null && !content.spoken ? `Best ${content.progress.best_points}` : content.spoken ? 'Practised' : 'Done'"
            quiet
          />
          <StatusPill
            v-else-if="content.progress"
            state="medium"
            :label="content.progress.best_points !== null && !content.spoken ? `Best ${content.progress.best_points}` : content.spoken ? 'Practised, not yet at the bar' : 'Studied'"
            quiet
          />
        </p>
        <p class="skills">
          <RouterLink
            v-for="s in content.skills"
            :key="s"
            :to="{ name: 'skill', params: { key: s } }"
            class="chip"
          >
            {{ skills.nameOf(s) }}
          </RouterLink>
        </p>
        <p
          v-if="RECORDS_LABEL[content.observation_kind]"
          class="muted small"
        >
          Completing it {{ RECORDS_LABEL[content.observation_kind] }}.
        </p>
      </header>
      <ContentRunner
        :key="content.key"
        :content="content"
        :submit="submit"
        @completed="completed"
      />
    </template>
  </div>
</template>

<style scoped>
.back { display: inline-flex; align-items: center; gap: var(--s-1); font-size: var(--fs-sm); color: var(--text-3); width: fit-content; }
.head { display: grid; gap: var(--s-2); }
.eyebrow { display: flex; align-items: center; gap: var(--s-1); }
h1 { font-size: var(--fs-2xl); text-wrap: balance; }
.meta { display: flex; flex-wrap: wrap; gap: var(--s-3); align-items: center; color: var(--text-2); font-size: var(--fs-sm); }
.meta span { display: inline-flex; align-items: center; gap: var(--s-1); }
.skills { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.chip { padding: 0.2rem 0.7rem; border-radius: 999px; background: var(--surface); border: 1px solid var(--border-strong); font-size: var(--fs-sm); color: var(--text); }
.chip:hover { text-decoration: none; background: var(--surface-2); }
.small { font-size: var(--fs-sm); }
</style>

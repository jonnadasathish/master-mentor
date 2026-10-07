<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '../../api'
import type { SkillLearning } from '../../api/types'
import { PRACTICE_CASE_TEXT, PRACTICE_STATE_LABEL, PRACTICE_STATE_TONE, RELATION_TEXT } from '../../presentation/learning'
import EmptyState from '../common/EmptyState.vue'
import Icon from '../common/Icon.vue'
import StatusPill from '../common/StatusPill.vue'
import ContentList from './ContentList.vue'

/**
 * Shown instead of "No problems match." when a skill has no problem of its own (MASTER_SPEC_V3 §8): related
 * problems with the reason they are related, the skill's own checks and exercises, or an honest content gap.
 */
const props = defineProps<{ skill: string; skillName: string }>()
const learning = ref<SkillLearning | null>(null)
const failed = ref(false)

async function load(): Promise<void> {
  failed.value = false
  try {
    learning.value = (await api.get<SkillLearning>(`/skills/${encodeURIComponent(props.skill)}/learning`)).data
  } catch {
    failed.value = true
  }
}
onMounted(load)
watch(() => props.skill, load)
</script>

<template>
  <EmptyState
    v-if="failed"
    icon="search"
    title="No problems match."
    body="Try a different search or clear a filter."
  />
  <section
    v-else-if="learning"
    class="fallback card"
    data-testid="practice-fallback"
    :data-case="learning.practice.case"
  >
    <p class="eyebrow">
      No problem practises {{ skillName }} directly
    </p>
    <p class="lead">
      {{ PRACTICE_CASE_TEXT[learning.practice.case] }}
    </p>
    <ul
      v-if="learning.practice.related.length"
      class="list card-quiet divided"
      data-testid="related-problems"
    >
      <li
        v-for="r in learning.practice.related"
        :key="r.problem.id"
      >
        <RouterLink
          :to="{ name: 'problem', params: { problemKey: r.problem.key } }"
          class="title"
        >
          {{ r.problem.title }}
        </RouterLink>
        <span class="muted small">via {{ r.via_name }} — {{ RELATION_TEXT[r.relation] }}</span>
        <StatusPill
          :state="PRACTICE_STATE_TONE[r.problem.practice_state]"
          :label="PRACTICE_STATE_LABEL[r.problem.practice_state]"
          quiet
        />
      </li>
    </ul>
    <ContentList
      v-if="[...learning.tabs.practice, ...learning.tabs.test].length"
      :items="[...learning.tabs.test, ...learning.tabs.practice]"
      testid="fallback-content"
    />
    <p
      v-if="learning.practice.case === 'UNCOVERED' && learning.practice.fallback_skill"
      data-testid="fallback-skill"
    >
      Nearest practice:
      <RouterLink :to="{ name: 'skill', params: { key: learning.practice.fallback_skill } }">
        {{ learning.practice.fallback_name }}
      </RouterLink>
    </p>
    <div class="actions">
      <RouterLink
        :to="{ name: 'skill', params: { key: skill } }"
        class="btn btn-primary"
        data-testid="open-skill"
      >
        <Icon
          name="book"
          :size="14"
        /> Learn {{ skillName }}
      </RouterLink>
      <RouterLink
        :to="{ name: 'log', query: { skill } }"
        class="btn"
      >
        Log practice yourself
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.fallback { display: grid; gap: var(--s-4); }
.lead { color: var(--text-2); }
.list li { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); flex-wrap: wrap; }
.title { font-weight: 600; flex: 1 1 12rem; }
.actions { display: flex; gap: var(--s-2); flex-wrap: wrap; }
.small { font-size: var(--fs-sm); }
</style>

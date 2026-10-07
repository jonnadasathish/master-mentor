<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { ContentDetail } from '../../api/types'
import { PRACTICE_STATE_LABEL, PRACTICE_STATE_TONE } from '../../presentation/learning'
import Icon from '../common/Icon.vue'
import StatusPill from '../common/StatusPill.vue'
import RichText from './RichText'

/** Guided or timed problems: how to approach them, then the problems themselves (recorded on the problem page). */
defineProps<{ content: ContentDetail }>()
</script>

<template>
  <section
    class="set"
    data-testid="problem-set"
  >
    <ul class="items">
      <li
        v-for="g in (content.body.guidance as string[]) ?? []"
        :key="g"
      >
        <RichText
          :text="g"
          inline
        />
      </li>
    </ul>
    <details
      v-if="Array.isArray(content.body.hints) && content.body.hints.length"
      class="hints"
    >
      <summary>Hints</summary>
      <ol class="items numbered">
        <li
          v-for="h in content.body.hints as string[]"
          :key="h"
        >
          <RichText
            :text="h"
            inline
          />
        </li>
      </ol>
    </details>
    <ul class="problems card-quiet divided">
      <li
        v-for="p in content.problems"
        :key="p.id"
        :data-testid="`problem-${p.id}`"
      >
        <RouterLink
          :to="{ name: 'problem', params: { problemKey: p.key } }"
          class="title"
        >
          {{ p.title }}
        </RouterLink>
        <span class="muted small">{{ p.difficulty.toLowerCase() }}<template v-if="content.type === 'timed_problem'"> · timed</template></span>
        <StatusPill
          :state="PRACTICE_STATE_TONE[p.practice_state]"
          :label="PRACTICE_STATE_LABEL[p.practice_state]"
          quiet
        />
        <RouterLink
          :to="{ name: 'problem', params: { problemKey: p.key } }"
          class="btn btn-sm btn-primary"
        >
          <Icon
            name="play"
            :size="12"
          /> Solve
        </RouterLink>
      </li>
    </ul>
    <p class="muted small">
      Your attempt is recorded on the problem page, with the timer, hints and result.
    </p>
  </section>
</template>

<style scoped>
.set { display: grid; gap: var(--s-4); max-width: 46rem; }
.items { list-style: disc; padding-left: var(--s-5); display: grid; gap: var(--s-1); }
.numbered { list-style: decimal; }
.hints summary { cursor: pointer; font-weight: 600; color: var(--accent-text); }
.problems li { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); flex-wrap: wrap; }
.title { font-weight: 600; flex: 1 1 12rem; }
.small { font-size: var(--fs-sm); }
</style>
